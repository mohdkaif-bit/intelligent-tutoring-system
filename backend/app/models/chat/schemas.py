"""
Pydantic schemas for chat operations.
"""
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
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "sample_doc_abc123",
                "question": "What is the main concept in this section?",
                "mode": "quick_answer",
                "page_number": 5,
                "history": []
            }
        }


class ChatResponse(BaseModel):
    """Response from chat system."""
    success: bool
    answer: str
    mode: str
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "answer": "The main concept is...",
                "mode": "quick_answer",
                "error": None
            }
        }


class ChatHistory(BaseModel):
    """Chat conversation history."""
    role: Literal["user", "assistant"]
    content: str