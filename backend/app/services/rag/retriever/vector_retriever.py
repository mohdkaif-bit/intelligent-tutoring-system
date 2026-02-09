"""
Vector Retriever - FAISS-based document retrieval with caching.
Handles embedding generation and vector store management.
"""
import os
import numpy as np
from pathlib import Path
from typing import Tuple
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class VectorRetriever:
    """
    Manages FAISS vector store creation and document retrieval.
    Embeddings are cached in FAISS index for fast loading.
    """
    
    def __init__(self, user_id: str = "default_user"):
        """Initialize vector retriever with embeddings model."""
        # Disable TensorFlow warnings
        os.environ["TRANSFORMERS_NO_TF"] = "1"
        
        self.user_id = user_id
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": settings.EMBEDDING_DEVICE}
        )
        
        logger.info(f"Initialized VectorRetriever with model: {settings.EMBEDDING_MODEL}")
    
    def has_faiss_cache(self, document_id: str) -> bool:
        """Check if FAISS cache exists for a document."""
        faiss_path = settings.VECTOR_STORAGE_DIR / self.user_id / document_id
        return faiss_path.exists()
    
    def load_or_create_vectorstore(
        self, 
        document_id: str,
        pdf_path: str,
        force_recreate: bool = False
    ) -> Tuple[FAISS, any]:
        """
        Load existing FAISS vector store from cache or create new one.
        
        Args:
            document_id: Unique document identifier
            pdf_path: Path to PDF file
            force_recreate: Force recreation even if cache exists
        
        Returns:
            Tuple of (vectorstore, retriever)
        """
        faiss_path = settings.VECTOR_STORAGE_DIR / self.user_id / document_id
        
        # Try loading FAISS cache
        if faiss_path.exists() and not force_recreate:
            logger.info(f"✅ Loading FAISS cache for {document_id}")
            try:
                vectorstore = FAISS.load_local(
                    str(faiss_path),
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                retriever = vectorstore.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": settings.VECTOR_SEARCH_K}
                )
                logger.info(f"Successfully loaded FAISS cache")
                return vectorstore, retriever
            except Exception as e:
                logger.warning(f"FAISS cache failed: {e}, creating fresh...")
        
        # Create from scratch
        logger.info(f"⏳ Creating new embeddings for {document_id}")
        vectorstore, retriever = self._create_vectorstore(
            document_id,
            pdf_path, 
            faiss_path
        )
        
        return vectorstore, retriever
    
    def _create_vectorstore(
        self,
        document_id: str,
        pdf_path: str, 
        faiss_path: Path
    ) -> Tuple[FAISS, any]:
        """
        Create FAISS vector store from PDF document and cache it.
        
        Args:
            document_id: Document identifier
            pdf_path: Path to PDF file
            faiss_path: Path to save FAISS index
        
        Returns:
            Tuple of (vectorstore, retriever)
        """
        try:
            # Load PDF pages
            logger.info(f"Loading PDF: {pdf_path}")
            loader = PyMuPDFLoader(pdf_path)
            pages = loader.load()
            
            if not pages:
                raise ValueError("No pages loaded from PDF")
            
            logger.info(f"Loaded {len(pages)} pages")
            
            # Split into chunks
            logger.info("Splitting documents into chunks")
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP
            )
            chunks_docs = splitter.split_documents(pages)
            logger.info(f"Created {len(chunks_docs)} chunks")
            
            # Generate embeddings and create FAISS index
            logger.info("Generating embeddings and creating FAISS index...")
            vectorstore = FAISS.from_documents(chunks_docs, self.embeddings)
            
            # Save FAISS cache
            faiss_path.parent.mkdir(parents=True, exist_ok=True)
            vectorstore.save_local(str(faiss_path))
            logger.info(f"✅ Saved FAISS index to {faiss_path}")
            
            # Create retriever
            retriever = vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": settings.VECTOR_SEARCH_K}
            )
            
            return vectorstore, retriever
            
        except Exception as e:
            logger.error(f"Error creating vector store: {e}")
            raise
    
    def delete_vectorstore(self, document_id: str) -> bool:
        """
        Delete FAISS cache for a document.
        
        Args:
            document_id: Document identifier
        
        Returns:
            True if deleted, False if not found
        """
        faiss_path = settings.VECTOR_STORAGE_DIR / self.user_id / document_id
        
        if faiss_path.exists():
            try:
                import shutil
                shutil.rmtree(faiss_path)
                logger.info(f"Deleted FAISS cache for {document_id}")
                return True
            except Exception as e:
                logger.error(f"Error deleting FAISS cache: {e}")
                return False
        
        logger.warning(f"No FAISS cache found for {document_id}")
        return False
    
    def get_embeddings_model(self):
        """Get the embeddings model instance."""
        return self.embeddings