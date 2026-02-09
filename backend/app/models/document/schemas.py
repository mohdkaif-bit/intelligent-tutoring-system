"""
Pydantic schemas for document operations.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime


class DocumentMetadata(BaseModel):
    """Document metadata schema."""
    document_id: str
    user_id: str
    original_filename: str
    stored_path: str
    page_count: int
    file_size_bytes: int
    upload_timestamp: str
    last_accessed: str
    embeddings_cached: bool = Field(
        default=False, 
        description="Whether embeddings are cached for instant querying"
    )
    
    model_config = {"validate_assignment": True}


class DocumentUploadResponse(BaseModel):
    """Response after document upload."""
    success: bool
    message: str
    document: Optional[DocumentMetadata] = None
    embeddings_cached: bool = Field(
        default=False,
        description="Whether embeddings were successfully generated and cached"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Document uploaded and indexed successfully",
                "document": {
                    "document_id": "sample_doc_abc123",
                    "original_filename": "course_notes.pdf",
                    "page_count": 50,
                    "embeddings_cached": True
                },
                "embeddings_cached": True
            }
        }


class DocumentListResponse(BaseModel):
    """Response for listing documents."""
    success: bool
    documents: list[DocumentMetadata]
    total_count: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "documents": [
                    {
                        "document_id": "doc_123",
                        "original_filename": "textbook.pdf",
                        "embeddings_cached": True
                    }
                ],
                "total_count": 1
            }
        }


class DocumentStats(BaseModel):
    """Storage statistics for user documents."""
    total_documents: int
    total_pages: int
    total_size_bytes: int
    total_size_mb: float
    storage_path: str
    embeddings_storage: Optional[Dict] = Field(
        default=None,
        description="Statistics about cached embeddings"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_documents": 5,
                "total_pages": 250,
                "total_size_bytes": 5242880,
                "total_size_mb": 5.0,
                "storage_path": ".storage/documents/user_001",
                "embeddings_storage": {
                    "total_documents": 5,
                    "total_chunks": 1250,
                    "total_size_mb": 3.2
                }
            }
        }