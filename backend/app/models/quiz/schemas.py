"""
Pydantic schemas for quiz operations.
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class QuizQuestion(BaseModel):
    """Single quiz question with MCQ options."""
    question: str
    options: Dict[str, str] = Field(
        description="Options A, B, C, D"
    )
    correct_answer: str = Field(
        description="Correct option letter (A/B/C/D)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is the main concept discussed?",
                "options": {
                    "A": "First option",
                    "B": "Second option",
                    "C": "Third option",
                    "D": "Fourth option"
                },
                "correct_answer": "A"
            }
        }


class QuizGenerateRequest(BaseModel):
    """Request to generate quiz questions."""
    document_id: str
    page_number: int
    num_questions: int = Field(default=3, ge=1, le=5)
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "sample_doc_abc123",
                "page_number": 5,
                "num_questions": 3
            }
        }


class QuizGenerateResponse(BaseModel):
    """Response with generated quiz questions."""
    success: bool
    questions: List[QuizQuestion]
    page_number: int
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "questions": [],
                "page_number": 5,
                "error": None
            }
        }


class QuizSubmitRequest(BaseModel):
    """Student's quiz submission."""
    document_id: str
    page_number: int
    answers: Dict[int, str] = Field(
        description="Question index to student answer (A/B/C/D)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "sample_doc_abc123",
                "page_number": 5,
                "answers": {
                    0: "A",
                    1: "B",
                    2: "C"
                }
            }
        }


class QuizEvaluationResponse(BaseModel):
    """Evaluation results for submitted quiz."""
    success: bool
    score: float = Field(description="Score between 0.0 and 1.0")
    correct_count: int
    total_questions: int
    results: List[str] = Field(
        description="List of 'CORRECT' or 'INCORRECT' for each question"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "score": 0.67,
                "correct_count": 2,
                "total_questions": 3,
                "results": ["CORRECT", "INCORRECT", "CORRECT"]
            }
        }