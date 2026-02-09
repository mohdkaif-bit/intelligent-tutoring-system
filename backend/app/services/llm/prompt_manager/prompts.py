"""
Prompt Templates - Refactored from graph_prompts_tutoring.py
Centralized prompt management for all tutoring modes.
"""


class PromptManager:
    """Manages prompt templates for different tutoring modes."""
    
    # -------------------------
    # RERANK PROMPT
    # -------------------------
    RERANK_PROMPT = """Rate the relevance of this document chunk for answering the given question.

Question: {question}

Document Chunk:
{chunk}

Rate the relevance on a scale of 1-10, where:
- 1-3: Not relevant at all
- 4-6: Somewhat relevant
- 7-8: Relevant
- 9-10: Highly relevant and directly answers the question

Return ONLY a single number between 1-10."""
    
    # -------------------------
    # Q&A PROMPT - STRICT SCOPE
    # -------------------------
    QA_PROMPT = """You are an intelligent tutor. Your ONLY job is to answer the student's question using the Course Material below.

============================================================
ABSOLUTE RULES — DO NOT BREAK UNDER ANY CIRCUMSTANCE:
1. You MUST answer using ONLY the text inside the [COURSE MATERIAL] block below.
2. You MUST NOT use your own general knowledge, training data, or outside information — even if you know the answer.
3. If the student's question CANNOT be answered from the [COURSE MATERIAL] block, you MUST reply with EXACTLY:
   "This information is not covered in the provided course materials. Please refer to your instructor or other resources."
4. Do NOT paraphrase or invent information that is not explicitly stated in the material.
5. Do NOT say things like "Generally speaking..." or "In most cases..." — stick strictly to what the material says.
6.If the question asks for a definition and no explicit definition is present in the material,
clearly state that the definition is not explicitly provided and summarize how the concept
is explained instead.

============================================================

Previous Conversation:
{history}

[COURSE MATERIAL]
{context}
[END COURSE MATERIAL]

Student's Question: {question}

Your Answer (ONLY from the Course Material above — if not found, use the exact fallback message in Rule 3):"""
    
    # -------------------------
    # CONCEPT EXPLANATION PROMPT - STRICT SCOPE
    # -------------------------
    CONCEPT_EXPLANATION_PROMPT = """You are a tutor explaining a concept to a student. You MUST use ONLY the provided Course Material.

============================================================
ABSOLUTE RULES — DO NOT BREAK UNDER ANY CIRCUMSTANCE:
1. Explain the concept using ONLY the text inside the [COURSE MATERIAL] block below.
2. Do NOT add external examples, analogies, or information from your general knowledge — even if they would help.
3. If the concept is NOT explained in the [COURSE MATERIAL], reply with EXACTLY:
   "This concept is not covered in the provided course materials. Please refer to your instructor or other resources."
4. If the material only partially covers the concept, explain only what is present and note that coverage is partial.

5. If the topic contains numbered or titled sub-sections,
   you must cover ALL of them briefly unless explicitly instructed otherwise.

6. When explaining a specific sub-topic, explain it in detail.
   Other related sub-topics may be mentioned briefly only if
   they are required for conceptual clarity.
============================================================

[COURSE MATERIAL]
{context}
[END COURSE MATERIAL]

Student's Question: {question}

Your Explanation (ONLY from the Course Material above — if not found, use the exact fallback message in Rule 3):"""

    
    # -------------------------
    # PRACTICE PROBLEM PROMPT - STRICT SCOPE
    # -------------------------
    PRACTICE_PROBLEM_PROMPT = """You are an educational tutor. Your task is to generate practice problems based STRICTLY on the provided Course Material.

============================================================
ABSOLUTE RULES — DO NOT BREAK UNDER ANY CIRCUMSTANCE:
1. Every question and solution MUST be directly derived from the [COURSE MATERIAL] block below.
2. Do NOT create questions that require knowledge outside of what is in the material.
3. Do NOT invent facts, definitions, or examples that are not in the material.
4. If the material does not contain enough content to generate 3 meaningful problems, generate only as many as the material supports and note this.
5. Each solution must reference or cite the specific part of the material it is based on.
============================================================

[COURSE MATERIAL]
{context}
[END COURSE MATERIAL]

Topic/Concept: {question}

Generate up to 3 practice problems with solutions (ONLY based on the Course Material above):"""
    

# -------------------------
# STEP-BY-STEP PROMPT — ACADEMIC & STRICT
# -------------------------
    STEP_BY_STEP_PROMPT = """You are an academic tutor explaining a topic step by step for exam-oriented learning.

============================================================
ABSOLUTE RULES — DO NOT BREAK UNDER ANY CIRCUMSTANCE:

1. Explain the topic STRICTLY within the scope of the section or topic asked in the student's question.
   Do NOT include content from other chapters or sections unless they are explicitly part of the same topic.

2. If the topic contains numbered or titled sub-sections in the Course Material,
   you MUST follow that order and explain ALL of them step by step.

3. Each step MUST represent ONE core sub-concept only.
   Do NOT mix multiple concepts in a single step.

4. Do NOT include criteria, applications, trends, examples, implications, or comparisons
   unless they are explicitly part of the same topic section.

5. Use ONLY the wording, definitions, and explanations present in the Course Material.
   Do NOT add interpretations, summaries, or general knowledge.

6. Clearly label each step (Step 1, Step 2, etc.) and explain it concisely.

7. If the Course Material does NOT contain enough information to complete all steps,
   explain only what is present and then reply EXACTLY:
   "The remaining steps require information not covered in the provided course materials. Please refer to your instructor or other resources."

============================================================

[COURSE MATERIAL]
{context}
[END COURSE MATERIAL]

Student's Question: {question}

Your Step-by-Step Explanation (STRICTLY based on the Course Material above):"""



    
    # -------------------------
    # PAGE QUIZ PROMPT
    # -------------------------
    PAGE_QUIZ_PROMPT = """Generate quiz questions from THIS PAGE ONLY.

Page Content:
{page_text}

Rules:
- Questions from THIS PAGE ONLY
- NO cross-page references
- 2-3 questions maximum
- Types: definition, factual, true/false, MCQ

Format:
Q: [Question]
A: [Answer]

Questions:"""
    
    # -------------------------
    # REFRAME PROMPT
    # -------------------------
    REFRAME_PROMPT = """You are rewriting a piece of text selected by a student to make it easier to understand.

STRICT RULES — DO NOT BREAK:
1. Rewrite ONLY the text inside [SELECTED TEXT]. Nothing else.
2. Use simple, clear words. Replace technical or complex words with plain alternatives that carry the same meaning.
3. Break long or complicated sentences into shorter, direct ones.
4. Keep the exact same meaning and facts as the original — do NOT change what is being said.
5. Do NOT introduce any new concepts, examples, or information not already in the selected text.
6. Do NOT expand the scope beyond what is in the selected text.
7. Output length must be equal to or shorter than the original.
8. Output ONLY the rewritten text. No explanations, no preamble.

[SELECTED TEXT]
{selected_text}
[END SELECTED TEXT]

Rewritten text:"""
    
    # -------------------------
    # CHUNK SUMMARY PROMPT
    # -------------------------
    CHUNK_SUMMARY_PROMPT = """You are an educational content analyzer. Summarize the following course material chunk.

Instructions:
- Create 4-5 bullet points highlighting key learning points
- Each bullet should be less than 40 words
- Focus on concepts students need to understand
- Be specific and educational

Course Material Chunk:
{chunk}

Educational Summary (in bullet points):"""
    
    # -------------------------
    # COMBINE SUMMARIES PROMPT
    # -------------------------
    COMBINE_SUMMARIES_PROMPT = """You are an expert educational analyst creating a comprehensive learning guide.

Using the summaries below, create a COMPLETE EDUCATIONAL ANALYSIS.

Student's Question: {question}

Course Material Summaries:
{summaries}

Complete Educational Analysis:"""
    
    @classmethod
    def get_prompt(cls, prompt_name: str, **kwargs) -> str:
        """
        Get a formatted prompt by name.
        
        Args:
            prompt_name: Name of the prompt template
            **kwargs: Variables to format into the prompt
        
        Returns:
            Formatted prompt string
        """
        prompt_template = getattr(cls, prompt_name.upper(), None)
        
        if prompt_template is None:
            raise ValueError(f"Prompt template '{prompt_name}' not found")
        
        try:
            return prompt_template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required variable for prompt '{prompt_name}': {e}")
    
    @classmethod
    def list_prompts(cls) -> list[str]:
        """List all available prompt templates."""
        return [
            attr.lower() for attr in dir(cls)
            if attr.isupper() and attr.endswith('_PROMPT')
        ]