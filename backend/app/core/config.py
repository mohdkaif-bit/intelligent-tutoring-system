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

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "Intelligent Tutoring System"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ── API ───────────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"

    # ── Security (legacy — kept for any existing JWT usage) ───────────────────
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── Supabase Auth ─────────────────────────────────────────────────────────
    # All four values live in your Supabase dashboard → Settings → API
    #
    # SUPABASE_URL             — Project URL
    # SUPABASE_ANON_KEY        — Public anon key (used for signUp / signIn)
    # SUPABASE_SERVICE_ROLE_KEY— Service role key (bypasses RLS; server-only)
    # SUPABASE_JWT_SECRET      — Legacy HS256 secret (not needed for ES256; kept for compatibility)
    SUPABASE_URL: str = Field(default="")
    SUPABASE_ANON_KEY: str = Field(default="")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="")
    SUPABASE_JWT_SECRET: str = Field(default="")  # optional for ES256 projects

    # ── CORS ──────────────────────────────────────────────────────────────────
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """
        CORS origins — allows all in development, specific origins in production.
        """
        if self.DEBUG:
            return ["*"]
        else:
            return [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:4173",
                "http://127.0.0.1:4173",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]

    # ── Storage Paths ─────────────────────────────────────────────────────────
    STORAGE_BASE_DIR: Path = Field(default=Path(".storage"))
    DOCUMENT_STORAGE_DIR: Path = Field(default=Path(".storage/documents"))
    VECTOR_STORAGE_DIR: Path = Field(default=Path(".storage/vectorstores"))
    VECTORSTORE_DIR: Path = Field(default=Path(".storage/vectorstores"))  # alias
    MEMORY_STORAGE_DIR: Path = Field(default=Path(".storage/user_memory"))

    # ── LLM Configuration ─────────────────────────────────────────────────────
    GROQ_API_KEY: str = Field(default="")
    DEFAULT_MODEL: str = "llama-3.1-8b-instant"
    DEFAULT_TEMPERATURE: float = 0.6
    DEFAULT_MAX_TOKENS: int = 2500

    # ── Embeddings ────────────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "sentence-transformers/all-mpnet-base-v2"
    EMBEDDING_DEVICE: str = "cpu"

    # ── PDF Processing ────────────────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES: List[str] = ["application/pdf"]

    # ── Vector Store ──────────────────────────────────────────────────────────
    VECTOR_SEARCH_K: int = 6
    CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 150

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }

    def model_post_init(self, __context) -> None:
        """Create storage directories after model initialization."""
        self.STORAGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
        self.DOCUMENT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTOR_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
        self.MEMORY_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    # ── Validation helpers ────────────────────────────────────────────────────
    @property
    def supabase_configured(self) -> bool:
        """True when all four Supabase vars are set — useful for startup checks."""
        return all([
            self.SUPABASE_URL,
            self.SUPABASE_ANON_KEY,
            self.SUPABASE_SERVICE_ROLE_KEY,
            # SUPABASE_JWT_SECRET not required for ES256 JWKS verification
        ])


# Global settings instance
settings = Settings()