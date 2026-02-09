"""
Reframe API Routes
Handles text reframing with semantic alignment.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional  # ← ADD THIS IMPORT

from app.services.reframe.reframe_engine import ReframeEngine
from app.services.rag.retriever.vector_retriever import VectorRetriever
from app.storage.user_memory import LearningMemory
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

DEFAULT_USER_ID = "default_user"


class ReframeRequest(BaseModel):
    """Request to reframe text."""
    document_id: str
    page_number: int
    selected_text: str
    optional_heading: Optional[str] = None  # ← CHANGED FROM: str = None


class ReframeResponse(BaseModel):
    """Response with reframed text and alignment."""
    success: bool
    reframed_text: str
    semantic_alignment: dict
    alignment_details_payload: dict
    error: Optional[str] = None  # ← CHANGED FROM: str = None


@router.post("/reframe", response_model=ReframeResponse)
async def reframe_text(request: ReframeRequest):
    """
    Reframe selected text for clarity.
    
    Args:
        request: Reframe request with text and context
    
    Returns:
        Reframed text with semantic alignment metrics
    """
    try:
        # Validate input
        if not request.selected_text or len(request.selected_text.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected text must be at least 10 characters"
            )
        
        # Get embeddings model
        vector_retriever = VectorRetriever()
        embeddings_model = vector_retriever.get_embeddings_model()
        
        # Initialize reframe engine
        reframe_engine = ReframeEngine(embeddings_model)
        
        # Reframe text
        result = reframe_engine.reframe_text(
            selected_text=request.selected_text,
            optional_heading=request.optional_heading
        )
        
        # Update learning memory - reframe requested
        memory = LearningMemory(user_id=DEFAULT_USER_ID)
        memory.update_reframe(
            document_id=request.document_id,
            page_number=request.page_number
        )
        
        logger.info(f"Reframed text with alignment score: {result['semantic_alignment']['score']}")
        
        return ReframeResponse(
            success=True,
            reframed_text=result["reframed_text"],
            semantic_alignment=result["semantic_alignment"],
            alignment_details_payload=result["alignment_details_payload"]
            # error defaults to None automatically now
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reframing text: {e}")
        return ReframeResponse(
            success=False,
            reframed_text="",
            semantic_alignment={},
            alignment_details_payload={},
            error=f"Failed to reframe text: {str(e)}"
        )