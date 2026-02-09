"""
Semantic Learning Memory for Intelligent Tutoring System
UPDATED to return fields that match frontend expectations
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, asdict
from pathlib import Path

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


@dataclass
class PageInteraction:
    """
    Evidence of interaction with a single page.
    Stores ONLY observable events, not inferred understanding.
    """
    page_number: int
    document_id: str
    
    # Viewing evidence
    viewed: bool = False
    time_spent_seconds: int = 0
    
    # Interaction counts (observable actions)
    selections_count: int = 0
    reframes_count: int = 0
    explanations_count: int = 0
    questions_asked_count: int = 0  # ADDED: Track chat questions
    
    # Quiz evidence
    quiz_attempted: bool = False
    quiz_score: Optional[float] = None
    
    # Self-reported clarity (user's own assessment, not system inference)
    self_assessment: Optional[Literal["not_clear", "somewhat_clear", "very_clear"]] = None
    
    # Temporal evidence
    last_interaction_timestamp: Optional[str] = None
    first_viewed_timestamp: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PageInteraction':
        """Create from dictionary."""
        # Handle old data without questions_asked_count
        if 'questions_asked_count' not in data:
            data['questions_asked_count'] = 0
        return cls(**data)


class LearningMemory:
    """
    Persistent semantic memory for learning interactions.
    
    Stores evidence of user interactions with course materials.
    Does NOT store content, chat history, or inferred understanding.
    """
    
    def __init__(self, user_id: str, storage_dir: Optional[Path] = None):
        """
        Initialize learning memory for a user.
        
        Args:
            user_id: Unique identifier for the user
            storage_dir: Directory to store memory files
        """
        self.user_id = user_id
        self.storage_dir = storage_dir or settings.MEMORY_STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.memory_file = self.storage_dir / f"{user_id}_memory.json"
        self.memory: Dict[str, Dict[int, PageInteraction]] = {}
        
        self._load_memory()
        logger.info(f"Initialized LearningMemory for user: {user_id}")
    
    def _load_memory(self):
        """Load memory from disk if it exists."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                
                # Reconstruct PageInteraction objects
                for doc_id, pages in data.items():
                    self.memory[doc_id] = {}
                    for page_num_str, page_data in pages.items():
                        page_num = int(page_num_str)
                        self.memory[doc_id][page_num] = PageInteraction.from_dict(page_data)
                
                logger.info(f"Loaded memory for user {self.user_id}")
            except Exception as e:
                # If loading fails, start with empty memory
                logger.error(f"Could not load memory: {e}")
                self.memory = {}
    
    def _save_memory(self):
        """Persist memory to disk."""
        data = {}
        for doc_id, pages in self.memory.items():
            data[doc_id] = {}
            for page_num, interaction in pages.items():
                data[doc_id][str(page_num)] = interaction.to_dict()
        
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug("Memory saved successfully")
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            raise
    
    def get_or_create_page(self, document_id: str, page_number: int) -> PageInteraction:
        """Get existing page interaction or create new one."""
        if document_id not in self.memory:
            self.memory[document_id] = {}
        
        if page_number not in self.memory[document_id]:
            self.memory[document_id][page_number] = PageInteraction(
                page_number=page_number,
                document_id=document_id
            )
        
        return self.memory[document_id][page_number]
    
    def update_page_view(self, document_id: str, page_number: int, time_spent: int = 0):
        """
        Record evidence of page viewing.
        
        Args:
            document_id: Identifier for the document
            page_number: Page number (1-indexed)
            time_spent: Additional time spent on page in seconds
        """
        page = self.get_or_create_page(document_id, page_number)
        
        if not page.viewed:
            page.viewed = True
            page.first_viewed_timestamp = datetime.now().isoformat()
        
        page.time_spent_seconds += time_spent
        page.last_interaction_timestamp = datetime.now().isoformat()
        
        self._save_memory()
        logger.debug(f"Updated page view: doc={document_id}, page={page_number}")
    
    def update_selection(self, document_id: str, page_number: int):
        """Record evidence of text selection."""
        page = self.get_or_create_page(document_id, page_number)
        page.selections_count += 1
        page.last_interaction_timestamp = datetime.now().isoformat()
        self._save_memory()
        logger.debug(f"Updated selection: doc={document_id}, page={page_number}")
    
    def update_reframe(self, document_id: str, page_number: int):
        """Record evidence of reframe request."""
        page = self.get_or_create_page(document_id, page_number)
        page.reframes_count += 1
        page.last_interaction_timestamp = datetime.now().isoformat()
        self._save_memory()
        logger.debug(f"Updated reframe: doc={document_id}, page={page_number}")
    
    def update_explanation(self, document_id: str, page_number: int):
        """Record evidence of explanation request (chat mode)."""
        page = self.get_or_create_page(document_id, page_number)
        page.explanations_count += 1
        # ALSO increment questions_asked_count
        page.questions_asked_count += 1
        page.last_interaction_timestamp = datetime.now().isoformat()
        self._save_memory()
        logger.debug(f"Updated explanation: doc={document_id}, page={page_number}")
    
    def update_quiz(self, document_id: str, page_number: int, score: float):
        """
        Record evidence of quiz attempt and score.
        
        Args:
            document_id: Identifier for the document
            page_number: Page number (1-indexed)
            score: Quiz score as float between 0.0 and 1.0
        """
        page = self.get_or_create_page(document_id, page_number)
        page.quiz_attempted = True
        page.quiz_score = score
        page.last_interaction_timestamp = datetime.now().isoformat()
        self._save_memory()
        logger.debug(f"Updated quiz: doc={document_id}, page={page_number}, score={score}")
    
    def update_self_assessment(
        self, 
        document_id: str, 
        page_number: int, 
        assessment: Literal["not_clear", "somewhat_clear", "very_clear"]
    ):
        """
        Record user's self-reported clarity assessment.
        
        Args:
            document_id: Identifier for the document
            page_number: Page number (1-indexed)
            assessment: User's self-assessment of clarity
        """
        page = self.get_or_create_page(document_id, page_number)
        page.self_assessment = assessment
        page.last_interaction_timestamp = datetime.now().isoformat()
        self._save_memory()
        logger.debug(f"Updated self-assessment: doc={document_id}, page={page_number}, assessment={assessment}")
    
    def get_account_progress(self) -> Dict:
        """
        Calculate account-level progress metrics across all documents.
        
        UPDATED: Returns fields that match frontend Home.tsx expectations
        
        Returns evidence-based statistics ONLY.
        Does NOT infer mastery or understanding.
        """
        total_pages = 0
        pages_viewed = 0
        pages_with_engagement = 0  # selections, reframes, or explanations
        pages_needing_attention = 0  # evidence of struggle
        quizzes_attempted = 0
        total_quiz_score = 0.0
        quiz_count = 0
        total_study_time_seconds = 0
        total_questions_asked = 0
        
        for doc_id, pages in self.memory.items():
            for page_num, interaction in pages.items():
                total_pages += 1
                
                if interaction.viewed:
                    pages_viewed += 1
                
                # Accumulate study time
                total_study_time_seconds += interaction.time_spent_seconds
                
                # Accumulate questions asked
                total_questions_asked += interaction.questions_asked_count
                
                # Engagement = any active interaction beyond viewing
                if (interaction.selections_count > 0 or 
                    interaction.reframes_count > 0 or 
                    interaction.explanations_count > 0):
                    pages_with_engagement += 1
                
                # Evidence suggesting need for attention
                needs_attention = False
                if interaction.quiz_attempted and interaction.quiz_score is not None:
                    if interaction.quiz_score < 0.7:
                        needs_attention = True
                
                if interaction.self_assessment == "not_clear":
                    needs_attention = True
                
                # Repeated reframes/explanations (>3) suggests struggle
                if interaction.reframes_count > 3 or interaction.explanations_count > 3:
                    needs_attention = True
                
                if needs_attention:
                    pages_needing_attention += 1
                
                if interaction.quiz_attempted:
                    quizzes_attempted += 1
                    if interaction.quiz_score is not None:
                        total_quiz_score += interaction.quiz_score
                        quiz_count += 1
        
        avg_quiz_score = (total_quiz_score / quiz_count) if quiz_count > 0 else None
        
        # Return fields matching frontend expectations
        return {
            # REQUIRED FIELDS (Frontend expects these exact field names)
            "study_time_minutes": total_study_time_seconds // 60,
            "total_pages_viewed": pages_viewed,
            "total_questions_asked": total_questions_asked,
            "total_quizzes_completed": quizzes_attempted,
            "average_quiz_score": (avg_quiz_score * 100) if avg_quiz_score is not None else None,
            
            # ADDITIONAL ANALYTICS (Optional, useful for debugging)
            "total_pages_uploaded": total_pages,
            "pages_with_engagement": pages_with_engagement,
            "pages_needing_attention": pages_needing_attention,
            "completion_rate": pages_viewed / total_pages if total_pages > 0 else 0.0,
            "engagement_rate": pages_with_engagement / total_pages if total_pages > 0 else 0.0
        }
    
    def get_revision_suggestions(self, max_suggestions: int = 10) -> List[Dict]:
        """
        Generate evidence-based revision suggestions.
        
        Suggestions are based ONLY on observable evidence:
        - Low quiz scores
        - Self-reported lack of clarity
        - Repeated help-seeking behavior
        - Very low time spent
        - Long time since last interaction
        
        Does NOT claim mastery or infer understanding level.
        
        Returns:
            List of suggestions with document_id, page_number, and reasons
        """
        suggestions = []
        now = datetime.now()
        
        for doc_id, pages in self.memory.items():
            for page_num, interaction in pages.items():
                if not interaction.viewed:
                    continue  # Skip pages never viewed
                
                reasons = []
                priority = 0
                
                # Evidence 1: Low quiz score
                if interaction.quiz_attempted and interaction.quiz_score is not None:
                    if interaction.quiz_score < 0.5:
                        reasons.append(f"quiz score: {interaction.quiz_score:.0%}")
                        priority += 3
                    elif interaction.quiz_score < 0.7:
                        reasons.append(f"quiz score: {interaction.quiz_score:.0%}")
                        priority += 2
                
                # Evidence 2: Self-reported lack of clarity
                if interaction.self_assessment == "not_clear":
                    reasons.append("you marked this as not clear")
                    priority += 3
                
                # Evidence 3: Repeated help-seeking (reframes/explanations)
                total_help = interaction.reframes_count + interaction.explanations_count
                if total_help > 5:
                    reasons.append(f"{total_help} help requests")
                    priority += 2
                elif total_help > 3:
                    reasons.append(f"{total_help} help requests")
                    priority += 1
                
                # Evidence 4: Very low time spent (< 1 minute for viewed page)
                if interaction.time_spent_seconds < 60 and interaction.time_spent_seconds > 0:
                    reasons.append(f"only {interaction.time_spent_seconds}s spent")
                    priority += 1
                
                # Evidence 5: Long time since last interaction (> 7 days)
                if interaction.last_interaction_timestamp:
                    try:
                        last_time = datetime.fromisoformat(interaction.last_interaction_timestamp)
                        days_ago = (now - last_time).days
                        if days_ago > 7:
                            reasons.append(f"last viewed {days_ago} days ago")
                            priority += 1
                    except:
                        pass
                
                # Add suggestion if there's evidence
                if reasons:
                    suggestions.append({
                        "document_id": doc_id,
                        "page_number": page_num,
                        "priority": priority,
                        "reasons": reasons,
                        "suggestion": f"You may want to revisit Page {page_num} of {doc_id}"
                    })
        
        # Sort by priority (highest first) and limit
        suggestions.sort(key=lambda x: x["priority"], reverse=True)
        return suggestions[:max_suggestions]
    
    def get_document_progress(self, document_id: str) -> Dict:
        """
        Get progress for a specific document.
        
        Returns evidence-based statistics for one document.
        """
        if document_id not in self.memory:
            return {
                "document_id": document_id,
                "total_pages": 0,
                "pages_viewed": 0,
                "pages_with_engagement": 0,
                "quizzes_attempted": 0
            }
        
        pages = self.memory[document_id]
        total_pages = len(pages)
        pages_viewed = sum(1 for p in pages.values() if p.viewed)
        pages_with_engagement = sum(
            1 for p in pages.values() 
            if p.selections_count > 0 or p.reframes_count > 0 or p.explanations_count > 0
        )
        quizzes_attempted = sum(1 for p in pages.values() if p.quiz_attempted)
        
        return {
            "document_id": document_id,
            "total_pages": total_pages,
            "pages_viewed": pages_viewed,
            "pages_with_engagement": pages_with_engagement,
            "quizzes_attempted": quizzes_attempted,
            "completion_rate": pages_viewed / total_pages if total_pages > 0 else 0.0
        }
    
    def clear_document(self, document_id: str):
        """Remove all memory for a specific document."""
        if document_id in self.memory:
            del self.memory[document_id]
            self._save_memory()
            logger.info(f"Cleared memory for document: {document_id}")
    
    def clear_all(self):
        """Clear all memory (use with caution)."""
        self.memory = {}
        self._save_memory()
        logger.warning(f"Cleared ALL memory for user: {self.user_id}")