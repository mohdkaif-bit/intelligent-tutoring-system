"""
File validation utilities.
"""
from typing import Tuple, Optional
from fastapi import UploadFile

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class FileValidator:
    """Validates uploaded files."""
    
    @staticmethod
    def validate_pdf_upload(file: UploadFile) -> Tuple[bool, Optional[str]]:
        """
        Validate PDF file upload.
        
        Args:
            file: Uploaded file
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file type
        if file.content_type not in settings.ALLOWED_FILE_TYPES:
            return False, f"Invalid file type. Only PDF files are allowed."
        
        # Check filename extension
        if not file.filename.lower().endswith('.pdf'):
            return False, "File must have .pdf extension"
        
        return True, None
    
    @staticmethod
    def validate_file_size(file_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        Validate file size.
        
        Args:
            file_bytes: File content as bytes
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        size_mb = len(file_bytes) / (1024 * 1024)
        
        if size_mb > settings.MAX_FILE_SIZE_MB:
            return False, f"File too large. Maximum size is {settings.MAX_FILE_SIZE_MB}MB"
        
        if size_mb == 0:
            return False, "File is empty"
        
        return True, None