"""
Retrieval Metrics
-----------------
Evaluates the retriever component of the RAG pipeline.

Works directly with LangChain Document objects as returned by
VectorRetriever, which uses PyMuPDFLoader. Each Document has:
  doc.metadata["source"] -> full PDF file path
  doc.metadata["page"]   -> 0-indexed page number

Metrics
-------
- Precision@K  : fraction of top-K docs that are relevant
- Recall@K     : fraction of all relevant docs captured in top-K
- MRR          : Mean Reciprocal Rank
- Hit Rate@K   : at least one relevant doc in top-K
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


def _doc_id(doc: Document) -> str:
    """
    Derive a stable string ID from a LangChain Document.

    PyMuPDFLoader populates:
      doc.metadata["source"] -> path to the PDF
      doc.metadata["page"]   -> 0-indexed page number

    Result example:
      "MohdKaif1.pdf_750ce72a6766__p3"
    """
    source = doc.metadata.get("source", "unknown")
    page = doc.metadata.get("page", 0)
    # Use just the filename, not the full path, for readability
    filename = source.replace("\\", "/").split("/")[-1]
    return f"{filename}__p{page}"


@dataclass
class RetrievalResult:
    """Scores for a single query."""
    query: str
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    mrr: float               # same as reciprocal_rank for single query
    hit_rate: bool
    k: int
    n_relevant_retrieved: int
    n_total_relevant: int
    retrieved_ids: list[str]
    relevant_ids: set[str]


class RetrievalMetrics:
    """
    Compute retrieval-quality metrics.

    Parameters
    ----------
    k : int
        Number of top retrieved documents to consider.

    Usage
    -----
    From the RAG graph state after retrieval:

        rm = RetrievalMetrics(k=5)

        # top_docs comes from state["top_docs"] (list[Document])
        # relevant_docs is your ground-truth list[Document] for this query
        result = rm.evaluate_single(
            query="What is gradient descent?",
            retrieved_docs=state["top_docs"],
            relevant_docs=ground_truth_docs,
        )

    Or with pre-computed string IDs if you have them:

        result = rm.evaluate_single_from_ids(
            query="...",
            retrieved_ids=["file.pdf__p3", "file.pdf__p7"],
            relevant_ids={"file.pdf__p3"},
        )
    """

    def __init__(self, k: int = 5) -> None:
        self.k = k

    # ------------------------------------------------------------------ #
    # ID derivation                                                         #
    # ------------------------------------------------------------------ #

    def docs_to_ids(self, docs: list[Document]) -> list[str]:
        """Convert a list of Documents to a list of stable string IDs."""
        return [_doc_id(doc) for doc in docs]

    # ------------------------------------------------------------------ #
    # Core metric functions (operate on string IDs)                        #
    # ------------------------------------------------------------------ #

    def precision_at_k(
        self,
        retrieved_ids: list[str],
        relevant_ids: set[str],
    ) -> float:
        """|relevant ∩ top-K| / K"""
        if not retrieved_ids:
            return 0.0
        top_k = retrieved_ids[: self.k]
        hits = sum(1 for d in top_k if d in relevant_ids)
        return hits / len(top_k)

    def recall_at_k(
        self,
        retrieved_ids: list[str],
        relevant_ids: set[str],
    ) -> float:
        """| relevant ∩ top-K| / |relevant|"""
        if not relevant_ids:
            return 1.0
        top_k = set(retrieved_ids[: self.k])
        return len(top_k & relevant_ids) / len(relevant_ids)

    def reciprocal_rank(
        self,
        retrieved_ids: list[str],
        relevant_ids: set[str],
    ) -> float:
        """1 / rank_of_first_relevant. Returns 0 if none found in top-K."""
        for rank, doc_id in enumerate(retrieved_ids[: self.k], start=1):
            if doc_id in relevant_ids:
                return 1.0 / rank
        return 0.0

    def hit_rate_at_k(
        self,
        retrieved_ids: list[str],
        relevant_ids: set[str],
    ) -> bool:
        """True if at least one relevant doc appears in top-K."""
        return bool(set(retrieved_ids[: self.k]) & relevant_ids)

    # ------------------------------------------------------------------ #
    # Single-query evaluation                                               #
    # ------------------------------------------------------------------ #

    def evaluate_single(
        self,
        query: str,
        retrieved_docs: list[Document],
        relevant_docs: list[Document],
    ) -> RetrievalResult:
        """
        Evaluate all retrieval metrics for one query using Document objects.

        Parameters
        ----------
        query          : The user's question.
        retrieved_docs : Ordered list of retrieved Documents (best first).
                         Comes from state["top_docs"] after reranking.
        relevant_docs  : Ground-truth relevant Documents for this query.
        """
        retrieved_ids = self.docs_to_ids(retrieved_docs)
        relevant_ids = set(self.docs_to_ids(relevant_docs))
        return self.evaluate_single_from_ids(query, retrieved_ids, relevant_ids)

    def evaluate_single_from_ids(
        self,
        query: str,
        retrieved_ids: list[str],
        relevant_ids: set[str],
    ) -> RetrievalResult:
        """
        Evaluate all retrieval metrics using pre-computed string IDs.
        Use this when you already know doc IDs (e.g. from a test dataset).
        """
        top_k = retrieved_ids[: self.k]
        n_relevant_retrieved = sum(1 for d in top_k if d in relevant_ids)
        rr = self.reciprocal_rank(retrieved_ids, relevant_ids)

        return RetrievalResult(
            query=query,
            precision_at_k=self.precision_at_k(retrieved_ids, relevant_ids),
            recall_at_k=self.recall_at_k(retrieved_ids, relevant_ids),
            reciprocal_rank=rr,
            mrr=rr,
            hit_rate=self.hit_rate_at_k(retrieved_ids, relevant_ids),
            k=self.k,
            n_relevant_retrieved=n_relevant_retrieved,
            n_total_relevant=len(relevant_ids),
            retrieved_ids=retrieved_ids,
            relevant_ids=relevant_ids,
        )

    # ------------------------------------------------------------------ #
    # Batch evaluation                                                      #
    # ------------------------------------------------------------------ #

    def evaluate_batch(self, batch: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Evaluate retrieval metrics across multiple queries.

        Each item in batch must have:
          - "query"           : str
          - "retrieved_docs"  : list[Document]   (from state["top_docs"])
          - "relevant_docs"   : list[Document]   (ground truth)

        OR with pre-computed IDs:
          - "query"           : str
          - "retrieved_ids"   : list[str]
          - "relevant_ids"    : set[str] | list[str]

        Returns
        -------
        dict with aggregate scores and per-query RetrievalResult list.
        """
        if not batch:
            logger.warning("evaluate_batch called with empty batch.")
            return self._zero_aggregate()

        results: list[RetrievalResult] = []
        for item in batch:
            if "retrieved_docs" in item:
                result = self.evaluate_single(
                    query=item["query"],
                    retrieved_docs=item["retrieved_docs"],
                    relevant_docs=item["relevant_docs"],
                )
            else:
                result = self.evaluate_single_from_ids(
                    query=item["query"],
                    retrieved_ids=item["retrieved_ids"],
                    relevant_ids=set(item["relevant_ids"]),
                )
            results.append(result)

        return {
            "results": results,
            "mean_precision_at_k": float(np.mean([r.precision_at_k for r in results])),
            "mean_recall_at_k": float(np.mean([r.recall_at_k for r in results])),
            "mrr": float(np.mean([r.mrr for r in results])),
            "hit_rate_at_k": float(np.mean([float(r.hit_rate) for r in results])),
            "k": self.k,
        }

    def _zero_aggregate(self) -> dict[str, Any]:
        return {
            "results": [],
            "mean_precision_at_k": 0.0,
            "mean_recall_at_k": 0.0,
            "mrr": 0.0,
            "hit_rate_at_k": 0.0,
            "k": self.k,
        }