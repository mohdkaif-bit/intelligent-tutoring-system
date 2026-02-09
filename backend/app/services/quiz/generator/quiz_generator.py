"""
Quiz Generator - Refactored from quiz_generator.py
Enhanced with JSON parsing and robust error handling.
"""
from typing import List, Dict, Optional
import random
import json
import re

from app.services.llm.groq_client import get_llm_client
from app.core.logging import get_logger

logger = get_logger(__name__)


class QuizGenerator:
    """Service for generating quiz questions from course material."""
    
    def __init__(self):
        """Initialize quiz generator with LLM client."""
        self.llm_client = get_llm_client()
    
    def generate_from_page(
        self, 
        page_text: str, 
        page_number: int = 1, 
        num_questions: int = 2
    ) -> List[Dict[str, any]]:
        """
        Generate MCQ quiz questions from a single page.
        Returns questions with 4 options each (shuffled).
        
        Enhanced with:
        - JSON-based parsing for reliability
        - Multiple fallback strategies
        - Comprehensive validation
        - Better error messages
        
        Args:
            page_text: Text content of the page
            page_number: Page number for context
            num_questions: Number of questions to generate
        
        Returns:
            List of quiz questions with options
        """
        # Limit text to avoid token limits
        text_sample = page_text[:2500]
        
        # Try JSON format first (most reliable)
        try:
            questions = self._generate_json_format(text_sample, page_number, num_questions)
            if questions and len(questions) > 0:
                logger.info(f"Generated {len(questions)} questions using JSON format")
                return questions
        except Exception as e:
            logger.warning(f"JSON format failed: {e}")
        
        # Fallback to structured text format
        try:
            questions = self._generate_text_format(text_sample, page_number, num_questions)
            if questions and len(questions) > 0:
                logger.info(f"Generated {len(questions)} questions using text format")
                return questions
        except Exception as e:
            logger.warning(f"Text format failed: {e}")
        
        # Final fallback: generate simple comprehension questions
        try:
            questions = self._generate_simple_quiz(text_sample, num_questions)
            if questions and len(questions) > 0:
                logger.info(f"Generated {len(questions)} questions using simple format")
                return questions
        except Exception as e:
            logger.error(f"Simple format failed: {e}")
        
        # Ultimate fallback
        logger.warning("All generation methods failed, using fallback quiz")
        return self._create_fallback_quiz(num_questions)
    
    def _generate_json_format(
        self, 
        text_sample: str, 
        page_number: int, 
        num_questions: int
    ) -> List[Dict[str, any]]:
        """Generate quiz using JSON format for reliable parsing."""
        prompt = f"""Generate EXACTLY {num_questions} multiple choice questions from the content below.

Content from Page {page_number}:
{text_sample}

Output ONLY valid JSON in this exact format (no markdown, no extra text):
{{
  "questions": [
    {{
      "question": "What is the main concept discussed?",
      "correct": "The actual correct answer",
      "wrong1": "First incorrect option",
      "wrong2": "Second incorrect option", 
      "wrong3": "Third incorrect option"
    }}
  ]
}}

Requirements:
- Focus on key concepts from this page
- Make wrong answers plausible but clearly incorrect
- Keep questions clear and concise
- Output ONLY the JSON, nothing else"""

        response = self.llm_client.invoke(prompt, mode="quick_answer")
        
        # Clean response - remove markdown code blocks if present
        response = re.sub(r'^```json\s*', '', response)
        response = re.sub(r'^```\s*', '', response)
        response = re.sub(r'\s*```$', '', response)
        response = response.strip()
        
        # Parse JSON
        data = json.loads(response)
        questions_data = data.get("questions", [])
        
        if not questions_data:
            raise ValueError("No questions in JSON response")
        
        # Convert to quiz format with shuffled options
        quiz_questions = []
        for q_data in questions_data[:num_questions]:
            question_text = q_data.get("question", "").strip()
            correct_ans = q_data.get("correct", "").strip()
            wrong1 = q_data.get("wrong1", "").strip()
            wrong2 = q_data.get("wrong2", "").strip()
            wrong3 = q_data.get("wrong3", "").strip()
            
            # Validate all fields present
            if not all([question_text, correct_ans, wrong1, wrong2, wrong3]):
                continue
            
            # Shuffle options
            all_options = [correct_ans, wrong1, wrong2, wrong3]
            random.shuffle(all_options)
            
            # Find correct answer position
            correct_position = all_options.index(correct_ans)
            correct_letter = ['A', 'B', 'C', 'D'][correct_position]
            
            quiz_questions.append({
                "question": question_text,
                "options": {
                    "A": all_options[0],
                    "B": all_options[1],
                    "C": all_options[2],
                    "D": all_options[3]
                },
                "correct_answer": correct_letter
            })
        
        return quiz_questions
    
    def _generate_text_format(
        self, 
        text_sample: str, 
        page_number: int, 
        num_questions: int
    ) -> List[Dict[str, any]]:
        """Generate quiz using structured text format."""
        prompt = f"""Generate EXACTLY {num_questions} multiple choice questions from THIS PAGE ONLY.

Page {page_number} Content:
{text_sample}

For EACH question, output in this EXACT format:

Q: [Your question here]
CORRECT: [Correct answer]
WRONG1: [Wrong answer 1]
WRONG2: [Wrong answer 2]
WRONG3: [Wrong answer 3]
---

Requirements:
- Focus on key concepts from this page
- Make distractors plausible but clearly incorrect
- Keep questions clear and specific

Generate {num_questions} questions now:"""
        
        response = self.llm_client.invoke(prompt, mode="quick_answer")
        questions = []
        blocks = response.split('---')
        
        for block in blocks:
            if not block.strip():
                continue
            
            # Parse block
            question_text = ""
            correct_option = ""
            wrong_options = []
            
            for line in block.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('Q:'):
                    question_text = line[2:].strip()
                elif line.startswith('CORRECT:'):
                    correct_option = line[8:].strip()
                elif line.startswith('WRONG1:'):
                    wrong_options.append(line[7:].strip())
                elif line.startswith('WRONG2:'):
                    wrong_options.append(line[7:].strip())
                elif line.startswith('WRONG3:'):
                    wrong_options.append(line[7:].strip())
            
            # Validate all components present
            if not question_text or not correct_option or len(wrong_options) != 3:
                continue
            
            # Shuffle options
            all_options = [correct_option] + wrong_options
            random.shuffle(all_options)
            
            correct_position = all_options.index(correct_option)
            correct_letter = ['A', 'B', 'C', 'D'][correct_position]
            
            questions.append({
                "question": question_text,
                "options": {
                    "A": all_options[0],
                    "B": all_options[1],
                    "C": all_options[2],
                    "D": all_options[3]
                },
                "correct_answer": correct_letter
            })
        
        return questions[:num_questions]
    
    def _generate_simple_quiz(self, text_sample: str, num_questions: int) -> List[Dict[str, any]]:
        """Generate simple comprehension questions as fallback."""
        # Extract key topics first
        topic_prompt = f"""Read this text and identify {num_questions} main topics or concepts.
List them as: 1. Topic, 2. Topic, etc.

Text:
{text_sample}

Topics:"""
        
        topics_response = self.llm_client.invoke(topic_prompt, mode="quick_answer")
        
        # Parse topics
        topics = []
        for line in topics_response.split('\n'):
            line = line.strip()
            if re.match(r'^\d+\.', line):
                topic = re.sub(r'^\d+\.\s*', '', line).strip()
                if topic:
                    topics.append(topic)
        
        if not topics:
            raise ValueError("Could not extract topics")
        
        # Generate questions about topics
        questions = []
        for i, topic in enumerate(topics[:num_questions]):
            q_prompt = f"""Create ONE multiple choice question about: {topic}

Based on this text:
{text_sample[:1000]}

Output format:
Q: [question]
A: [correct answer]
B: [wrong answer]
C: [wrong answer]
D: [wrong answer]"""
            
            q_response = self.llm_client.invoke(q_prompt, mode="quick_answer")
            
            # Parse response
            lines = [l.strip() for l in q_response.split('\n') if l.strip()]
            
            question_text = ""
            options_dict = {}
            
            for line in lines:
                if line.startswith('Q:'):
                    question_text = line[2:].strip()
                elif line.startswith('A:'):
                    options_dict['A'] = line[2:].strip()
                elif line.startswith('B:'):
                    options_dict['B'] = line[2:].strip()
                elif line.startswith('C:'):
                    options_dict['C'] = line[2:].strip()
                elif line.startswith('D:'):
                    options_dict['D'] = line[2:].strip()
            
            if question_text and len(options_dict) == 4:
                questions.append({
                    "question": question_text,
                    "options": options_dict,
                    "correct_answer": "A"  # First option is correct in this format
                })
        
        return questions
    
    def _create_fallback_quiz(self, num_questions: int) -> List[Dict[str, any]]:
        """Create generic fallback quiz when all else fails."""
        questions = []
        
        templates = [
            {
                "question": "What is the main topic discussed in this section?",
                "correct": "The key concepts presented in the text",
                "wrong": ["Unrelated topic A", "Unrelated topic B", "Unrelated topic C"]
            },
            {
                "question": "Which statement best describes the content?",
                "correct": "Information relevant to the page content",
                "wrong": ["Completely different subject", "Another unrelated idea", "Something not discussed"]
            }
        ]
        
        for i in range(min(num_questions, len(templates))):
            template = templates[i]
            
            all_options = [template["correct"]] + template["wrong"]
            random.shuffle(all_options)
            
            correct_position = all_options.index(template["correct"])
            correct_letter = ['A', 'B', 'C', 'D'][correct_position]
            
            questions.append({
                "question": template["question"],
                "options": {
                    "A": all_options[0],
                    "B": all_options[1],
                    "C": all_options[2],
                    "D": all_options[3]
                },
                "correct_answer": correct_letter
            })
        
        return questions