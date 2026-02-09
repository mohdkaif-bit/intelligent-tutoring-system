"""
Groq LLM Client - Refactored from groq_client_tutoring.py
Provides multiple configurations for different tutoring modes.
"""
import os
from typing import Optional, Dict, Any
from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# Configuration for different tutoring modes
TUTORING_CONFIGS = {
    "quick_answer": {
        "temperature": 0.0, # More focused for quick facts
        "max_tokens": 1000,
    },
    "explain_concept": {
        "temperature": 0.6,  # Balanced for clear explanations
        "max_tokens": 2500,
    },
    "generate_practice": {
        "temperature": 0.7,  # More creative for varied problems
        "max_tokens": 3000,
    },
    "step_by_step": {
        "temperature": 0.2,  # More structured for procedures
        "max_tokens": 2000,
    },
    "socratic": {
        "temperature": 0.7,  # Creative for generating questions
        "max_tokens": 1500,
    },
    "deep_analysis": {
        "temperature": 0.5,  # Balanced for comprehensive analysis
        "max_tokens": 3500,
    }
}


class GroqClient:
    """
    Groq LLM client with mode-specific configurations.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Groq client.
        
        Args:
            api_key: Optional Groq API key (uses settings if not provided)
        """
        self.api_key = api_key or settings.GROQ_API_KEY
        
        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY not found. Please set it in environment variables."
            )
        
        # Default LLM instance
        self._default_llm = self._create_llm()
        
        logger.info("Initialized GroqClient")
    
    def _create_llm(
        self, 
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> ChatGroq:
        """
        Create a ChatGroq instance with given parameters.
        
        Args:
            model: Model name (uses default if not provided)
            temperature: Temperature setting
            max_tokens: Max tokens setting
        
        Returns:
            Configured ChatGroq instance
        """
        return ChatGroq(
            api_key=self.api_key,
            model=model or settings.DEFAULT_MODEL,
            temperature=temperature if temperature is not None else settings.DEFAULT_TEMPERATURE,
            max_tokens=max_tokens if max_tokens is not None else settings.DEFAULT_MAX_TOKENS
        )
    
    def get_llm(self, mode: Optional[str] = None) -> ChatGroq:
        """
        Get LLM instance configured for specific tutoring mode.
        
        Args:
            mode: Tutoring mode ('quick_answer', 'explain_concept', etc.)
        
        Returns:
            Configured ChatGroq instance
        """
        if mode and mode in TUTORING_CONFIGS:
            config = TUTORING_CONFIGS[mode]
            logger.debug(f"Creating LLM for mode: {mode}")
            return self._create_llm(**config)
        
        return self._default_llm
    
    def invoke(self, prompt: str, mode: Optional[str] = None) -> str:
        """
        Invoke LLM with a prompt.
        
        Args:
            prompt: Input prompt
            mode: Optional tutoring mode
        
        Returns:
            LLM response text
        """
        llm = self.get_llm(mode)
        
        try:
            response = llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            logger.error(f"LLM invocation error: {e}")
            raise
    
    def get_available_modes(self) -> list[str]:
        """Get list of available tutoring modes."""
        return list(TUTORING_CONFIGS.keys())


# Global client instance
_client: Optional[GroqClient] = None


def get_llm_client() -> GroqClient:
    """
    Get or create global GroqClient instance.
    
    Returns:
        GroqClient instance
    """
    global _client
    
    if _client is None:
        _client = GroqClient()
    
    return _client