"""
Generation Metrics
------------------
Evaluates the LLM output component of the RAG pipeline.

Metrics
-------
- Exact Match (EM)        : normalised string equality
- Token F1                : token-overlap F1 between answer and expected
- Semantic Similarity     : cosine sim between embeddings (or Jaccard fallback)
- Faithfulness            : how grounded the answer is in retrieved context
- Context Utilization     : fraction of retrieved chunks actually used
- Chunk Relevance         : how relevant retrieved chunks are to the query
- Answer Completeness     : how well the answer covers key points in chunks
"""

from __future__ import annotations

import logging
import re
import string
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Text helpers                                                          #
# ------------------------------------------------------------------ #

def _normalize(text: str) -> str:
    text = text.lower().translate(str.maketrans("", "", string.punctuation))
    return " ".join(text.split())


def _tokens(text: str) -> list[str]:
    return _normalize(text).split()


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ------------------------------------------------------------------ #
# Result dataclass                                                      #
# ------------------------------------------------------------------ #

@dataclass
class GenerationResult:
    """All generation metric scores for a single query-answer pair."""
    query: str
    generated_answer: str
    expected_answer: str | None
    # Supervised metrics (require expected_answer)
    exact_match: bool | None
    f1_score: float | None
    semantic_similarity: float | None
    # Unsupervised metrics (no expected_answer needed)
    faithfulness_score: float
    context_utilization: float
    context_chunks: list[str]
    # NEW unsupervised metrics
    chunk_relevance: float = 0.0
    answer_completeness: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "exact_match": self.exact_match,
            "f1_score": self.f1_score,
            "semantic_similarity": self.semantic_similarity,
            "faithfulness_score": self.faithfulness_score,
            "context_utilization": self.context_utilization,
            "chunk_relevance": self.chunk_relevance,
            "answer_completeness": self.answer_completeness,
        }


# ------------------------------------------------------------------ #
# Main class                                                            #
# ------------------------------------------------------------------ #

class GenerationMetrics:
    """
    Compute generation-quality metrics for RAG answers.

    Parameters
    ----------
    embeddings : optional
        HuggingFaceEmbeddings instance from VectorRetriever.
    groq_client : optional
        GroqClient instance for LLM-as-judge faithfulness scoring.
    """

    def __init__(self, embeddings=None, groq_client=None) -> None:
        self.embeddings = embeddings
        self.groq_client = groq_client

    # ------------------------------------------------------------------ #
    # 1. Exact Match                                                        #
    # ------------------------------------------------------------------ #

    def exact_match(self, generated: str, expected: str) -> bool:
        return _normalize(generated) == _normalize(expected)

    # ------------------------------------------------------------------ #
    # 2. Token F1                                                           #
    # ------------------------------------------------------------------ #

    def token_f1(self, generated: str, expected: str) -> float:
        gen_toks = _tokens(generated)
        exp_toks = _tokens(expected)
        if not gen_toks or not exp_toks:
            return float(gen_toks == exp_toks)
        common = Counter(gen_toks) & Counter(exp_toks)
        n_common = sum(common.values())
        if n_common == 0:
            return 0.0
        precision = n_common / len(gen_toks)
        recall = n_common / len(exp_toks)
        return 2 * precision * recall / (precision + recall)

    # ------------------------------------------------------------------ #
    # 3. Semantic Similarity                                                #
    # ------------------------------------------------------------------ #

    def semantic_similarity(self, generated: str, expected: str) -> float:
        if self.embeddings is not None:
            try:
                vecs = self.embeddings.embed_documents([generated, expected])
                return _cosine(np.array(vecs[0]), np.array(vecs[1]))
            except Exception as exc:
                logger.warning("Embedding model failed (%s); falling back to Jaccard.", exc)
        gen_set = set(_tokens(generated))
        exp_set = set(_tokens(expected))
        if not gen_set and not exp_set:
            return 1.0
        if not gen_set or not exp_set:
            return 0.0
        return len(gen_set & exp_set) / len(gen_set | exp_set)

    # ------------------------------------------------------------------ #
    # 4. Faithfulness                                                       #
    # ------------------------------------------------------------------ #

    def faithfulness_score(self, generated_answer: str, context_chunks: list[str]) -> float:
        if not context_chunks:
            return 0.0
        if self.groq_client is not None:
            return self._faithfulness_llm_judge(generated_answer, context_chunks)
        return self._faithfulness_heuristic(generated_answer, context_chunks)

    def _faithfulness_heuristic(self, answer: str, context_chunks: list[str]) -> float:
        sentences = [s.strip() for s in re.split(r"[.!?]", answer) if s.strip()]
        if not sentences:
            return 0.0
        context_words = set(_tokens(" ".join(context_chunks)))
        grounded = 0
        for sent in sentences:
            sent_words = set(_tokens(sent))
            if not sent_words:
                continue
            if len(sent_words & context_words) / len(sent_words) >= 0.5:
                grounded += 1
        return grounded / len(sentences)

    def _faithfulness_llm_judge(self, answer: str, context_chunks: list[str]) -> float:
        context_text = "\n\n".join(
            f"[Chunk {i + 1}]: {chunk}" for i, chunk in enumerate(context_chunks)
        )
        prompt = (
            "You are an expert evaluator for a tutoring system. "
            "Given the retrieved context and a generated answer, "
            "score how faithful the answer is to the context.\n\n"
            f"CONTEXT:\n{context_text}\n\n"
            f"GENERATED ANSWER:\n{answer}\n\n"
            "Respond with ONLY a JSON object, no extra text:\n"
            '{"score": <float 0.0-1.0>, "reasoning": "<one sentence>"}\n'
            "1.0 = completely grounded in context. 0.0 = complete hallucination."
        )
        try:
            import json
            response = self.groq_client.invoke(prompt, mode="quick_answer")
            match = re.search(r"\{.*?\}", response, re.DOTALL)
            if match:
                data = json.loads(match.group())
                score = float(data.get("score", 0.0))
                return max(0.0, min(1.0, score))
        except Exception as exc:
            logger.warning("LLM-judge faithfulness failed (%s); falling back to heuristic.", exc)
        return self._faithfulness_heuristic(answer, context_chunks)

    # ------------------------------------------------------------------ #
    # 5. Context Utilization                                                #
    # ------------------------------------------------------------------ #

    def context_utilization(self, generated_answer: str, context_chunks: list[str]) -> float:
        if not context_chunks:
            return 0.0
        answer_words = set(_tokens(generated_answer))
        utilized = 0
        for chunk in context_chunks:
            chunk_words = set(_tokens(chunk))
            if not chunk_words:
                continue
            overlap = len(answer_words & chunk_words) / len(chunk_words)
            if overlap >= 0.20:
                utilized += 1
        return utilized / len(context_chunks)

    # ------------------------------------------------------------------ #
    # 6. NEW — Chunk Relevance                                              #
    # ------------------------------------------------------------------ #

    def chunk_relevance(self, query: str, context_chunks: list[str]) -> float:
        """
        How relevant are the retrieved chunks to the query?

        For each chunk, compute token overlap between query and chunk.
        A chunk is considered relevant if >= 30% of query tokens
        appear in the chunk.

        Returns float in [0, 1].
        1.0 = all chunks are relevant to the query.
        0.0 = no chunks are relevant to the query.
        """
        if not context_chunks:
            return 0.0

        query_words = set(_tokens(query))
        if not query_words:
            return 0.0

        relevant_chunks = 0
        for chunk in context_chunks:
            chunk_words = set(_tokens(chunk))
            if not chunk_words:
                continue
            overlap = len(query_words & chunk_words) / len(query_words)
            if overlap >= 0.30:
                relevant_chunks += 1

        return relevant_chunks / len(context_chunks)

    # ------------------------------------------------------------------ #
    # 7. NEW — Answer Completeness                                          #
    # ------------------------------------------------------------------ #

    def answer_completeness(
        self, generated_answer: str, context_chunks: list[str]
    ) -> float:
        """
        Does the answer cover the key points present in the context?

        Extracts high-frequency content words from context chunks
        (excluding stopwords) and checks what fraction appear in
        the generated answer.

        Returns float in [0, 1].
        1.0 = answer covers all key points from context.
        0.0 = answer misses all key points from context.
        """
        if not context_chunks or not generated_answer:
            return 0.0

        # Basic English stopwords to filter noise
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "this", "that", "these",
            "those", "it", "its", "and", "or", "but", "if", "then",
            "than", "so", "yet", "both", "either", "not", "no", "nor",
        }

        # Count word frequencies across all context chunks
        context_text = " ".join(context_chunks)
        context_token_counts = Counter(_tokens(context_text))

        # Keep only content words (not stopwords) that appear 2+ times
        key_terms = {
            word for word, count in context_token_counts.items()
            if count >= 2 and word not in stopwords and len(word) > 3
        }

        if not key_terms:
            return 0.0

        answer_words = set(_tokens(generated_answer))
        covered = len(key_terms & answer_words)

        return covered / len(key_terms)

    # ------------------------------------------------------------------ #
    # Single evaluation                                                     #
    # ------------------------------------------------------------------ #

    def evaluate_single(
        self,
        query: str,
        generated_answer: str,
        context_chunks: list[str],
        expected_answer: str | None = None,
    ) -> GenerationResult:
        em = f1 = sem_sim = None
        if expected_answer is not None:
            em = self.exact_match(generated_answer, expected_answer)
            f1 = self.token_f1(generated_answer, expected_answer)
            sem_sim = self.semantic_similarity(generated_answer, expected_answer)

        return GenerationResult(
            query=query,
            generated_answer=generated_answer,
            expected_answer=expected_answer,
            exact_match=em,
            f1_score=f1,
            semantic_similarity=sem_sim,
            faithfulness_score=self.faithfulness_score(generated_answer, context_chunks),
            context_utilization=self.context_utilization(generated_answer, context_chunks),
            context_chunks=context_chunks,
            chunk_relevance=self.chunk_relevance(query, context_chunks),        # NEW
            answer_completeness=self.answer_completeness(generated_answer, context_chunks),  # NEW
        )

    # ------------------------------------------------------------------ #
    # Batch evaluation                                                      #
    # ------------------------------------------------------------------ #

    def evaluate_batch(self, batch: list[dict[str, Any]]) -> dict[str, Any]:
        if not batch:
            return self._zero_aggregate()

        results: list[GenerationResult] = []
        for item in batch:
            results.append(
                self.evaluate_single(
                    query=item["query"],
                    generated_answer=item["generated_answer"],
                    context_chunks=item.get("context_chunks", []),
                    expected_answer=item.get("expected_answer"),
                )
            )

        supervised = [r for r in results if r.expected_answer is not None]

        return {
            "results": results,
            "mean_f1": (
                float(np.mean([r.f1_score for r in supervised]))
                if supervised else None
            ),
            "mean_semantic_similarity": (
                float(np.mean([r.semantic_similarity for r in supervised]))
                if supervised else None
            ),
            "mean_faithfulness": float(np.mean([r.faithfulness_score for r in results])),
            "mean_context_utilization": float(np.mean([r.context_utilization for r in results])),
            "mean_chunk_relevance": float(np.mean([r.chunk_relevance for r in results])),          # NEW
            "mean_answer_completeness": float(np.mean([r.answer_completeness for r in results])),  # NEW
            "exact_match_rate": (
                float(np.mean([float(r.exact_match) for r in supervised]))
                if supervised else None
            ),
        }

    def _zero_aggregate(self) -> dict[str, Any]:
        return {
            "results": [],
            "mean_f1": None,
            "mean_semantic_similarity": None,
            "mean_faithfulness": 0.0,
            "mean_context_utilization": 0.0,
            "mean_chunk_relevance": 0.0,       # NEW
            "mean_answer_completeness": 0.0,   # NEW
            "exact_match_rate": None,
        }