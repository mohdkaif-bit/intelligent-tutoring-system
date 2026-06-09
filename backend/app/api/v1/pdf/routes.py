"""
PDF API Routes
Handles PDF page extraction, text extraction, and rendering.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.v1.auth.dependencies import CurrentUser
from app.storage.documents import DocumentStorage
from app.services.pdf.pdf_processor import PDFProcessor
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class PageTextResponse(BaseModel):
    success: bool
    page_number: int
    text: str
    word_count: int


class PageBase64Response(BaseModel):
    success: bool
    page_number: int
    base64_pdf: str


@router.get("/{document_id}/page/{page_number}/text", response_model=PageTextResponse)
async def get_page_text(document_id: str, page_number: int, user: CurrentUser):
    """Extract text from a specific page of the authenticated user's document."""
    try:
        doc_storage = DocumentStorage(user_id=user.id)
        doc_path    = doc_storage.get_document_path(document_id)

        if not doc_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )

        text       = PDFProcessor.extract_page_text(doc_path, page_number)
        word_count = len(text.split())

        logger.info("Extracted text from page %d of %s (user=%s)", page_number, document_id, user.id)

        return PageTextResponse(
            success=True,
            page_number=page_number,
            text=text,
            word_count=word_count,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error extracting page text: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract page text: {str(e)}",
        )


@router.get("/{document_id}/page/{page_number}/render", response_model=PageBase64Response)
async def get_page_render(document_id: str, page_number: int, user: CurrentUser):
    """Get base64-encoded PDF page for the authenticated user's document."""
    try:
        doc_storage = DocumentStorage(user_id=user.id)
        doc_path    = doc_storage.get_document_path(document_id)

        if not doc_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )

        base64_pdf = PDFProcessor.pdf_page_to_base64(doc_path, page_number)

        logger.info("Rendered page %d of %s (user=%s)", page_number, document_id, user.id)

        return PageBase64Response(
            success=True,
            page_number=page_number,
            base64_pdf=base64_pdf,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error rendering page: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to render page: {str(e)}",
        )


@router.get("/{document_id}/metadata")
async def get_pdf_metadata(document_id: str, user: CurrentUser):
    """Get PDF metadata for the authenticated user's document."""
    try:
        doc_storage = DocumentStorage(user_id=user.id)
        doc_path    = doc_storage.get_document_path(document_id)

        if not doc_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )

        metadata = PDFProcessor.get_pdf_metadata(doc_path)

        return {"success": True, "document_id": document_id, **metadata}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting PDF metadata: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get PDF metadata: {str(e)}",
        )