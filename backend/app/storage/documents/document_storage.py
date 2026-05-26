"""
Document Storage Manager - Persistent PDF storage with metadata.
Refactored from original document_storage.py with improvements.
"""
import os
import shutil
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import hashlib

from app.core.logging import get_logger
from app.core.config import settings
from app.models.document.schemas import DocumentMetadata

logger = get_logger(__name__)


class DocumentStorage:
    """
    Manages persistent storage of PDF documents.
    
    Features:
    - Stores PDFs permanently on disk
    - Tracks document metadata per user
    - Supports multi-document management
    - Auto-cleanup of orphaned files
    """
    
    def __init__(self, user_id: str, storage_base_dir: Optional[Path] = None):
        """
        Initialize document storage for a user.
        
        Args:
            user_id: Unique identifier for the user
            storage_base_dir: Base directory for all document storage
        """
        self.user_id = user_id
        self.storage_base_dir = storage_base_dir or settings.DOCUMENT_STORAGE_DIR
        self.user_storage_dir = self.storage_base_dir / user_id
        self.metadata_file = self.user_storage_dir / "documents_metadata.json"
        
        # Create directories if they don't exist
        self.user_storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing metadata
        self.documents: Dict[str, DocumentMetadata] = {}
        self._load_metadata()
        
        logger.info(f"Initialized DocumentStorage for user: {user_id}")
    
    def _generate_document_id(self, file_content: bytes, filename: str) -> str:
        """
        Generate unique document ID from file content.
        Uses MD5 hash of content for consistency.
        """
        content_hash = hashlib.md5(file_content).hexdigest()[:12]
        # Add filename for human readability
        clean_name = "".join(c for c in filename if c.isalnum() or c in "._-")[:30]
        return f"{clean_name}_{content_hash}"
    
    def _load_metadata(self):
        """Load document metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                
                for doc_id, doc_data in data.items():
                    self.documents[doc_id] = DocumentMetadata.model_validate(doc_data)
                
                logger.info(f"Loaded {len(self.documents)} documents for user {self.user_id}")
            except Exception as e:
                logger.error(f"Could not load document metadata: {e}")
                self.documents = {}
    
    def _save_metadata(self):
        """Persist document metadata to disk."""
        data = {doc_id: doc.model_dump() for doc_id, doc in self.documents.items()}
        
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved metadata for {len(self.documents)} documents")
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
            raise
    
    def store_document(self, file_bytes: bytes, filename: str, page_count: int) -> DocumentMetadata:
        """
        Store a PDF document permanently.
        
        Args:
            file_bytes: Raw PDF file bytes
            filename: Original filename
            page_count: Number of pages in the PDF
        
        Returns:
            DocumentMetadata object with storage information
        """
        # Generate unique document ID
        doc_id = self._generate_document_id(file_bytes, filename)
        
        # Check if document already exists
        if doc_id in self.documents:
            logger.info(f"Document {doc_id} already exists, updating access time")
            # Update last accessed time
            self.documents[doc_id].last_accessed = datetime.now().isoformat()
            self._save_metadata()
            return self.documents[doc_id]
        
        # Store PDF to disk
        stored_path = self.user_storage_dir / f"{doc_id}.pdf"
        try:
            with open(stored_path, 'wb') as f:
                f.write(file_bytes)
            logger.info(f"Stored document {doc_id} at {stored_path}")
        except Exception as e:
            logger.error(f"Failed to store document: {e}")
            raise
        
        # Create metadata with POSIX-style paths (works on both Windows and Linux)
        metadata = DocumentMetadata(
            document_id=doc_id,
            user_id=self.user_id,
            original_filename=filename,
            stored_path=str(stored_path).replace('\\', '/'),  # FIXED: Use forward slashes
            page_count=page_count,
            file_size_bytes=len(file_bytes),
            upload_timestamp=datetime.now().isoformat(),
            last_accessed=datetime.now().isoformat()
        )
        
        # Save metadata
        self.documents[doc_id] = metadata
        self._save_metadata()
        
        return metadata
    
    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        """
        Get metadata for a specific document.
        
        Args:
            document_id: Document identifier
        
        Returns:
            DocumentMetadata if found, None otherwise
        """
        if document_id in self.documents:
            # Update last accessed time
            self.documents[document_id].last_accessed = datetime.now().isoformat()
            self._save_metadata()
            return self.documents[document_id]
        return None
    
    def get_document_path(self, document_id: str) -> Optional[str]:
        """
        Get file system path for a document.
        Works on both Windows and Linux.
        
        Args:
            document_id: Document identifier
        
        Returns:
            File path if document exists, None otherwise
        """
        metadata = self.get_document(document_id)
        if not metadata:
            return None
        
        # Try the stored path first (handles both / and \ automatically via Path)
        stored_path = Path(metadata.stored_path)
        if stored_path.exists():
            return str(stored_path)
        
        # Fallback: construct path from document ID
        fallback_path = self.user_storage_dir / f"{document_id}.pdf"
        if fallback_path.exists():
            return str(fallback_path)
        
        logger.warning(f"Document file not found for {document_id}")
        return None
    
    def list_documents(self) -> List[DocumentMetadata]:
        """
        List all documents for the user.
        
        Returns:
            List of DocumentMetadata objects, sorted by last accessed (newest first)
        """
        docs = list(self.documents.values())
        # Sort by last accessed, most recent first
        docs.sort(key=lambda d: d.last_accessed, reverse=True)
        return docs
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document permanently.
        
        Args:
            document_id: Document identifier
        
        Returns:
            True if deleted successfully, False otherwise
        """
        if document_id not in self.documents:
            logger.warning(f"Document {document_id} not found for deletion")
            return False
        
        metadata = self.documents[document_id]
        
        # Delete file from disk
        try:
            stored_path = Path(metadata.stored_path)
            if stored_path.exists():
                stored_path.unlink()
                logger.info(f"Deleted document file: {stored_path}")
        except Exception as e:
            logger.error(f"Could not delete file {metadata.stored_path}: {e}")
        
        # Remove from metadata
        del self.documents[document_id]
        self._save_metadata()
        
        logger.info(f"Deleted document {document_id}")
        return True
    
    def get_storage_stats(self) -> Dict:
        """
        Get storage statistics for the user.
        
        Returns:
            Dictionary with storage statistics
        """
        total_size = sum(doc.file_size_bytes for doc in self.documents.values())
        total_documents = len(self.documents)
        total_pages = sum(doc.page_count for doc in self.documents.values())
        
        return {
            "total_documents": total_documents,
            "total_pages": total_pages,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "storage_path": str(self.user_storage_dir)
        }
    
    def cleanup_orphaned_files(self):
        """
        Remove PDF files that exist on disk but not in metadata.
        Useful for recovering from crashes or manual file operations.
        """
        # Get all PDF files in user directory
        pdf_files = set(self.user_storage_dir.glob("*.pdf"))
        
        # Get tracked files
        tracked_files = {Path(doc.stored_path) for doc in self.documents.values()}
        
        # Find orphaned files
        orphaned = pdf_files - tracked_files
        
        # Remove orphaned files
        for orphan in orphaned:
            try:
                orphan.unlink()
                logger.info(f"Removed orphaned file: {orphan}")
            except Exception as e:
                logger.error(f"Could not remove orphaned file {orphan}: {e}")
    
    def document_exists(self, document_id: str) -> bool:
        """Check if a document exists in storage."""
        return document_id in self.documents
    
    def rename_document(self, document_id: str, new_filename: str) -> bool:
        """
        Rename a document (updates metadata only, not file on disk).
        
        Args:
            document_id: Document identifier
            new_filename: New filename to display
        
        Returns:
            True if renamed successfully, False otherwise
        """
        if document_id not in self.documents:
            return False
        
        self.documents[document_id].original_filename = new_filename
        self._save_metadata()
        logger.info(f"Renamed document {document_id} to {new_filename}")
        return True

    def get_document_ids(self) -> set[str]:
        """Return the set of all document IDs currently tracked in storage."""
        return set(self.documents.keys())