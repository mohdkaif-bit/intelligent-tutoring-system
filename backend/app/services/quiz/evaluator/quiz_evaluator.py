"""
Quiz Evaluator - Simple MCQ answer evaluation.
"""
from typing import Dict, List

from app.core.logging import get_logger

logger = get_logger(__name__)


class QuizEvaluator:
    """Service for evaluating quiz answers."""
    
    @staticmethod
    def evaluate_answer(student_answer: str, correct_answer: str) -> str:
        """
        Evaluate MCQ answer - simple exact match.
        
        Args:
            student_answer: Student's choice (A/B/C/D)
            correct_answer: Correct answer (A/B/C/D)
        
        Returns:
            "CORRECT" or "INCORRECT"
        """
        # Normalize answers
        student_answer = str(student_answer).strip().upper()
        correct_answer = str(correct_answer).strip().upper()
        
        # Validate answers are A/B/C/D
        if student_answer not in ['A', 'B', 'C', 'D']:
            logger.warning(f"Invalid student answer: {student_answer}")
            return "INCORRECT"
        
        if correct_answer not in ['A', 'B', 'C', 'D']:
            logger.error(f"Invalid correct answer: {correct_answer}")
            return "INCORRECT"
        
        # Simple exact match
        result = "CORRECT" if student_answer == correct_answer else "INCORRECT"
        logger.debug(f"Evaluation: {student_answer} vs {correct_answer} = {result}")
        return result
    
    @staticmethod
    def evaluate_quiz(
        answers: Dict[int, str], 
        questions: List[Dict]
    ) -> Dict:
        """
        Evaluate entire quiz submission.
        
        Args:
            answers: Dict mapping question index to student answer
            questions: List of quiz questions with correct answers
        
        Returns:
            Evaluation results with score and details
        """
        results = []
        correct_count = 0
        
        for idx, question in enumerate(questions):
            student_answer = answers.get(idx, "")
            correct_answer = question.get("correct_answer", "")
            
            result = QuizEvaluator.evaluate_answer(student_answer, correct_answer)
            results.append(result)
            
            if result == "CORRECT":
                correct_count += 1
        
        total_questions = len(questions)
        score = correct_count / total_questions if total_questions > 0 else 0.0
        
        logger.info(f"Quiz evaluated: {correct_count}/{total_questions} correct ({score:.2%})")
        
        return {
            "score": score,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "results": results
        }