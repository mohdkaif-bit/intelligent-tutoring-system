"""
Documents API Routes
Handles document upload, listing, deletion, and metadata.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from typing import List

from app.api.v1.auth.dependencies import CurrentUser
from app.models.document.schemas import (
    DocumentMetadata,
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentStats,
)
from app.storage.documents import DocumentStorage
from app.services.pdf.pdf_processor import PDFProcessor
from app.services.rag.retriever.vector_retriever import VectorRetriever
from app.utils.validators.file_validators import FileValidator
from app.core.logging import get_logger
from app.storage.user_memory.learning_memory import LearningMemory

logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...), user: CurrentUser = ...):
    """
    Upload a PDF document.

    - Validates PDF file
    - Stores document in the authenticated user's private storage
    - Embeddings generated on first use (lazy loading)
    - Returns document metadata
    """
    try:
        is_valid, error = FileValidator.validate_pdf_upload(file)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

        file_bytes = await file.read()

        is_valid, error = FileValidator.validate_file_size(file_bytes)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

        is_valid, error = PDFProcessor.validate_pdf(file_bytes)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

        import tempfile, os

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_bytes)
            temp_path = tmp_file.name

        try:
            page_count  = PDFProcessor.get_page_count(temp_path)
            doc_storage = DocumentStorage(user_id=user.id)
            metadata    = doc_storage.store_document(
                file_bytes=file_bytes,
                filename=file.filename,
                page_count=page_count,
            )
            logger.info("Document uploaded: %s (user=%s)", metadata.document_id, user.id)

            return DocumentUploadResponse(
                success=True,
                message="Document uploaded successfully. Embeddings will be generated on first use.",
                document=metadata,
                embeddings_cached=False,
            )
        finally:
            try:
                os.remove(temp_path)
            except Exception:
                pass

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error uploading document: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}",
        )


@router.get("/list", response_model=DocumentListResponse)
async def list_documents(user: CurrentUser):
    """
    List all documents for the authenticated user.

    Returns documents sorted by last accessed (newest first).
    Includes FAISS cache status.
    """
    try:
        doc_storage      = DocumentStorage(user_id=user.id)
        vector_retriever = VectorRetriever(user_id=user.id)
        documents        = doc_storage.list_documents()

        enriched_documents = []
        for doc in documents:
            if isinstance(doc, dict):
                doc_dict = doc
            elif hasattr(doc, "model_dump"):
                doc_dict = doc.model_dump()
            elif hasattr(doc, "dict"):
                doc_dict = doc.dict()
            else:
                doc_dict = {
                    "document_id":       getattr(doc, "document_id", None),
                    "user_id":           getattr(doc, "user_id", user.id),
                    "original_filename": getattr(doc, "original_filename", "Unknown"),
                    "stored_path":       getattr(doc, "stored_path", ""),
                    "page_count":        getattr(doc, "page_count", 0),
                    "file_size_bytes":   getattr(doc, "file_size_bytes", 0),
                    "upload_timestamp":  getattr(doc, "upload_timestamp", ""),
                    "last_accessed":     getattr(doc, "last_accessed", ""),
                }

            doc_dict["embeddings_cached"] = vector_retriever.has_faiss_cache(
                doc_dict["document_id"]
            )
            enriched_documents.append(DocumentMetadata(**doc_dict))

        logger.info("Listed %d documents for user=%s", len(enriched_documents), user.id)

        return DocumentListResponse(
            success=True,
            documents=enriched_documents,
            total_count=len(enriched_documents),
        )

    except Exception as e:
        logger.error("Error listing documents: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}",
        )


@router.get("/{document_id}", response_model=DocumentMetadata)
async def get_document(document_id: str, user: CurrentUser):
    """Get metadata for a specific document owned by the authenticated user."""
    try:
        doc_storage = DocumentStorage(user_id=user.id)
        metadata    = doc_storage.get_document(document_id)

        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )
        return metadata

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting document: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document: {str(e)}",
        )


@router.delete("/{document_id}")
async def delete_document(document_id: str, user: CurrentUser):
    """
    Delete a document, its FAISS cache, and its learning progress.
    Only the owning user can delete their own documents.
    """
    try:
        doc_storage = DocumentStorage(user_id=user.id)
        success     = doc_storage.delete_document(document_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )

        vector_retriever = VectorRetriever(user_id=user.id)
        cache_deleted    = vector_retriever.delete_vectorstore(document_id)

        learning_memory  = LearningMemory(user_id=user.id)
        learning_memory.clear_document(document_id)

        logger.info("Deleted document %s for user=%s", document_id, user.id)

        return {
            "success":        True,
            "message":        f"Document {document_id}, FAISS cache, and learning progress deleted successfully",
            "caches_deleted": cache_deleted,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting document: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )


@router.get("/stats/storage", response_model=DocumentStats)
async def get_storage_stats(user: CurrentUser):
    """Get storage statistics for the authenticated user."""
    try:
        doc_storage = DocumentStorage(user_id=user.id)
        doc_stats   = doc_storage.get_storage_stats()
        return DocumentStats(**doc_stats)

    except Exception as e:
        logger.error("Error getting storage stats: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get storage stats: {str(e)}",
        )