"""
RAG Evaluator
-------------
Unified orchestrator combining RetrievalMetrics and GenerationMetrics.

Plugs into your existing ITS stack:
  - Reads Documents directly from state["top_docs"]
  - Uses settings.STORAGE_BASE_DIR for report persistence
  - Uses GroqClient.invoke() for LLM-as-judge faithfulness
  - Uses HuggingFaceEmbeddings for semantic similarity

Metrics (no ground truth required)
-----------------------------------
  - Faithfulness          : answer stays grounded in PDF content
  - Chunk Relevance       : retriever pulls right sections for the query
  - Answer Completeness   : answer covers key points from context
  - Context Utilization   : fraction of retrieved chunks actually used

Typical usage
-------------
    from app.services.rag.metrics import RAGEvaluator

    evaluator = RAGEvaluator(retrieval_k=5)
    report = evaluator.run(eval_dataset)
    evaluator.save_report(report, user_id="default_user")
    evaluator.print_report(report)
"""

from __future__ import annotations

import dataclasses
import json
import logging
from datetime import datetime
from typing import Any

from langchain_core.documents import Document

from app.core.config import settings
from app.core.logging import get_logger
from .generation_metrics import GenerationMetrics
from .retrieval_metrics import RetrievalMetrics

logger = get_logger(__name__)

EVAL_STORAGE_DIR = settings.STORAGE_BASE_DIR / "evaluation"


class RAGEvaluator:
    """
    Unified RAG evaluation pipeline.

    Parameters
    ----------
    retrieval_k : int
        Top-K documents to evaluate for retrieval metrics.
    embeddings : optional
        HuggingFaceEmbeddings instance (from vector_retriever.get_embeddings_model()).
    groq_client : optional
        GroqClient instance (from get_llm_client()).
    """

    def __init__(
        self,
        retrieval_k: int = 5,
        embeddings=None,
        groq_client=None,
    ) -> None:
        self.retrieval_metrics = RetrievalMetrics(k=retrieval_k)
        self.generation_metrics = GenerationMetrics(
            embeddings=embeddings,
            groq_client=groq_client,
        )

    # ------------------------------------------------------------------ #
    # Core evaluation                                                       #
    # ------------------------------------------------------------------ #

    def run(self, eval_dataset: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Run the full RAG evaluation pipeline.

        Each item in eval_dataset must have:

          Always required:
            "query"             : str
            "context_chunks"    : list[str]
            "generated_answer"  : str

          For retrieval metrics (optional):
            Option A – Document objects:
              "retrieved_docs"  : list[Document]
              "relevant_docs"   : list[Document]
            Option B – pre-computed string IDs:
              "retrieved_ids"   : list[str]
              "relevant_ids"    : list[str] | set[str]

          For supervised generation metrics (optional):
            "expected_answer"   : str

        Returns
        -------
        dict with keys: "retrieval", "generation", "per_query", "metadata"
        """
        if not eval_dataset:
            logger.warning("RAGEvaluator.run() called with empty dataset.")
            return {}

        retrieval_batch = []
        generation_batch = []

        for item in eval_dataset:
            # Retrieval batch entry
            if "retrieved_docs" in item:
                retrieval_batch.append({
                    "query": item["query"],
                    "retrieved_docs": item["retrieved_docs"],
                    "relevant_docs": item.get("relevant_docs", []),
                })
            else:
                retrieval_batch.append({
                    "query": item["query"],
                    "retrieved_ids": item.get("retrieved_ids", []),
                    "relevant_ids": set(item.get("relevant_ids", [])),
                })

            # Generation batch entry
            generation_batch.append({
                "query": item["query"],
                "generated_answer": item["generated_answer"],
                "context_chunks": item.get("context_chunks", []),
                "expected_answer": item.get("expected_answer"),
            })

        ret_report = self.retrieval_metrics.evaluate_batch(retrieval_batch)
        gen_report = self.generation_metrics.evaluate_batch(generation_batch)

        # Per-query combined view
        per_query = []
        for ret_res, gen_res in zip(ret_report["results"], gen_report["results"]):
            per_query.append({
                "query": ret_res.query,
                # Retrieval
                "precision_at_k": round(ret_res.precision_at_k, 4),
                "recall_at_k": round(ret_res.recall_at_k, 4),
                "reciprocal_rank": round(ret_res.reciprocal_rank, 4),
                "hit_rate": ret_res.hit_rate,
                # Generation — supervised (null if no expected_answer)
                "exact_match": gen_res.exact_match,
                "f1_score": (
                    round(gen_res.f1_score, 4)
                    if gen_res.f1_score is not None else None
                ),
                "semantic_similarity": (
                    round(gen_res.semantic_similarity, 4)
                    if gen_res.semantic_similarity is not None else None
                ),
                # Generation — unsupervised (always calculated)
                "faithfulness": round(gen_res.faithfulness_score, 4),
                "context_utilization": round(gen_res.context_utilization, 4),
                "chunk_relevance": round(gen_res.chunk_relevance, 4),
                "answer_completeness": round(gen_res.answer_completeness, 4),
            })

        return {
            "retrieval": {
                "mean_precision_at_k": round(ret_report["mean_precision_at_k"], 4),
                "mean_recall_at_k": round(ret_report["mean_recall_at_k"], 4),
                "mrr": round(ret_report["mrr"], 4),
                "hit_rate_at_k": round(ret_report["hit_rate_at_k"], 4),
                "k": ret_report["k"],
            },
            "generation": {
                # Supervised (null without expected_answer)
                "mean_f1": (
                    round(gen_report["mean_f1"], 4)
                    if gen_report["mean_f1"] is not None else None
                ),
                "mean_semantic_similarity": (
                    round(gen_report["mean_semantic_similarity"], 4)
                    if gen_report["mean_semantic_similarity"] is not None else None
                ),
                "exact_match_rate": (
                    round(gen_report["exact_match_rate"], 4)
                    if gen_report["exact_match_rate"] is not None else None
                ),
                # Unsupervised (always calculated — core ITS metrics)
                "mean_faithfulness": round(gen_report["mean_faithfulness"], 4),
                "mean_context_utilization": round(
                    gen_report["mean_context_utilization"], 4
                ),
                "mean_chunk_relevance": round(
                    gen_report["mean_chunk_relevance"], 4
                ),
                "mean_answer_completeness": round(
                    gen_report["mean_answer_completeness"], 4
                ),
            },
            "per_query": per_query,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "n_queries": len(eval_dataset),
                "k": self.retrieval_metrics.k,
                "faithfulness_method": (
                    "llm_judge"
                    if self.generation_metrics.groq_client is not None
                    else "heuristic"
                ),
                "semantic_similarity_method": (
                    "huggingface_embeddings"
                    if self.generation_metrics.embeddings is not None
                    else "jaccard_fallback"
                ),
            },
        }

    # ------------------------------------------------------------------ #
    # Persistence                                                           #
    # ------------------------------------------------------------------ #

    def save_report(
        self,
        report: dict[str, Any],
        user_id: str = "default_user",
        filename: str | None = None,
    ) -> str:
        """Save evaluation report to .storage/evaluation/<user_id>/."""
        user_dir = EVAL_STORAGE_DIR / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"rag_eval_{ts}.json"

        path = user_dir / filename
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(_make_serialisable(report), fh, indent=2, ensure_ascii=False)

        logger.info("RAG evaluation report saved to %s", path)
        return str(path)

    # ------------------------------------------------------------------ #
    # Pretty-print                                                          #
    # ------------------------------------------------------------------ #

    def print_report(self, report: dict[str, Any]) -> None:
        """Print a human-readable summary to stdout."""
        meta = report.get("metadata", {})
        ret  = report.get("retrieval", {})
        gen  = report.get("generation", {})

        def fmt(val: float | None) -> str:
            return f"{val:.4f}" if val is not None else "N/A"

        print("\n" + "=" * 60)
        print("  RAG EVALUATION REPORT")
        print("=" * 60)
        print(f"  Timestamp    : {meta.get('timestamp', 'N/A')}")
        print(f"  Queries      : {meta.get('n_queries', 'N/A')}")
        print(f"  K            : {meta.get('k', 'N/A')}")
        print(f"  Faithfulness : {meta.get('faithfulness_method', 'N/A')}")
        print(f"  Sem. Sim.    : {meta.get('semantic_similarity_method', 'N/A')}")
        print("-" * 60)
        print("  RETRIEVAL METRICS")
        print(f"    Precision@K   : {fmt(ret.get('mean_precision_at_k'))}")
        print(f"    Recall@K      : {fmt(ret.get('mean_recall_at_k'))}")
        print(f"    MRR           : {fmt(ret.get('mrr'))}")
        print(f"    Hit Rate@K    : {fmt(ret.get('hit_rate_at_k'))}")
        print("-" * 60)
        print("  GENERATION METRICS")
        print(f"    Faithfulness      : {fmt(gen.get('mean_faithfulness'))}")
        print(f"    Context Util.     : {fmt(gen.get('mean_context_utilization'))}")
        print(f"    Chunk Relevance   : {fmt(gen.get('mean_chunk_relevance'))}")
        print(f"    Answer Complete.  : {fmt(gen.get('mean_answer_completeness'))}")
        print(f"    Exact Match       : {fmt(gen.get('exact_match_rate'))}")
        print(f"    Token F1          : {fmt(gen.get('mean_f1'))}")
        print(f"    Semantic Sim.     : {fmt(gen.get('mean_semantic_similarity'))}")
        print("=" * 60 + "\n")


# ------------------------------------------------------------------ #
# Serialisation helper                                                  #
# ------------------------------------------------------------------ #

def _make_serialisable(obj: Any) -> Any:
    """Recursively convert dataclasses and non-JSON types to plain dicts."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _make_serialisable(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _make_serialisable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serialisable(v) for v in obj]
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, (bool, int, float, str)) or obj is None:
        return obj
    return str(obj)