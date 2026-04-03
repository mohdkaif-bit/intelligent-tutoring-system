"""
Eval Logger
-----------
Silently logs real RAG interactions per session for offline evaluation.
"""
from __future__ import annotations

import json
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

EVAL_LOG_DIR = settings.STORAGE_BASE_DIR / "evaluation" / "logs"


def log_interaction(
    session_id: str,
    query: str,
    generated_answer: str,
    context_chunks: list[str],
    retrieved_ids: list[str],
    user_id: str = "default_user",
) -> None:
    """Append a single RAG interaction to the session log file."""
    try:
        session_dir = EVAL_LOG_DIR / user_id
        session_dir.mkdir(parents=True, exist_ok=True)

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "query": query,
            "generated_answer": generated_answer,
            "context_chunks": context_chunks,
            "retrieved_ids": retrieved_ids,
            "relevant_ids": [],
        }

        log_file = session_dir / f"session_{session_id}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        logger.debug("Logged interaction for session %s", session_id)
    except Exception as exc:
        # Never crash the chat endpoint due to logging failure
        logger.warning("eval_logger failed silently: %s", exc)


def load_session(
    session_id: str,
    user_id: str = "default_user",
) -> list[dict]:
    """Load all interactions for a session."""
    log_file = EVAL_LOG_DIR / user_id / f"session_{session_id}.jsonl"
    if not log_file.exists():
        return []
    with open(log_file, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def list_sessions(user_id: str = "default_user") -> list[str]:
    """List all session IDs that have logged interactions, newest first."""
    session_dir = EVAL_LOG_DIR / user_id
    if not session_dir.exists():
        return []
    return [
        f.stem.replace("session_", "")
        for f in sorted(session_dir.glob("session_*.jsonl"), reverse=True)
    ]
