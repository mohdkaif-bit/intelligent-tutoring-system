"""
Style Adapter & Mode Advisor
-----------------------------
Adaptation A: Response Style Adaptation
    Reads LearningMemory signals for the current page and injects
    a style instruction into the RAG state so the LLM adjusts
    how it explains things.

Adaptation B: Mode Suggestion (non-forced)
    Looks at page history and recommends the optimal tutoring mode.
    Returns the suggestion + a human-readable reason so the frontend
    can show a banner. The user's requested mode is ALWAYS used for
    the actual answer — the suggestion is advisory only.
"""

from __future__ import annotations

from typing import Literal, Optional

from app.storage.user_memory import LearningMemory, PageInteraction
from app.core.logging import get_logger

logger = get_logger(__name__)

TutoringMode = Literal[
    "quick_answer",
    "explain_concept",
    "step_by_step",
    "practice_problems",
    "deep_analysis",
]

MODE_LABELS = {
    "quick_answer": "Quick Answer",
    "explain_concept": "Explain Concept",
    "step_by_step": "Step by Step",
    "practice_problems": "Practice Problems",
    "deep_analysis": "Deep Analysis",
}


class StyleAdapter:
    """
    Reads LearningMemory signals and produces:
      - A style hint string to prepend to the LLM prompt (Adaptation A)
      - A mode suggestion + reason string (Adaptation B, non-forced)

    Parameters
    ----------
    user_id : str
    """

    def __init__(self, user_id: str = "default_user") -> None:
        self.user_id = user_id
        self.memory = LearningMemory(user_id=user_id)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                      #
    # ------------------------------------------------------------------ #

    def _get_page(
        self, document_id: str, page_number: Optional[int]
    ) -> Optional[PageInteraction]:
        if page_number is None:
            return None
        return self.memory.memory.get(document_id, {}).get(page_number)

    def _struggle_level(
        self, page: PageInteraction
    ) -> Literal["high", "medium", "low", "none"]:
        """Derive struggle level from observable signals."""
        score = 0

        if page.quiz_attempted and page.quiz_score is not None:
            if page.quiz_score < 0.5:
                score += 4
            elif page.quiz_score < 0.7:
                score += 2

        if page.self_assessment == "not_clear":
            score += 4
        elif page.self_assessment == "somewhat_clear":
            score += 2

        total_help = page.reframes_count + page.explanations_count
        if total_help > 5:
            score += 3
        elif total_help > 3:
            score += 2
        elif total_help > 1:
            score += 1

        if page.time_spent_seconds > 600:
            score += 1

        if score >= 6:
            return "high"
        elif score >= 3:
            return "medium"
        elif score >= 1:
            return "low"
        return "none"

    # ------------------------------------------------------------------ #
    # Adaptation A — Style Hint                                             #
    # ------------------------------------------------------------------ #

    def get_style_hint(
        self,
        document_id: str,
        page_number: Optional[int],
    ) -> str:
        """
        Return a style instruction string to prepend to the LLM prompt.
        Returns empty string if no adaptation needed.
        """
        page = self._get_page(document_id, page_number)
        if page is None:
            return ""

        struggle = self._struggle_level(page)

        if struggle == "high":
            return (
                "[TEACHING STYLE: This student has shown significant difficulty "
                "with this material — low quiz scores, repeated requests for help, "
                "or self-reported confusion. Use very simple language. Break every "
                "concept into small numbered steps. Use concrete real-world examples "
                "and analogies. Avoid jargon. Check understanding at the end by "
                "asking one simple question.]\n\n"
            )
        elif struggle == "medium":
            return (
                "[TEACHING STYLE: This student has shown some difficulty with this "
                "material. Explain clearly with examples. Define technical terms when "
                "you use them. Keep sentences short and direct.]\n\n"
            )
        elif struggle == "low":
            return (
                "[TEACHING STYLE: This student is generally following along but may "
                "benefit from a concrete example to solidify understanding.]\n\n"
            )

        if page.quiz_score is not None and page.quiz_score >= 0.9:
            return (
                "[TEACHING STYLE: This student has demonstrated strong understanding. "
                "You can use precise technical language and go deeper into nuance "
                "without over-explaining basics.]\n\n"
            )

        return ""

    # ------------------------------------------------------------------ #
    # Adaptation B — Mode Suggestion (non-forced)                          #
    # ------------------------------------------------------------------ #

    def suggest_mode_with_reason(
        self,
        document_id: str,
        page_number: Optional[int],
        requested_mode: TutoringMode,
    ) -> tuple[Optional[TutoringMode], Optional[str]]:
        """
        Suggest a better tutoring mode based on memory signals.

        This is ADVISORY only — the caller always uses the user's
        requested_mode for the actual answer. The suggestion is returned
        so the frontend can show a banner like:
          "Based on your history, we recommend Step by Step mode. Switch?"

        Returns
        -------
        (suggested_mode, reason) where both are None if no suggestion needed,
        or if the requested mode is already the best choice.
        """
        page = self._get_page(document_id, page_number)
        if page is None:
            return None, None

        struggle = self._struggle_level(page)

        # Build a human-readable reason from the actual signals
        def _quiz_str() -> str:
            if page.quiz_attempted and page.quiz_score is not None:
                return f"scored {page.quiz_score:.0%} on the quiz for this page"
            return ""

        def _help_str() -> str:
            total = page.reframes_count + page.explanations_count
            if total > 1:
                return f"requested help {total} times on this page"
            return ""

        def _assessment_str() -> str:
            if page.self_assessment == "not_clear":
                return "marked this page as not clear"
            if page.self_assessment == "somewhat_clear":
                return "marked this page as somewhat clear"
            return ""

        signals = [s for s in [_quiz_str(), _help_str(), _assessment_str()] if s]
        signal_text = " and ".join(signals) if signals else "your activity on this page"

        # High struggle
        if struggle == "high":
            if requested_mode == "quick_answer":
                return (
                    "step_by_step",
                    f"You {signal_text}. "
                    f"Step by Step mode may help build a stronger foundation."
                )
            if requested_mode == "deep_analysis":
                return (
                    "explain_concept",
                    f"You {signal_text}. "
                    f"Explain Concept mode may work better before going deep."
                )

        # Medium struggle
        if struggle == "medium" and requested_mode == "quick_answer":
            return (
                "explain_concept",
                f"You {signal_text}. "
                f"Explain Concept mode may give you a clearer understanding."
            )

        # Doing very well — suggest practice
        if (
            page.quiz_score is not None
            and page.quiz_score >= 0.85
            and requested_mode in ("quick_answer", "explain_concept")
        ):
            return (
                "practice_problems",
                f"You {_quiz_str() or 'are doing well on this page'}. "
                f"Practice Problems mode could help consolidate your knowledge."
            )

        # No suggestion needed
        return None, None

    # ------------------------------------------------------------------ #
    # Debug summary                                                         #
    # ------------------------------------------------------------------ #

    def get_adaptation_summary(
        self,
        document_id: str,
        page_number: Optional[int],
    ) -> dict:
        page = self._get_page(document_id, page_number)
        if page is None:
            return {
                "page_found": False,
                "struggle_level": "none",
                "style_hint_applied": False,
            }

        struggle = self._struggle_level(page)
        hint = self.get_style_hint(document_id, page_number)

        return {
            "page_found": True,
            "struggle_level": struggle,
            "style_hint_applied": bool(hint),
            "quiz_score": page.quiz_score,
            "self_assessment": page.self_assessment,
            "reframes_count": page.reframes_count,
            "explanations_count": page.explanations_count,
            "time_spent_seconds": page.time_spent_seconds,
        }