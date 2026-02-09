"""
PDF Processing Service
Handles PDF text extraction, page rendering, and metadata extraction.
"""
import base64
from pathlib import Path
from typing import Optional, Tuple
import fitz  # PyMuPDF

from app.core.logging import get_logger

logger = get_logger(__name__)


class PDFProcessor:
    """Service for PDF processing operations."""
    
    @staticmethod
    def extract_page_text(pdf_path: str, page_number: int) -> str:
        """
        Extract text from a specific PDF page.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number (1-indexed)
        
        Returns:
            Extracted text from the page
        """
        try:
            doc = fitz.open(pdf_path)
            
            if page_number < 1 or page_number > doc.page_count:
                raise ValueError(f"Invalid page number: {page_number}")
            
            page = doc[page_number - 1]  # Convert to 0-indexed
            text = page.get_text()
            doc.close()
            
            logger.debug(f"Extracted text from page {page_number} of {pdf_path}")
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise
    
    @staticmethod
    def extract_all_text(pdf_path: str) -> str:
        """
        Extract all text from a PDF.
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            All text from the PDF
        """
        try:
            doc = fitz.open(pdf_path)
            all_text = ""
            
            for page in doc:
                all_text += page.get_text() + "\n\n"
            
            doc.close()
            logger.debug(f"Extracted all text from {pdf_path}")
            return all_text
        except Exception as e:
            logger.error(f"Error extracting all text from PDF: {e}")
            raise
    
    @staticmethod
    def get_page_count(pdf_path: str) -> int:
        """
        Get the number of pages in a PDF.
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Number of pages
        """
        try:
            doc = fitz.open(pdf_path)
            page_count = doc.page_count
            doc.close()
            return page_count
        except Exception as e:
            logger.error(f"Error getting page count: {e}")
            raise
    
    @staticmethod
    def get_pdf_metadata(pdf_path: str) -> dict:
        """
        Extract metadata from a PDF.
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Dictionary with metadata
        """
        try:
            doc = fitz.open(pdf_path)
            metadata = doc.metadata
            page_count = doc.page_count
            doc.close()
            
            return {
                "page_count": page_count,
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "keywords": metadata.get("keywords", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "creation_date": metadata.get("creationDate", ""),
                "modification_date": metadata.get("modDate", "")
            }
        except Exception as e:
            logger.error(f"Error extracting PDF metadata: {e}")
            raise
    
    @staticmethod
    def pdf_page_to_base64(pdf_path: str, page_number: int) -> str:
        """
        Extract a single page as base64 for rendering.
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number (1-indexed)
        
        Returns:
            Base64-encoded PDF page
        """
        try:
            doc = fitz.open(pdf_path)
            
            if page_number < 1 or page_number > doc.page_count:
                raise ValueError(f"Invalid page number: {page_number}")
            
            # Create new PDF with just this page
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=page_number-1, to_page=page_number-1)
            
            # Convert to bytes
            pdf_bytes = new_doc.tobytes()
            new_doc.close()
            doc.close()
            
            # Encode to base64
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            
            logger.debug(f"Converted page {page_number} to base64")
            return base64_pdf
        except Exception as e:
            logger.error(f"Error converting PDF page to base64: {e}")
            raise
    
    @staticmethod
    def validate_pdf(file_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        Validate if bytes represent a valid PDF.
        
        Args:
            file_bytes: PDF file bytes
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page_count = doc.page_count
            doc.close()
            
            if page_count == 0:
                return False, "PDF has no pages"
            
            return True, None
        except Exception as e:
            return False, f"Invalid PDF: {str(e)}"