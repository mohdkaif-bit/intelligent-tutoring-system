"""
Reframe Engine - Text simplification with semantic alignment scoring.
Refactored from reframe_engine.py with improved structure.
"""
import numpy as np
from typing import Optional, Dict

from app.services.llm.groq_client import get_llm_client
from app.services.llm.prompt_manager.prompts import PromptManager
from app.core.logging import get_logger

logger = get_logger(__name__)


class ReframeEngine:
    """
    Service for reframing text with semantic alignment validation.
    
    Features:
    - Text simplification while preserving meaning
    - Semantic alignment scoring using embeddings
    - Transparent alignment metrics
    """
    
    def __init__(self, embeddings_model):
        """
        Initialize reframe engine.
        
        Args:
            embeddings_model: HuggingFace embeddings model instance
        """
        self.llm_client = get_llm_client()
        self.prompts = PromptManager()
        self.embeddings_model = embeddings_model
        logger.info("Initialized ReframeEngine")
    
    def reframe_text(
        self, 
        selected_text: str,
        optional_heading: Optional[str] = None
    ) -> Dict:
        """
        Reframe selected text for clarity with alignment scoring.
        
        Args:
            selected_text: Original text to reframe
            optional_heading: Optional heading for context (not used currently)
        
        Returns:
            Dictionary with reframed text and alignment metrics
        """
        if not selected_text or len(selected_text.strip()) < 10:
            raise ValueError("Selected text must be at least 10 characters")
        
        # Generate reframed text
        logger.info("Generating reframed text")
        prompt = self.prompts.get_prompt(
            "reframe_prompt",
            selected_text=selected_text.strip()
        )
        
        try:
            reframed_text = self.llm_client.invoke(prompt, mode="quick_answer")
        except Exception as e:
            logger.error(f"Error reframing text: {e}")
            raise
        
        # Compute semantic alignment
        alignment = self._compute_semantic_alignment(
            selected_text.strip(),
            reframed_text
        )
        
        # Build detailed alignment info
        alignment_details = self._build_alignment_details(alignment)
        
        logger.info(f"Reframed text with alignment score: {alignment['score']}")
        
        return {
            "reframed_text": reframed_text,
            "semantic_alignment": alignment,
            "alignment_details_payload": alignment_details
        }
    
    def _cosine_similarity(self, vec_a: list, vec_b: list) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec_a: First embedding vector
            vec_b: Second embedding vector
        
        Returns:
            Cosine similarity score (0-1)
        """
        a = np.array(vec_a, dtype=np.float64)
        b = np.array(vec_b, dtype=np.float64)
        
        dot = np.dot(a, b)
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        
        if norm == 0.0:
            return 0.0
        
        return float(dot / norm)
    
    def _score_to_label(self, score: float) -> str:
        """
        Convert alignment score to human-readable label.
        
        Args:
            score: Alignment score
        
        Returns:
            Label describing alignment quality
        """
        if score >= 0.90:
            return "Very closely aligned"
        elif score >= 0.80:
            return "Closely aligned"
        elif score >= 0.65:
            return "Mostly aligned"
        else:
            return "Low alignment"
    
    def _compute_semantic_alignment(
        self, 
        original_text: str,
        reframed_text: str
    ) -> Dict:
        """
        Compute semantic alignment between original and reframed text.
        
        Args:
            original_text: Original text
            reframed_text: Reframed text
        
        Returns:
            Dictionary with alignment metrics
        """
        # Embed both texts
        vec_original = self.embeddings_model.embed_query(original_text)
        vec_reframed = self.embeddings_model.embed_query(reframed_text)
        
        # Compute cosine similarity
        raw_score = self._cosine_similarity(vec_original, vec_reframed)
        score = round(raw_score, 2)
        
        # Generate label
        label = self._score_to_label(score)
        
        # Check for warning
        warning = score < 0.65
        warning_message = (
            "This rewrite may deviate from the original meaning. "
            "Try reframing again with stricter phrasing if needed."
            if warning else None
        )
        
        logger.debug(f"Computed alignment: score={score}, label={label}")
        
        return {
            "score": score,
            "label": label,
            "warning": warning,
            "warning_message": warning_message
        }
    
    def _build_alignment_details(self, alignment: Dict) -> Dict:
        """
        Build detailed alignment explanation for UI.
        
        Args:
            alignment: Alignment metrics
        
        Returns:
            Dictionary with detailed alignment information
        """
        score = alignment["score"]
        label = alignment["label"]
        
        # Dynamic explanation based on score
        if score >= 0.90:
            what_it_means = [
                "The rewritten text very closely matches the meaning of your original selection.",
                "No significant new ideas or shifts in meaning were introduced.",
                "Wording may have been adjusted for clarity while keeping the core meaning intact."
            ]
        elif score >= 0.80:
            what_it_means = [
                "The rewritten text closely matches the meaning of your original selection.",
                "Minor rephrasing or simplification was applied.",
                "The core ideas remain well-preserved."
            ]
        elif score >= 0.65:
            what_it_means = [
                "The rewritten text mostly preserves the meaning of your original selection.",
                "Some rephrasing shifted the emphasis slightly.",
                "The overall topic and direction remain aligned, but wording diverged more than usual."
            ]
        else:
            what_it_means = [
                "The rewritten text may have drifted from the meaning of your original selection.",
                "Significant rephrasing or restructuring may have changed the intended meaning.",
                "Consider reframing again with stricter or more specific phrasing."
            ]
        
        return {
            "alignment_details": {
                "numeric_score": score,
                "label": label,
                "what_it_means": what_it_means,
                "how_calculated": [
                    "The system compares the meaning of the original and rewritten text",
                    "using a mathematical similarity model (embeddings).",
                    "This score does not measure correctness or factual accuracy."
                ]
            }
        }