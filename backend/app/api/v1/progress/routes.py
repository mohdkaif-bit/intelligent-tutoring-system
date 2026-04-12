"""
Progress API Routes - FIXED
Handles learning progress tracking and analytics.
"""
from fastapi import APIRouter, HTTPException, status
from typing import List
from datetime import datetime, timedelta

from app.models.progress.schemas import (
    PageInteractionUpdate,
    ProgressResponse,
    RevisionSuggestion
)
from app.storage.user_memory import LearningMemory
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

DEFAULT_USER_ID = "default_user"


@router.post("/update")
async def update_interaction(update: PageInteractionUpdate):
    """
    Update page interaction.

    Args:
        update: Page interaction update

    Returns:
        Success confirmation
    """
    try:
        memory = LearningMemory(user_id=DEFAULT_USER_ID)

        # Route to appropriate update method based on interaction type
        if update.interaction_type in ("view", "page_view"):       # ← FIXED
            memory.update_page_view(
                document_id=update.document_id,
                page_number=update.page_number,
                time_spent=update.time_spent or 0
            )
        elif update.interaction_type == "selection":
            memory.update_selection(
                document_id=update.document_id,
                page_number=update.page_number
            )
        elif update.interaction_type == "reframe":
            memory.update_reframe(
                document_id=update.document_id,
                page_number=update.page_number
            )
        elif update.interaction_type == "explanation":
            memory.update_explanation(
                document_id=update.document_id,
                page_number=update.page_number
            )
        elif update.interaction_type == "quiz":
            if update.quiz_score is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="quiz_score required for quiz interaction"
                )
            memory.update_quiz(
                document_id=update.document_id,
                page_number=update.page_number,
                score=update.quiz_score
            )
        elif update.interaction_type == "self_assessment":
            if update.self_assessment is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="self_assessment required for self_assessment interaction"
                )
            memory.update_self_assessment(
                document_id=update.document_id,
                page_number=update.page_number,
                assessment=update.self_assessment
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown interaction type: {update.interaction_type}"
            )

        logger.info(
            "Updated %s interaction for page %s",
            update.interaction_type, update.page_number,
        )

        return {
            "success": True,
            "message": "Interaction updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating interaction: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update interaction: {str(e)}"
        )


@router.get("/account")
async def get_account_progress():
    """
    Get account-level learning progress.

    Returns:
        Progress metrics across all documents
    """
    try:
        memory = LearningMemory(user_id=DEFAULT_USER_ID)
        progress = memory.get_account_progress()

        logger.info("Retrieved account progress")

        # Return the progress data directly (not wrapped in ProgressResponse)
        # Frontend expects the raw data
        return progress

    except Exception as e:
        logger.error("Error getting account progress: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get account progress: {str(e)}"
        )


@router.get("/document/{document_id}")
async def get_document_progress(document_id: str):
    """
    Get progress for a specific document.

    Args:
        document_id: Document identifier

    Returns:
        Progress metrics for the document
    """
    try:
        memory = LearningMemory(user_id=DEFAULT_USER_ID)
        progress = memory.get_document_progress(document_id)

        logger.info("Retrieved progress for document: %s", document_id)

        return {
            "success": True,
            **progress
        }

    except Exception as e:
        logger.error("Error getting document progress: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document progress: {str(e)}"
        )


@router.get("/suggestions")
async def get_revision_suggestions(max_suggestions: int = 10):
    """
    Get evidence-based revision suggestions.

    Args:
        max_suggestions: Maximum number of suggestions to return

    Returns:
        List of pages needing revision
    """
    try:
        memory = LearningMemory(user_id=DEFAULT_USER_ID)
        suggestions = memory.get_revision_suggestions(max_suggestions=max_suggestions)

        logger.info("Retrieved %d revision suggestions", len(suggestions))

        return suggestions

    except Exception as e:
        logger.error("Error getting revision suggestions: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get revision suggestions: {str(e)}"
        )


# ── shortcut endpoints ────────────────────────────────────────────────────────

@router.post("/page-view")
async def track_page_view(
    document_id: str,
    page_number: int,
    time_spent: int = 0
):
    """
    Shortcut endpoint to track page views.
    Alternative to using /update with interaction_type="view"
    """
    try:
        memory = LearningMemory(user_id=DEFAULT_USER_ID)
        memory.update_page_view(document_id, page_number, time_spent)

        logger.info(
            "Tracked page view: doc=%s, page=%d, time=%ds",
            document_id, page_number, time_spent,
        )

        return {"success": True}
    except Exception as e:
        logger.error("Error tracking page view: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/question")
async def track_question(
    document_id: str,
    page_number: int
):
    """
    Shortcut endpoint to track questions asked.
    Call this when user sends a chat message.
    """
    try:
        memory = LearningMemory(user_id=DEFAULT_USER_ID)
        memory.update_explanation(document_id, page_number)

        logger.info("Tracked question: doc=%s, page=%d", document_id, page_number)

        return {"success": True}
    except Exception as e:
        logger.error("Error tracking question: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/quiz")
async def track_quiz(
    document_id: str,
    page_number: int,
    score: float
):
    """
    Shortcut endpoint to track quiz completion.
    Score should be 0.0 to 1.0 (e.g., 0.8 for 80%)
    """
    try:
        memory = LearningMemory(user_id=DEFAULT_USER_ID)
        memory.update_quiz(document_id, page_number, score)

        logger.info(
            "Tracked quiz: doc=%s, page=%d, score=%.2f",
            document_id, page_number, score,
        )

        return {"success": True}
    except Exception as e:
        logger.error("Error tracking quiz: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ── debug endpoint — remove in production ────────────────────────────────────

@router.get("/debug/memory")
async def debug_memory():
    """Debug endpoint to view raw memory data."""
    try:
        memory = LearningMemory(user_id=DEFAULT_USER_ID)

        memory_data = {}
        for doc_id, pages in memory.memory.items():
            memory_data[doc_id] = {}
            for page_num, interaction in pages.items():
                memory_data[doc_id][str(page_num)] = interaction.to_dict()

        return {
            "success": True,
            "user_id": DEFAULT_USER_ID,
            "memory_file": str(memory.memory_file),
            "file_exists": memory.memory_file.exists(),
            "memory": memory_data,
            "progress": memory.get_account_progress()
        }
    except Exception as e:
        logger.error("Error getting debug info: %s", e)
        return {"success": False, "error": str(e)}


# ── revision endpoints ────────────────────────────────────────────────────────

@router.get("/document/{document_id}/revisions")
async def get_document_revisions(document_id: str):
    """
    Get revision statistics and suggestions for a specific document.

    Args:
        document_id: Document identifier

    Returns:
        Revision statistics including streak, mastery level, and pages needing revision
    """
    try:
        memory = LearningMemory(user_id=DEFAULT_USER_ID)

        if document_id not in memory.memory:
            return {
                "success": True,
                "total_revisions": 0,
                "last_revision_date": None,
                "next_suggested_revision": None,
                "revision_streak": 0,
                "total_time_spent_seconds": 0,
                "mastery_level": 0,
                "pages_needing_revision": []
            }

        pages = memory.memory[document_id]

        total_revisions = 0
        last_revision_date = None
        total_time = 0
        revision_dates = []
        pages_needing_revision = []

        for page_num, interaction in pages.items():
            if interaction.view_count > 1:
                total_revisions += interaction.view_count - 1

            if hasattr(interaction, 'time_spent_seconds'):
                total_time += interaction.time_spent_seconds

            if interaction.last_interaction_timestamp:
                if last_revision_date is None or interaction.last_interaction_timestamp > last_revision_date:
                    last_revision_date = interaction.last_interaction_timestamp

                try:
                    revision_dates.append(
                        datetime.fromisoformat(
                            interaction.last_interaction_timestamp.replace('Z', '+00:00')
                        )
                    )
                except (ValueError, AttributeError):
                    pass

            days_since_last_view = None
            if interaction.last_interaction_timestamp:
                try:
                    last_view = datetime.fromisoformat(
                        interaction.last_interaction_timestamp.replace('Z', '+00:00')
                    )
                    days_since_last_view = (datetime.now().astimezone() - last_view).days
                except (ValueError, AttributeError):
                    pass

            needs_revision = False
            priority = "low"

            if days_since_last_view and days_since_last_view >= 3:
                needs_revision = True
                priority = "high" if days_since_last_view >= 7 else "medium"
            elif interaction.quiz_attempted and interaction.quiz_score and interaction.quiz_score < 0.7:
                needs_revision = True
                priority = "medium"

            if needs_revision:
                pages_needing_revision.append({
                    "page_number": page_num,
                    "days_since_last_view": days_since_last_view,
                    "quiz_score": round(interaction.quiz_score * 100, 1) if interaction.quiz_score else None,
                    "priority": priority
                })

        revision_streak = _calculate_streak(revision_dates) if revision_dates else 0
        mastery_level   = _calculate_mastery(pages)

        next_suggested_revision = None
        if last_revision_date:
            try:
                last_date = datetime.fromisoformat(last_revision_date.replace('Z', '+00:00'))
                next_suggested_revision = (last_date + timedelta(days=3)).isoformat()
            except (ValueError, AttributeError):
                pass

        logger.info(
            "Retrieved revision stats for %s: %d revisions, mastery %.1f%%",
            document_id, total_revisions, mastery_level,
        )

        return {
            "success": True,
            "total_revisions": total_revisions,
            "last_revision_date": last_revision_date,
            "next_suggested_revision": next_suggested_revision,
            "revision_streak": revision_streak,
            "total_time_spent_seconds": total_time,
            "mastery_level": round(mastery_level, 1),
            "pages_needing_revision": sorted(
                pages_needing_revision,
                key=lambda x: (x['priority'] == 'high', x.get('days_since_last_view', 0)),
                reverse=True
            )
        }

    except Exception as e:
        logger.error("Error getting revision stats for %s: %s", document_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get revision stats: {str(e)}"
        )


# ── private helpers ───────────────────────────────────────────────────────────

def _calculate_streak(revision_dates: List[datetime]) -> int:
    """Calculate consecutive days with revisions."""
    if not revision_dates:
        return 0

    sorted_dates = sorted(revision_dates, reverse=True)

    unique_days = []
    for dt in sorted_dates:
        day = dt.date()
        if not unique_days or day != unique_days[-1]:
            unique_days.append(day)

    streak = 0
    today  = datetime.now().date()

    for i, day in enumerate(unique_days):
        if day == today - timedelta(days=i):
            streak += 1
        else:
            break

    return streak


def _calculate_mastery(pages: dict) -> float:
    """Calculate overall mastery level (0-100) based on engagement and performance."""
    if not pages:
        return 0.0

    total_score = 0
    count       = 0

    for page_num, interaction in pages.items():
        page_score = 0

        # Quiz performance (50% weight)
        if interaction.quiz_attempted and interaction.quiz_score is not None:
            page_score += interaction.quiz_score * 50

        # View frequency (30% weight)
        if interaction.view_count >= 3:
            page_score += 30
        elif interaction.view_count >= 2:
            page_score += 20
        elif interaction.view_count >= 1:
            page_score += 10

        # Recency (20% weight)
        if interaction.last_interaction_timestamp:
            try:
                last_view = datetime.fromisoformat(
                    interaction.last_interaction_timestamp.replace('Z', '+00:00')
                )
                days_ago = (datetime.now().astimezone() - last_view).days
                if days_ago <= 1:
                    page_score += 20
                elif days_ago <= 3:
                    page_score += 15
                elif days_ago <= 7:
                    page_score += 10
            except (ValueError, AttributeError):
                pass

        total_score += page_score
        count       += 1

    return (total_score / count) if count > 0 else 0.0