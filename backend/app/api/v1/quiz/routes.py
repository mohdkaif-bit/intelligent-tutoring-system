"""
Quiz API Routes
Handles quiz generation and evaluation.
"""
from fastapi import APIRouter, HTTPException, status
from typing import List

from app.models.quiz.schemas import (
    QuizQuestion,
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizSubmitRequest,
    QuizEvaluationResponse
)
from app.storage.documents import DocumentStorage
from app.services.pdf.pdf_processor import PDFProcessor
from app.services.quiz.generator.quiz_generator import QuizGenerator
from app.services.quiz.evaluator.quiz_evaluator import QuizEvaluator
from app.storage.user_memory import LearningMemory
from app.core.logging import get_logger
from app.api.v1.auth.dependencies import CurrentUser


logger = get_logger(__name__)
router = APIRouter()


@router.post("/generate", response_model=QuizGenerateResponse)
async def generate_quiz(request: QuizGenerateRequest, user: CurrentUser):
    """
    Generate quiz questions from a PDF page.

    Args:
        request: Quiz generation request with document_id, page_number, num_questions

    Returns:
        Generated quiz questions
    """
    try:
        # Get document path
        doc_storage = DocumentStorage(user_id=user.id)
        doc_path = doc_storage.get_document_path(request.document_id)

        if not doc_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {request.document_id} not found"
            )

        # Extract page text
        page_text = PDFProcessor.extract_page_text(doc_path, request.page_number)

        # Check if page has enough content
        word_count = len(page_text.split())
        if word_count < 50:
            return QuizGenerateResponse(
                success=False,
                questions=[],
                page_number=request.page_number,
                error="Page has too little text to generate meaningful questions (minimum 50 words required)"
            )

        # Generate quiz
        quiz_generator = QuizGenerator()
        questions = quiz_generator.generate_from_page(
            page_text=page_text,
            page_number=request.page_number,
            num_questions=request.num_questions
        )

        if not questions:
            return QuizGenerateResponse(
                success=False,
                questions=[],
                page_number=request.page_number,
                error="Could not generate questions from this page content"
            )

        # Update learning memory - quiz attempted
        memory = LearningMemory(user_id=user.id)
        page_interaction = memory.get_or_create_page(
            request.document_id,
            request.page_number
        )
        page_interaction.quiz_attempted = True
        memory._save_memory()

        logger.info(
            "Generated %d quiz questions for page %d (user=%s)",
            len(questions), request.page_number, user.id,
        )

        return QuizGenerateResponse(
            success=True,
            questions=[QuizQuestion(**q) for q in questions],
            page_number=request.page_number,
            error=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generating quiz: %s", e)
        return QuizGenerateResponse(
            success=False,
            questions=[],
            page_number=request.page_number,
            error=f"Quiz generation error: {str(e)}"
        )


@router.post("/evaluate", response_model=QuizEvaluationResponse)
async def evaluate_quiz(request: QuizSubmitRequest, questions: List[QuizQuestion], user: CurrentUser):
    """
    Evaluate quiz submission.

    Args:
        request: Quiz submission with answers
        questions: Original quiz questions (passed in request body)

    Returns:
        Evaluation results with score and feedback
    """
    try:
        # Convert questions to dict format
        questions_dict = [q.dict() for q in questions]

        # Evaluate quiz
        evaluator = QuizEvaluator()
        evaluation = evaluator.evaluate_quiz(
            answers=request.answers,
            questions=questions_dict
        )

        # Update learning memory with score
        memory = LearningMemory(user_id=user.id)
        memory.update_quiz(
            document_id=request.document_id,
            page_number=request.page_number,
            score=evaluation["score"]
        )

        logger.info(
            "Evaluated quiz: %d/%d correct (user=%s)",
            evaluation["correct_count"], evaluation["total_questions"], user.id,
        )

        return QuizEvaluationResponse(
            success=True,
            score=evaluation["score"],
            correct_count=evaluation["correct_count"],
            total_questions=evaluation["total_questions"],
            results=evaluation["results"]
        )

    except Exception as e:
        logger.error("Error evaluating quiz: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate quiz: {str(e)}"
        )


@router.get("/stats/{document_id}")
async def get_quiz_stats(document_id: str, user: CurrentUser):
    """
    Get quiz statistics for a specific document.

    Args:
        document_id: Document identifier

    Returns:
        Quiz statistics including scores, attempts, and performance metrics
    """
    try:
        memory = LearningMemory(user_id=user.id)

        if document_id not in memory.memory:
            return {
                "success": True,
                "total_quizzes_taken": 0,
                "average_score": 0,
                "best_score": 0,
                "last_quiz_date": None,
                "total_questions_answered": 0,
                "total_correct_answers": 0,
                "quizzes": []
            }

        pages = memory.memory[document_id]
        quizzes = []
        total_score = 0
        quiz_count = 0
        best_score = 0
        last_quiz_date = None
        total_questions = 0
        total_correct = 0

        for page_num, interaction in pages.items():
            if interaction.quiz_attempted and interaction.quiz_score is not None:
                score_percent = interaction.quiz_score * 100
                quizzes.append({
                    "page_number": page_num,
                    "score": score_percent,
                    "timestamp": interaction.last_interaction_timestamp
                })
                total_score += interaction.quiz_score
                quiz_count += 1
                best_score = max(best_score, score_percent)

                # Estimate questions answered (default 5 per quiz)
                questions_for_this_quiz = 5
                correct_for_this_quiz = int(questions_for_this_quiz * interaction.quiz_score)
                total_questions += questions_for_this_quiz
                total_correct += correct_for_this_quiz

                if last_quiz_date is None or interaction.last_interaction_timestamp > last_quiz_date:
                    last_quiz_date = interaction.last_interaction_timestamp

        avg_score = (total_score / quiz_count * 100) if quiz_count > 0 else 0

        logger.info(
            "Retrieved quiz stats for %s: %d quizzes, avg score %.1f%% (user=%s)",
            document_id, quiz_count, avg_score, user.id,
        )

        return {
            "success": True,
            "total_quizzes_taken": quiz_count,
            "average_score": round(avg_score, 2),
            "best_score": round(best_score, 2),
            "last_quiz_date": last_quiz_date,
            "total_questions_answered": total_questions,
            "total_correct_answers": total_correct,
            "quizzes": sorted(
                quizzes,
                key=lambda x: x["timestamp"] if x["timestamp"] else "",
                reverse=True,
            )
        }

    except Exception as e:
        logger.error("Error getting quiz stats for %s: %s", document_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quiz stats: {str(e)}"
        )