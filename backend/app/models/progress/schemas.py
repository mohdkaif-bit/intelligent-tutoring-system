"""
Pydantic schemas for learning progress tracking.
UPDATED to match frontend expectations
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class PageInteractionUpdate(BaseModel):
    """Update for page interaction."""
    document_id: str
    page_number: int
    interaction_type: Literal[
        "view", "selection", "reframe", "explanation", "quiz", "self_assessment"
    ]
    time_spent: Optional[int] = None
    quiz_score: Optional[float] = None
    self_assessment: Optional[Literal["not_clear", "somewhat_clear", "very_clear"]] = None


class ProgressResponse(BaseModel):
    """
    User's learning progress summary.
    UPDATED: Fields match what frontend Home.tsx expects
    """
    # Frontend expected fields (REQUIRED)
    study_time_minutes: int = Field(default=0, description="Total study time in minutes")
    total_pages_viewed: int = Field(default=0, description="Total pages viewed across all documents")
    total_questions_asked: int = Field(default=0, description="Total questions asked in chat")
    total_quizzes_completed: int = Field(default=0, description="Total quizzes completed")
    average_quiz_score: Optional[float] = Field(default=None, description="Average quiz score as percentage (0-100)")
    
    # Additional analytics (OPTIONAL - frontend doesn't use these but they're useful)
    total_pages_uploaded: Optional[int] = Field(default=0, description="Total pages in all uploaded documents")
    pages_with_engagement: Optional[int] = Field(default=0, description="Pages with active interaction")
    pages_needing_attention: Optional[int] = Field(default=0, description="Pages that may need review")
    completion_rate: Optional[float] = Field(default=0.0, description="Percentage of pages viewed")
    engagement_rate: Optional[float] = Field(default=0.0, description="Percentage of pages with engagement")


class RevisionSuggestion(BaseModel):
    """Suggestion for page revision."""
    document_id: str
    page_number: int
    priority: int
    reasons: List[str]
    suggestion: str