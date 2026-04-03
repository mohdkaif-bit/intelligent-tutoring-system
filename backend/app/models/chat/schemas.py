"""
Pydantic schemas for chat operations.
"""
import uuid
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class ChatRequest(BaseModel):
    """Request for chat/question answering."""
    document_id: str
    question: str
    mode: Literal[
        "quick_answer",
        "explain_concept",
        "step_by_step",
        "practice_problems",
        "deep_analysis"
    ] = "quick_answer"
    page_number: Optional[int] = None
    history: List[dict] = Field(default_factory=list)
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Session ID for grouping queries in evaluation logs."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "sample_doc_abc123",
                "question": "What is the main concept in this section?",
                "mode": "quick_answer",
                "page_number": 5,
                "history": [],
                "session_id": "my-session-123"
            }
        }


class ChatResponse(BaseModel):
    """Response from chat system."""
    success: bool
    answer: str
    mode: str
    error: Optional[str] = None

    # Adaptation suggestion fields
    suggested_mode: Optional[str] = Field(
        default=None,
        description=(
            "A better mode suggested by the adaptation system based on your "
            "learning history. None if the current mode is already optimal."
        )
    )
    suggestion_reason: Optional[str] = Field(
        default=None,
        description="Human-readable reason for the mode suggestion."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "answer": "The main concept is...",
                "mode": "quick_answer",
                "error": None,
                "suggested_mode": "step_by_step",
                "suggestion_reason": (
                    "You scored 40% on the quiz for this page. "
                    "Step by step mode may help build understanding."
                )
            }
        }


class ChatHistory(BaseModel):
    """Chat conversation history."""
    role: Literal["user", "assistant"]
    content: str