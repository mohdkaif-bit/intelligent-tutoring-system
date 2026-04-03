"""
Context Ranker
--------------
Adaptation C: Context Prioritization

After the retriever returns top_docs, this module re-scores each
Document by boosting chunks that come from pages the user has
struggled with. The rerank node in RAGGraph then sees a better-ordered
list, so the LLM's context window is filled with the most relevant
AND most-struggled-with material first.

How it works
------------
Each retrieved Document has:
  doc.metadata["source"] → PDF file path
  doc.metadata["page"]   → 0-indexed page number

We look up the PageInteraction for that page and compute a
"struggle boost" score. The final score passed to the rerank node
is: retriever_rank_score + struggle_boost_weight * struggle_boost

Usage (in chat endpoint, after retrieval, before RAG graph):
    from app.services.memory.adaptation.context_ranker import ContextRanker

    ranker = ContextRanker(user_id="default_user")
    reranked_docs = ranker.rerank(
        docs=result_from_retriever,
        document_id=request.document_id,
    )
    # Then pass reranked_docs into the RAG graph state as top_docs
"""

from __future__ import annotations

from typing import Optional

from langchain_core.documents import Document

from app.storage.user_memory import LearningMemory, PageInteraction
from app.core.logging import get_logger

logger = get_logger(__name__)


class ContextRanker:
    """
    Re-ranks retrieved Documents by combining retrieval order with
    struggle-based boosting from LearningMemory.

    Parameters
    ----------
    user_id : str
    struggle_boost_weight : float
        How much to weight struggle signals vs retrieval order.
        0.0 = pure retrieval order (no adaptation)
        1.0 = struggle signals have equal weight to retrieval order
        Default 0.4 gives a meaningful but not overwhelming boost.
    """

    def __init__(
        self,
        user_id: str = "default_user",
        struggle_boost_weight: float = 0.4,
    ) -> None:
        self.user_id = user_id
        self.struggle_boost_weight = struggle_boost_weight
        self.memory = LearningMemory(user_id=user_id)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                      #
    # ------------------------------------------------------------------ #

    def _page_from_doc(self, doc: Document) -> Optional[int]:
        """Extract 0-indexed page number from Document metadata."""
        return doc.metadata.get("page")

    def _doc_id_from_doc(self, doc: Document, document_id: str) -> str:
        """
        Map a retrieved Document back to the storage document_id.

        PyMuPDFLoader sets doc.metadata["source"] to the full PDF path.
        We use the passed document_id directly since all docs in a
        single RAG call come from the same document.
        """
        return document_id

    def _struggle_boost(self, page: Optional[PageInteraction]) -> float:
        """
        Compute a boost score [0.0, 1.0] based on struggle signals.

        Higher score = more struggle = boost this chunk higher so the
        LLM focuses its answer on the user's weak areas.
        """
        if page is None:
            return 0.0

        score = 0.0

        # Quiz performance (strongest signal)
        if page.quiz_attempted and page.quiz_score is not None:
            if page.quiz_score < 0.5:
                score += 0.5
            elif page.quiz_score < 0.7:
                score += 0.3

        # Self-assessment
        if page.self_assessment == "not_clear":
            score += 0.4
        elif page.self_assessment == "somewhat_clear":
            score += 0.2

        # Repeated help-seeking
        total_help = page.reframes_count + page.explanations_count
        if total_help > 5:
            score += 0.3
        elif total_help > 3:
            score += 0.2
        elif total_help > 1:
            score += 0.1

        # Cap at 1.0
        return min(score, 1.0)

    # ------------------------------------------------------------------ #
    # Main reranking                                                        #
    # ------------------------------------------------------------------ #

    def rerank(
        self,
        docs: list[Document],
        document_id: str,
    ) -> list[Document]:
        """
        Re-rank retrieved Documents using struggle-based boosting.

        Parameters
        ----------
        docs        : list of Documents from the retriever (ordered best-first)
        document_id : the storage document_id for this RAG call

        Returns
        -------
        list[Document] re-ordered, best first, with struggle signals factored in.
        """
        if not docs:
            return docs

        scored: list[tuple[float, Document]] = []

        for rank, doc in enumerate(docs):
            # Base score: invert rank so rank 0 (best) gets highest score
            # Normalise to [0, 1] range
            base_score = 1.0 - (rank / len(docs))

            # Look up struggle boost for this page
            page_num = self._page_from_doc(doc)
            page_interaction = None

            if page_num is not None:
                doc_pages = self.memory.memory.get(document_id, {})
                # PyMuPDF uses 0-indexed pages, LearningMemory uses whatever
                # the frontend sends (typically 1-indexed). Try both.
                page_interaction = (
                    doc_pages.get(page_num)
                    or doc_pages.get(page_num + 1)
                )

            boost = self._struggle_boost(page_interaction)

            # Combined score
            final_score = base_score + self.struggle_boost_weight * boost

            scored.append((final_score, doc))

            logger.debug(
                "ContextRanker: page=%s base=%.2f boost=%.2f final=%.2f",
                page_num, base_score, boost, final_score,
            )

        # Sort by final score, highest first
        scored.sort(key=lambda x: x[0], reverse=True)
        reranked = [doc for _, doc in scored]

        # Log if order changed
        original_pages = [self._page_from_doc(d) for d in docs]
        reranked_pages = [self._page_from_doc(d) for d in reranked]
        if original_pages != reranked_pages:
            logger.info(
                "ContextRanker: reordered pages %s → %s",
                original_pages, reranked_pages,
            )

        return reranked