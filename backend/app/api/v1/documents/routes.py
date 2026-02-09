"""
Documents API Routes
Handles document upload, listing, deletion, and metadata.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from typing import List

from app.models.document.schemas import (
    DocumentMetadata,
    DocumentUploadResponse,
    DocumentListResponse,
    DocumentStats
)
from app.storage.documents import DocumentStorage
from app.services.pdf.pdf_processor import PDFProcessor
from app.services.rag.retriever.vector_retriever import VectorRetriever
from app.utils.validators.file_validators import FileValidator
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Constants
DEFAULT_USER_ID = "default_user"  # TODO: Replace with actual user authentication


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF document.
    
    - Validates PDF file
    - Stores document persistently
    - Embeddings generated on first use (lazy loading)
    - Returns document metadata
    """
    try:
        # Validate file type
        is_valid, error = FileValidator.validate_pdf_upload(file)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        # Read file bytes
        file_bytes = await file.read()
        
        # Validate file size
        is_valid, error = FileValidator.validate_file_size(file_bytes)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        # Validate PDF content
        is_valid, error = PDFProcessor.validate_pdf(file_bytes)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
        
        # Get page count
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(file_bytes)
            temp_path = tmp_file.name
        
        try:
            page_count = PDFProcessor.get_page_count(temp_path)
            
            # Store document
            doc_storage = DocumentStorage(user_id=DEFAULT_USER_ID)
            metadata = doc_storage.store_document(
                file_bytes=file_bytes,
                filename=file.filename,
                page_count=page_count
            )
            
            logger.info(f"✅ Document uploaded: {metadata.document_id}")
            
            return DocumentUploadResponse(
                success=True,
                message="Document uploaded successfully. Embeddings will be generated on first use.",
                document=metadata,
                embeddings_cached=False  # Will be cached on first access
            )
            
        finally:
            # Clean up temp file
            try:
                os.remove(temp_path)
            except:
                pass
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


@router.get("/list", response_model=DocumentListResponse)
async def list_documents():
    """
    List all documents for the user.
    
    Returns documents sorted by last accessed (newest first).
    Includes FAISS cache status.
    """
    try:
        doc_storage = DocumentStorage(user_id=DEFAULT_USER_ID)
        vector_retriever = VectorRetriever(user_id=DEFAULT_USER_ID)
        
        documents = doc_storage.list_documents()
        
        # Add FAISS cache status to each document
        enriched_documents = []
        for doc in documents:
            # Handle different document formats
            if isinstance(doc, dict):
                doc_dict = doc
            elif hasattr(doc, 'model_dump'):  # Pydantic v2
                doc_dict = doc.model_dump()
            elif hasattr(doc, 'dict'):  # Pydantic v1
                doc_dict = doc.dict()
            else:
                # If it's an object with attributes, convert to dict
                doc_dict = {
                    "document_id": getattr(doc, 'document_id', None),
                    "user_id": getattr(doc, 'user_id', DEFAULT_USER_ID),
                    "original_filename": getattr(doc, 'original_filename', 'Unknown'),
                    "stored_path": getattr(doc, 'stored_path', ''),
                    "page_count": getattr(doc, 'page_count', 0),
                    "file_size_bytes": getattr(doc, 'file_size_bytes', 0),
                    "upload_timestamp": getattr(doc, 'upload_timestamp', ''),
                    "last_accessed": getattr(doc, 'last_accessed', ''),
                }
            
            # Check if FAISS cache exists
            doc_dict["embeddings_cached"] = vector_retriever.has_faiss_cache(
                doc_dict["document_id"]
            )
            
            # Create DocumentMetadata object
            enriched_doc = DocumentMetadata(**doc_dict)
            enriched_documents.append(enriched_doc)
        
        logger.info(f"Retrieved {len(enriched_documents)} documents")
        
        return DocumentListResponse(
            success=True,
            documents=enriched_documents,
            total_count=len(enriched_documents)
        )
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}"
        )
    

@router.get("/{document_id}", response_model=DocumentMetadata)
async def get_document(document_id: str):
    """
    Get metadata for a specific document.
    """
    try:
        doc_storage = DocumentStorage(user_id=DEFAULT_USER_ID)
        metadata = doc_storage.get_document(document_id)
        
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and its FAISS cache.
    """
    try:
        doc_storage = DocumentStorage(user_id=DEFAULT_USER_ID)
        
        # Delete document
        success = doc_storage.delete_document(document_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        # Delete FAISS cache
        vector_retriever = VectorRetriever(user_id=DEFAULT_USER_ID)
        cache_deleted = vector_retriever.delete_vectorstore(document_id)
        
        logger.info(f"Deleted document and FAISS cache: {document_id}")
        
        return {
            "success": True,
            "message": f"Document {document_id} and FAISS cache deleted successfully",
            "caches_deleted": cache_deleted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


@router.get("/stats/storage", response_model=DocumentStats)
async def get_storage_stats():
    """
    Get storage statistics for the user.
    """
    try:
        doc_storage = DocumentStorage(user_id=DEFAULT_USER_ID)
        
        # Get document stats
        doc_stats = doc_storage.get_storage_stats()
        
        return DocumentStats(**doc_stats)
        
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get storage stats: {str(e)}"
        )