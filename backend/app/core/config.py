"""
Application configuration using Pydantic Settings.
Loads from environment variables with validation.
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from pathlib import Path
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    APP_NAME: str = "Intelligent Tutoring System"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS - Simplified for development
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """
        CORS origins - allows all in development, specific origins in production.
        """
        if self.DEBUG:
            # Development: Allow all origins
            return ["*"]
        else:
            # Production: Specify allowed origins
            return [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:4173",
                "http://127.0.0.1:4173",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]
    
    # Storage Paths
    STORAGE_BASE_DIR: Path = Field(default=Path(".storage"))
    DOCUMENT_STORAGE_DIR: Path = Field(default=Path(".storage/documents"))
    VECTOR_STORAGE_DIR: Path = Field(default=Path(".storage/vectorstores"))
    VECTORSTORE_DIR: Path = Field(default=Path(".storage/vectorstores"))  # Alias for compatibility
    MEMORY_STORAGE_DIR: Path = Field(default=Path(".storage/user_memory"))
    
    # LLM Configuration
    GROQ_API_KEY: str = Field(default="")
    DEFAULT_MODEL: str = "llama-3.1-8b-instant"
    DEFAULT_TEMPERATURE: float = 0.6
    DEFAULT_MAX_TOKENS: int = 2500
    
    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-mpnet-base-v2"
    EMBEDDING_DEVICE: str = "cpu"
    
    # PDF Processing
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES: List[str] = ["application/pdf"]
    
    # Vector Store
    VECTOR_SEARCH_K: int = 6
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 150
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"  # Ignore extra fields from .env
    }
    
    def model_post_init(self, __context) -> None:
        """Create storage directories after model initialization."""
        self.STORAGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
        self.DOCUMENT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTOR_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
        self.MEMORY_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()