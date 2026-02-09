"""
PDF API Routes
Handles PDF page extraction, text extraction, and rendering.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.storage.documents import DocumentStorage
from app.services.pdf.pdf_processor import PDFProcessor
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

DEFAULT_USER_ID = "default_user"


class PageTextResponse(BaseModel):
    """Response with extracted page text."""
    success: bool
    page_number: int
    text: str
    word_count: int


class PageBase64Response(BaseModel):
    """Response with base64-encoded PDF page."""
    success: bool
    page_number: int
    base64_pdf: str


@router.get("/{document_id}/page/{page_number}/text", response_model=PageTextResponse)
async def get_page_text(document_id: str, page_number: int):
    """
    Extract text from a specific page.
    
    Args:
        document_id: Document identifier
        page_number: Page number (1-indexed)
    
    Returns:
        Extracted text and metadata
    """
    try:
        # Get document path
        doc_storage = DocumentStorage(user_id=DEFAULT_USER_ID)
        doc_path = doc_storage.get_document_path(document_id)
        
        if not doc_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        # Extract text
        text = PDFProcessor.extract_page_text(doc_path, page_number)
        word_count = len(text.split())
        
        logger.info(f"Extracted text from page {page_number} of {document_id}")
        
        return PageTextResponse(
            success=True,
            page_number=page_number,
            text=text,
            word_count=word_count
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting page text: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract page text: {str(e)}"
        )


@router.get("/{document_id}/page/{page_number}/render", response_model=PageBase64Response)
async def get_page_render(document_id: str, page_number: int):
    """
    Get base64-encoded PDF page for rendering.
    
    Args:
        document_id: Document identifier
        page_number: Page number (1-indexed)
    
    Returns:
        Base64-encoded PDF page
    """
    try:
        # Get document path
        doc_storage = DocumentStorage(user_id=DEFAULT_USER_ID)
        doc_path = doc_storage.get_document_path(document_id)
        
        if not doc_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        # Get base64-encoded page
        base64_pdf = PDFProcessor.pdf_page_to_base64(doc_path, page_number)
        
        logger.info(f"Rendered page {page_number} of {document_id}")
        
        return PageBase64Response(
            success=True,
            page_number=page_number,
            base64_pdf=base64_pdf
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering page: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to render page: {str(e)}"
        )


@router.get("/{document_id}/metadata")
async def get_pdf_metadata(document_id: str):
    """
    Get PDF metadata.
    
    Args:
        document_id: Document identifier
    
    Returns:
        PDF metadata
    """
    try:
        # Get document path
        doc_storage = DocumentStorage(user_id=DEFAULT_USER_ID)
        doc_path = doc_storage.get_document_path(document_id)
        
        if not doc_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        # Get metadata
        metadata = PDFProcessor.get_pdf_metadata(doc_path)
        
        return {
            "success": True,
            "document_id": document_id,
            **metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting PDF metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get PDF metadata: {str(e)}"
        )