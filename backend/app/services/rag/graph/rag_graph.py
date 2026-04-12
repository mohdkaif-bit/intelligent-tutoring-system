"""
RAG Graph - Main workflow orchestration using LangGraph.
Refactored with mode-aware retrieval config and hybrid BM25+FAISS support.
"""
from dataclasses import dataclass
from langgraph.graph import StateGraph, START, END

from app.services.rag.graph.state import RAGState
from app.services.rag.graph.nodes import RAGNodes
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Retrieval config per mode
# k        → how many docs each sub-retriever fetches (BM25 + FAISS each get k)
# cap      → max docs passed to the answer node after reranking
# bm25_w   → BM25 weight in the ensemble (faiss_w = 1 - bm25_w)
#
# quick_answer  : high precision, tiny context — strict cap, lean on FAISS
# explain/step  : balanced breadth + precision
# practice      : needs variety → more BM25 weight for keyword diversity
# deep_analysis : maximum recall, reranker + summariser prune later
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class RetrievalConfig:
    k: int           # docs fetched per sub-retriever
    cap: int         # docs kept after rerank
    bm25_w: float    # BM25 ensemble weight  (FAISS = 1 - bm25_w)


RETRIEVAL_CONFIGS: dict[str, RetrievalConfig] = {
    "quick_answer":      RetrievalConfig(k=3,  cap=2,  bm25_w=0.30),
    "explain_concept":   RetrievalConfig(k=6,  cap=4,  bm25_w=0.40),
    "step_by_step":      RetrievalConfig(k=6,  cap=5,  bm25_w=0.40),
    "generate_practice": RetrievalConfig(k=10, cap=8,  bm25_w=0.50),
    "deep_analysis":     RetrievalConfig(k=14, cap=10, bm25_w=0.40),
}
DEFAULT_CONFIG = RetrievalConfig(k=6, cap=4, bm25_w=0.40)


class RAGGraph:
    """
    RAG workflow graph using LangGraph.
    Orchestrates document retrieval, reranking, and answer generation.
    """

    def __init__(self):
        self.nodes = RAGNodes()
        self.graph = self._build_graph()
        logger.info("Initialized RAG Graph")

    # ── graph wiring ──────────────────────────────────────────────────────────

    def _build_graph(self):
        """Build and compile the LangGraph workflow."""
        workflow = StateGraph(RAGState)

        workflow.add_node("retrieve",         self.nodes.retrieve_node)
        workflow.add_node("rerank",           self.nodes.rerank_node)
        workflow.add_node("summarize_chunks", self.nodes.summarize_chunks_node)
        workflow.add_node("combine",          self.nodes.combine_summaries_node)
        workflow.add_node("quick_answer",     self.nodes.quick_answer_node)
        workflow.add_node("explain_concept",  self.nodes.explain_concept_node)
        workflow.add_node("step_by_step",     self.nodes.step_by_step_node)
        workflow.add_node("generate_practice",self.nodes.generate_practice_node)
        workflow.add_node("update_history",   self.nodes.update_history_node)

        workflow.add_edge(START, "retrieve")
        workflow.add_edge("retrieve", "rerank")

        workflow.add_conditional_edges(
            "rerank",
            lambda state: state.get("mode", "quick_answer"),
            {
                "quick_answer":      "quick_answer",
                "explain_concept":   "explain_concept",
                "step_by_step":      "step_by_step",
                "generate_practice": "generate_practice",
                "deep_analysis":     "summarize_chunks",
            }
        )

        workflow.add_edge("summarize_chunks", "combine")

        for node in ("quick_answer", "explain_concept",
                     "step_by_step", "generate_practice", "combine"):
            workflow.add_edge(node, "update_history")

        workflow.add_edge("update_history", END)

        logger.info("Built RAG graph workflow")
        return workflow.compile()

    # ── retriever factory ─────────────────────────────────────────────────────

    def _build_retriever(self, vector_retriever, mode: str):
        """
        Build an EnsembleRetriever whose k and BM25/FAISS weights are tuned
        for the given mode.  Mutates only the local copies so the shared
        VectorRetriever state is never touched.

        Args:
            vector_retriever : VectorRetriever instance (already has .vectorstore
                               and .bm25_retriever loaded)
            mode             : RAG mode string

        Returns:
            EnsembleRetriever configured for this mode
        """
        from langchain_community.retrievers import BM25Retriever
        from langchain_classic.retrievers import EnsembleRetriever
        import copy

        cfg = RETRIEVAL_CONFIGS.get(mode, DEFAULT_CONFIG)

        # ── FAISS retriever ───────────────────────────────────────────────
        faiss_ret = vector_retriever.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": cfg.k},
        )

        # ── BM25 retriever — shallow-copy so we don't mutate the cached one ─
        bm25_ret = copy.copy(vector_retriever.bm25_retriever)
        bm25_ret.k = cfg.k

        faiss_w = round(1.0 - cfg.bm25_w, 2)

        ensemble = EnsembleRetriever(
            retrievers=[bm25_ret, faiss_ret],
            weights=[cfg.bm25_w, faiss_w],
        )

        logger.info(
            "Built retriever for mode=%s  k=%d  bm25=%.2f  faiss=%.2f",
            mode, cfg.k, cfg.bm25_w, faiss_w,
        )
        return ensemble, cfg

    # ── public API ────────────────────────────────────────────────────────────

    def invoke(self, state: dict, vector_retriever=None) -> dict:
        """
        Execute the RAG workflow.

        Args:
            state            : Initial state dict (must contain at least 'question')
            vector_retriever : VectorRetriever instance. When provided the graph
                               builds a mode-tuned EnsembleRetriever and injects
                               it (+ the cap) into state automatically.

        Returns:
            Final state after workflow execution
        """
        mode = state.get("mode", "quick_answer")

        # ── inject a mode-tuned retriever if the caller supplied one ──────
        if vector_retriever is not None and not state.get("top_docs"):
            try:
                retriever, cfg = self._build_retriever(vector_retriever, mode)
                state = {
                    **state,
                    "retriever": retriever,
                    # cap travels in state so retrieve_node can slice correctly
                    "_retrieval_cap": cfg.cap,
                }
                logger.info(
                    "invoke: injected mode-tuned retriever "
                    "(mode=%s k=%d cap=%d)", mode, cfg.k, cfg.cap,
                )
            except Exception as exc:
                logger.warning(
                    "invoke: could not build mode-tuned retriever (%s), "
                    "falling back to state['retriever']", exc,
                )

        try:
            logger.info("Invoking RAG graph — mode: %s", mode)
            result = self.graph.invoke(state)
            logger.info("RAG graph execution completed")
            return result
        except Exception as e:
            logger.error("Error executing RAG graph: %s", e)
            raise