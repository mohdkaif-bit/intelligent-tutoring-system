"""
RAG Graph Nodes - Individual processing steps in the workflow.
"""
import copy
from typing import Dict, List, Any
from dataclasses import dataclass
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from sentence_transformers import CrossEncoder

from app.services.llm.groq_client import get_llm_client
from app.services.llm.prompt_manager.prompts import PromptManager
from app.services.rag.graph.state import RAGState
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Retrieval config per mode
# k      → docs fetched by each sub-retriever (BM25 + FAISS independently)
# cap    → docs kept after rerank and passed to the answer node
# bm25_w → BM25 ensemble weight  (faiss_w = 1 - bm25_w)
# floor  → minimum cross-encoder score to keep a doc (scores range ~ -5 to +5)
#
# quick_answer  : high precision, tiny context — strict floor
# explain/step  : balanced breadth + precision
# generate_prac : needs topic variety → loose floor
# deep_analysis : max recall, summariser prunes later → very loose floor
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RetrievalConfig:
    k: int          # docs fetched per sub-retriever
    cap: int        # docs kept after rerank
    bm25_w: float   # BM25 ensemble weight (FAISS = 1 - bm25_w)
    floor: float    # cross-encoder score floor (below = noise, drop it)


RETRIEVAL_CONFIGS: dict[str, RetrievalConfig] = {
    "quick_answer":      RetrievalConfig(k=3,  cap=2,  bm25_w=0.30, floor=0.5),
    "explain_concept":   RetrievalConfig(k=6,  cap=4,  bm25_w=0.40, floor=0.3),
    "step_by_step":      RetrievalConfig(k=6,  cap=5,  bm25_w=0.40, floor=0.1),
    "generate_practice": RetrievalConfig(k=10, cap=8,  bm25_w=0.50, floor=-0.5),
    "deep_analysis":     RetrievalConfig(k=14, cap=10, bm25_w=0.40, floor=-1.0),
}
DEFAULT_CONFIG = RetrievalConfig(k=6, cap=4, bm25_w=0.40, floor=0.0)


class RAGNodes:
    """Collection of nodes for the RAG graph workflow."""

    def __init__(self):
        self.llm_client   = get_llm_client()
        self.prompts      = PromptManager()

        # Cross-encoder loaded once at startup — zero API tokens, runs locally
        # max_length=512 truncates long chunks for faster CPU inference
        logger.info("Loading cross-encoder model...")
        self.cross_encoder = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            max_length=512,
        )
        logger.info("Cross-encoder ready")

    # ─────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────

    def _build_mode_retriever(
        self,
        vector_retriever,
        mode: str,
    ) -> tuple:
        """
        Build a mode-tuned EnsembleRetriever from a loaded VectorRetriever.
        Returns (ensemble, RetrievalConfig).
        """
        cfg = RETRIEVAL_CONFIGS.get(mode, DEFAULT_CONFIG)

        faiss_ret = vector_retriever.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": cfg.k},
        )

        bm25_ret   = copy.copy(vector_retriever.bm25_retriever)
        bm25_ret.k = cfg.k

        faiss_w  = round(1.0 - cfg.bm25_w, 2)
        ensemble = EnsembleRetriever(
            retrievers=[bm25_ret, faiss_ret],
            weights=[cfg.bm25_w, faiss_w],
        )
        logger.info(
            "_build_mode_retriever: mode=%s  k=%d  bm25=%.2f  faiss=%.2f",
            mode, cfg.k, cfg.bm25_w, faiss_w,
        )
        return ensemble, cfg

    # ─────────────────────────────────────────────────────────────────────
    # Node: retrieve
    # ─────────────────────────────────────────────────────────────────────

    def retrieve_node(self, state: RAGState) -> Dict:
        """
        Retrieve relevant documents.

        Priority order:
          1. top_docs already in state (adaptation layer pre-retrieved) → slice to cap
          2. vector_retriever in state → build mode-tuned ensemble on the fly
          3. retriever in state        → use as-is, slice to cap
        """
        mode = state.get("mode", "quick_answer")
        cfg  = RETRIEVAL_CONFIGS.get(mode, DEFAULT_CONFIG)
        cap  = state.get("_retrieval_cap", cfg.cap)

        # ── fast-path: adaptation layer already retrieved ─────────────────
        if state.get("top_docs"):
            docs = state["top_docs"][:cap]
            logger.info(
                "retrieve_node [%s]: %d pre-ranked docs from adaptation layer (cap=%d)",
                mode, len(docs), cap,
            )
            return {"docs": docs, "top_docs": docs}

        # ── build mode-tuned retriever from VectorRetriever instance ──────
        vector_retriever = state.get("vector_retriever")
        if vector_retriever is not None:
            try:
                retriever, cfg = self._build_mode_retriever(vector_retriever, mode)
                cap = cfg.cap
                logger.info(
                    "retrieve_node [%s]: built mode-tuned retriever (k=%d cap=%d)",
                    mode, cfg.k, cap,
                )
            except Exception as exc:
                logger.warning(
                    "retrieve_node: failed to build mode retriever (%s), "
                    "falling back to state['retriever']", exc,
                )
                retriever = state.get("retriever")
        else:
            retriever = state.get("retriever")

        if not retriever:
            logger.warning("retrieve_node: no retriever available")
            return {"docs": [], "top_docs": []}

        try:
            raw  = list(retriever.invoke(state["question"]))
            docs = raw[:cap]
            logger.info(
                "retrieve_node [%s]: retrieved %d → kept %d (cap=%d)",
                mode, len(raw), len(docs), cap,
            )
            return {"docs": docs, "top_docs": docs}
        except Exception as exc:
            logger.error("retrieve_node error: %s", exc)
            return {"docs": [], "top_docs": []}

    # ─────────────────────────────────────────────────────────────────────
    # Node: rerank
    # Cross-encoder replaces LLM scoring — zero API tokens, ~50ms on CPU
    # ─────────────────────────────────────────────────────────────────────

    def rerank_node(self, state: RAGState) -> Dict:
        """
        Rerank top_docs using a cross-encoder model.

        Cross-encoder scores each (query, chunk) pair jointly — much more
        accurate than embedding cosine similarity and uses zero LLM tokens.

        Score floor per mode filters noise before the cap is applied so
        the answer node never receives weakly relevant chunks.
        """
        docs = state.get("top_docs", [])
        if not docs:
            logger.warning("rerank_node: no documents to rerank")
            return {"top_docs": []}

        mode  = state.get("mode", "quick_answer")
        cfg   = RETRIEVAL_CONFIGS.get(mode, DEFAULT_CONFIG)
        cap   = state.get("_retrieval_cap", cfg.cap)
        query = state["question"]

        # ── score all pairs in one batch (single forward pass) ────────────
        pairs = [[query, doc.page_content] for doc in docs]

        try:
            scores = self.cross_encoder.predict(
                pairs,
                batch_size=8,            # controls CPU memory usage
                show_progress_bar=False,
            )
        except Exception as exc:
            # Cross-encoder failure is non-fatal — pass docs through unranked
            logger.error("rerank_node: cross-encoder failed (%s), passing docs unranked", exc)
            return {"top_docs": docs[:cap]}

        ranked = sorted(
            zip(scores, docs),
            key=lambda x: x[0],
            reverse=True,
        )

        # ── apply score floor (cap is a ceiling, not a target) ────────────
        above_floor = [(s, d) for s, d in ranked if s >= cfg.floor]

        if not above_floor:
            # Nothing passed floor — keep top-1 so pipeline never starves
            logger.warning(
                "rerank_node [%s]: no docs passed floor=%.2f, keeping top-1 fallback",
                mode, cfg.floor,
            )
            final_docs = [ranked[0][1]] if ranked else docs
        else:
            final_docs = [d for _, d in above_floor][:cap]

        logger.info(
            "rerank_node [%s]: %d docs scored → %d passed floor=%.2f → %d kept (cap=%d)"
            " | top=%.3f  bottom=%.3f",
            mode,
            len(ranked),
            len(above_floor),
            cfg.floor,
            len(final_docs),
            cap,
            ranked[0][0]  if ranked else 0.0,
            ranked[-1][0] if ranked else 0.0,
        )
        return {"top_docs": final_docs}

    # ─────────────────────────────────────────────────────────────────────
    # Node: quick_answer
    # ─────────────────────────────────────────────────────────────────────

    def quick_answer_node(self, state: RAGState) -> Dict:
        """Generate a concise answer from the top 1-2 chunks."""
        context_text = "\n\n".join(
            doc.page_content for doc in state.get("top_docs", [])
        )
        style_hint = state.get("style_hint", "")

        prompt = self.prompts.get_prompt(
            "qa_prompt",
            history="",
            context=context_text,
            question=state["question"],
        )
        if style_hint:
            prompt = style_hint + prompt

        try:
            answer = self.llm_client.invoke(prompt, mode="quick_answer")
            logger.info("quick_answer_node: answer generated")
        except Exception as exc:
            logger.error("quick_answer_node error: %s", exc)
            answer = f"Error: {exc}"

        return {"answer": answer}

    # ─────────────────────────────────────────────────────────────────────
    # Node: explain_concept
    # ─────────────────────────────────────────────────────────────────────

    def explain_concept_node(self, state: RAGState) -> Dict:
        """Explain a concept in detail using 4-5 chunks."""
        context_text = "\n\n".join(
            doc.page_content for doc in state.get("top_docs", [])
        )
        style_hint = state.get("style_hint", "")

        prompt = self.prompts.get_prompt(
            "concept_explanation_prompt",
            context=context_text,
            question=state["question"],
        )
        if style_hint:
            prompt = style_hint + prompt

        try:
            answer = self.llm_client.invoke(prompt, mode="explain_concept")
            logger.info("explain_concept_node: explanation generated")
        except Exception as exc:
            logger.error("explain_concept_node error: %s", exc)
            answer = "Error generating explanation"

        return {"answer": answer}

    # ─────────────────────────────────────────────────────────────────────
    # Node: step_by_step
    # ─────────────────────────────────────────────────────────────────────

    def step_by_step_node(self, state: RAGState) -> Dict:
        """Provide a step-by-step solution using 4-5 chunks."""
        context_text = "\n\n".join(
            doc.page_content for doc in state.get("top_docs", [])
        )
        style_hint = state.get("style_hint", "")

        prompt = self.prompts.get_prompt(
            "step_by_step_prompt",
            context=context_text,
            question=state["question"],
        )
        if style_hint:
            prompt = style_hint + prompt

        try:
            answer = self.llm_client.invoke(prompt, mode="step_by_step")
            logger.info("step_by_step_node: guide generated")
        except Exception as exc:
            logger.error("step_by_step_node error: %s", exc)
            answer = "Error"

        return {"answer": answer}

    # ─────────────────────────────────────────────────────────────────────
    # Node: generate_practice
    # ─────────────────────────────────────────────────────────────────────

    def generate_practice_node(self, state: RAGState) -> Dict:
        """Generate practice problems using 7-8 diverse chunks."""
        context_text = "\n\n".join(
            doc.page_content for doc in state.get("top_docs", [])
        )
        style_hint = state.get("style_hint", "")

        prompt = self.prompts.get_prompt(
            "practice_problem_prompt",
            context=context_text,
            question=state["question"],
        )
        if style_hint:
            prompt = style_hint + prompt

        try:
            answer = self.llm_client.invoke(prompt, mode="generate_practice")
            logger.info("generate_practice_node: problems generated")
        except Exception as exc:
            logger.error("generate_practice_node error: %s", exc)
            answer = "Error"

        return {"answer": answer}

    # ─────────────────────────────────────────────────────────────────────
    # Node: summarize_chunks  (deep_analysis only)
    # ─────────────────────────────────────────────────────────────────────

    def summarize_chunks_node(self, state: RAGState) -> Dict:
        """
        Summarize each retrieved chunk individually.
        Only runs for deep_analysis; all other modes return early.
        Uses state['docs'] (full set) so every chunk gets summarised.
        """
        if state.get("mode") != "deep_analysis":
            return {"per_chunk_summaries": []}

        summaries = []
        for doc in state.get("docs", []):
            prompt = self.prompts.get_prompt(
                "chunk_summary_prompt",
                chunk=doc.page_content,
            )
            try:
                summary = self.llm_client.invoke(prompt, mode="deep_analysis")
                summaries.append(summary)
            except Exception as exc:
                logger.warning("summarize_chunks_node: chunk error (%s), skipping", exc)

        logger.info("summarize_chunks_node: %d summaries generated", len(summaries))
        return {"per_chunk_summaries": summaries}

    # ─────────────────────────────────────────────────────────────────────
    # Node: combine_summaries
    # ─────────────────────────────────────────────────────────────────────

    def combine_summaries_node(self, state: RAGState) -> Dict:
        """Combine per-chunk summaries into a final deep-analysis report."""
        summaries = state.get("per_chunk_summaries", [])
        if not summaries:
            logger.warning("combine_summaries_node: no summaries to combine")
            return {"final_report": "No content available", "answer": "No content available"}

        summaries_text = "\n".join(f"- {s}" for s in summaries)
        prompt = self.prompts.get_prompt(
            "combine_summaries_prompt",
            question=state["question"],
            summaries=summaries_text,
        )

        try:
            report = self.llm_client.invoke(prompt, mode="deep_analysis")
            logger.info("combine_summaries_node: report generated")
        except Exception as exc:
            logger.error("combine_summaries_node error: %s", exc)
            report = "Error generating report"

        return {"final_report": report, "answer": report}

    # ─────────────────────────────────────────────────────────────────────
    # Node: update_history
    # ─────────────────────────────────────────────────────────────────────

    def update_history_node(self, state: RAGState) -> Dict:
        """Append the current Q&A turn to conversation history."""
        history = state.get("history", [])
        updated = history + [
            {"role": "user",      "content": state["question"]},
            {"role": "assistant", "content": state.get("answer", "")},
        ]
        logger.debug("update_history_node: history now %d messages", len(updated))
        return {"history": updated}