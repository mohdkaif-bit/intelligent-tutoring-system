"""
Evaluation Router
-----------------
Exposes RAG evaluation endpoints under /api/v1/evaluation.

Endpoints
---------
POST /api/v1/evaluation/run
    Evaluate a batch of query-answer pairs.

GET  /api/v1/evaluation/history/{user_id}
    List saved evaluation reports for a user.

GET  /api/v1/evaluation/sessions/{user_id}
    List all session IDs that have logged interactions.

POST /api/v1/evaluation/run-session/{user_id}/{session_id}
    Run evaluation averaged across all queries in a session.

GET  /api/v1/evaluation/session-logs/{user_id}/{session_id}
    Preview raw logged interactions for a session.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger
from app.services.rag.metrics import RAGEvaluator
from app.services.rag.eval_logger import load_session, list_sessions, log_interaction

logger = get_logger(__name__)

router = APIRouter()

EVAL_STORAGE_DIR = settings.STORAGE_BASE_DIR / "evaluation"


# ------------------------------------------------------------------ #
# Request / Response schemas                                            #
# ------------------------------------------------------------------ #

class EvalItem(BaseModel):
    """A single query-answer pair to evaluate."""
    query: str
    generated_answer: str
    context_chunks: list[str] = Field(
        description="Text of retrieved chunks: [doc.page_content for doc in top_docs]"
    )
    expected_answer: str | None = Field(
        default=None,
        description="Ground-truth answer. Required for EM, F1, and semantic similarity."
    )
    retrieved_ids: list[str] | None = Field(
        default=None,
        description=(
            "Pre-computed doc IDs in retrieval order. "
            "Format: 'filename__pN' (e.g. 'ISLP_website.pdf_683d1248c5be__p3'). "
            "Use retrieval_metrics.docs_to_ids(top_docs) to generate these."
        )
    )
    relevant_ids: list[str] | None = Field(
        default=None,
        description="Ground-truth relevant doc IDs (same format as retrieved_ids)."
    )


class EvalRequest(BaseModel):
    user_id: str = "default_user"
    k: int = Field(default=5, ge=1, le=20)
    use_llm_judge: bool = Field(default=False)
    use_embeddings: bool = Field(default=True)
    dataset: list[EvalItem]


class EvalResponse(BaseModel):
    retrieval: dict[str, Any]
    generation: dict[str, Any]
    per_query: list[dict[str, Any]]
    metadata: dict[str, Any]
    report_path: str


# ------------------------------------------------------------------ #
# Helpers                                                               #
# ------------------------------------------------------------------ #

def _build_evaluator(
    k: int,
    user_id: str,
    use_embeddings: bool,
    use_llm_judge: bool,
) -> RAGEvaluator:
    groq_client = None
    if use_llm_judge:
        try:
            from app.services.llm.groq_client import get_llm_client
            groq_client = get_llm_client()
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialise GroqClient for LLM-judge: {exc}",
            )

    embeddings = None
    if use_embeddings:
        try:
            from app.services.rag.retriever.vector_retriever import VectorRetriever
            vr = VectorRetriever(user_id=user_id)
            embeddings = vr.get_embeddings_model()
        except Exception as exc:
            logger.warning("Could not load embedding model (%s). Falling back to Jaccard.", exc)

    return RAGEvaluator(retrieval_k=k, embeddings=embeddings, groq_client=groq_client)


# ------------------------------------------------------------------ #
# Routes                                                                #
# ------------------------------------------------------------------ #

@router.post("/run", response_model=EvalResponse)
async def run_evaluation(request: EvalRequest) -> EvalResponse:
    """Evaluate RAG quality across a batch of query-answer pairs."""
    if not request.dataset:
        raise HTTPException(status_code=400, detail="Dataset cannot be empty.")

    evaluator = _build_evaluator(
        k=request.k,
        user_id=request.user_id,
        use_embeddings=request.use_embeddings,
        use_llm_judge=request.use_llm_judge,
    )

    eval_dataset = []
    for item in request.dataset:
        entry: dict[str, Any] = {
            "query": item.query,
            "generated_answer": item.generated_answer,
            "context_chunks": item.context_chunks,
        }
        if item.expected_answer is not None:
            entry["expected_answer"] = item.expected_answer
        if item.retrieved_ids is not None:
            entry["retrieved_ids"] = item.retrieved_ids
            entry["relevant_ids"] = item.relevant_ids or []
        eval_dataset.append(entry)

    try:
        report = evaluator.run(eval_dataset)
    except Exception as exc:
        logger.error("RAG evaluation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}")

    report_path = evaluator.save_report(report, user_id=request.user_id)

    return EvalResponse(
        retrieval=report["retrieval"],
        generation=report["generation"],
        per_query=report["per_query"],
        metadata=report["metadata"],
        report_path=report_path,
    )


@router.get("/history/{user_id}")
async def get_evaluation_history(user_id: str) -> list[dict[str, Any]]:
    """List saved evaluation reports for a user, newest first."""
    user_dir = EVAL_STORAGE_DIR / user_id
    if not user_dir.exists():
        return []

    reports = []
    for path in sorted(user_dir.glob("rag_eval_*.json"), reverse=True):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            reports.append({
                "filename": path.name,
                "timestamp": data.get("metadata", {}).get("timestamp"),
                "session_id": data.get("metadata", {}).get("session_id"),
                "n_queries": data.get("metadata", {}).get("n_queries"),
                "mrr": data.get("retrieval", {}).get("mrr"),
                "mean_faithfulness": data.get("generation", {}).get("mean_faithfulness"),
                "mean_f1": data.get("generation", {}).get("mean_f1"),
            })
        except Exception:
            continue

    return reports


@router.get("/sessions/{user_id}")
async def get_user_sessions(user_id: str) -> list[str]:
    """List all session IDs that have logged real interactions."""
    return list_sessions(user_id=user_id)


@router.get("/session-logs/{user_id}/{session_id}")
async def get_session_logs(
    user_id: str,
    session_id: str,
) -> list[dict[str, Any]]:
    """Preview all raw logged interactions for a session."""
    interactions = load_session(session_id=session_id, user_id=user_id)
    if not interactions:
        raise HTTPException(
            status_code=404,
            detail=f"No interactions found for session '{session_id}'."
        )
    return interactions


@router.post("/run-session/{user_id}/{session_id}", response_model=EvalResponse)
async def run_session_evaluation(
    user_id: str,
    session_id: str,
    k: int = 5,
    use_llm_judge: bool = False,
    use_embeddings: bool = False,
) -> EvalResponse:
    """
    Run evaluation averaged across all queries logged in a session.
    Call this as a developer after users have chatted — metrics are
    averaged over every query in the session automatically.
    """
    dataset = load_session(session_id=session_id, user_id=user_id)

    if not dataset:
        raise HTTPException(
            status_code=404,
            detail=f"No interactions found for session '{session_id}'."
        )

    evaluator = _build_evaluator(
        k=k,
        user_id=user_id,
        use_embeddings=use_embeddings,
        use_llm_judge=use_llm_judge,
    )

    try:
        report = evaluator.run(dataset)
    except Exception as exc:
        logger.error("Session evaluation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}")

    # Tag the report with session metadata
    report["metadata"]["session_id"] = session_id
    report["metadata"]["n_queries"] = len(dataset)

    report_path = evaluator.save_report(
        report,
        user_id=user_id,
        filename=f"rag_eval_session_{session_id}.json",
    )

    return EvalResponse(
        retrieval=report["retrieval"],
        generation=report["generation"],
        per_query=report["per_query"],
        metadata=report["metadata"],
        report_path=report_path,
    )