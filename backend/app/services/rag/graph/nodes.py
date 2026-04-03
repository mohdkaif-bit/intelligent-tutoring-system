"""
RAG Graph Nodes - Individual processing steps in the workflow.
Refactored from rag_graph_tutoring.py with improvements.
"""
from typing import Dict, List, Any
from langchain_core.documents import Document

from app.services.llm.groq_client import get_llm_client
from app.services.llm.prompt_manager.prompts import PromptManager
from app.services.rag.graph.state import RAGState
from app.core.logging import get_logger

logger = get_logger(__name__)


class RAGNodes:
    """Collection of nodes for RAG graph workflow."""
    
    def __init__(self):
        """Initialize with LLM client and prompt manager."""
        self.llm_client = get_llm_client()
        self.prompts = PromptManager()
    
    def retrieve_node(self, state: RAGState) -> Dict:
        """
        Retrieve relevant documents using vector similarity search.
        
        If the adaptation layer has already pre-retrieved and reranked
        documents, skip retrieval entirely and use those directly.
        
        Args:
            state: Current RAG state
        
        Returns:
            Updated state with retrieved documents
        """
        # If adaptation layer already pre-retrieved and reranked, skip retrieval
        if state.get("top_docs"):
            logger.info(
                "retrieve_node: using %d pre-ranked docs from adaptation layer",
                len(state["top_docs"])
            )
            return {"docs": state["top_docs"], "top_docs": state["top_docs"]}

        retriever = state.get("retriever")
        if not retriever:
            logger.warning("No retriever provided")
            return {"docs": [], "top_docs": []}
        
        query = state["question"]
        mode = state.get("mode", "quick_answer")
        
        # Adjust k based on mode
        k = 20 if mode in ["deep_analysis", "practice_problems"] else 6
        
        try:
            docs = list(retriever.invoke(query))[:k]
            logger.info(f"Retrieved {len(docs)} documents for query")
            
            return {"docs": docs, "top_docs": docs[:6]}
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return {"docs": [], "top_docs": []}
    
    def rerank_node(self, state: RAGState) -> Dict:
        """
        Rerank documents by relevance to the question.
        
        Args:
            state: Current RAG state
        
        Returns:
            Updated state with reranked documents
        """
        docs = state.get("top_docs", [])
        if not docs:
            logger.warning("No documents to rerank")
            return {"top_docs": []}
        
        query = state["question"]
        ranked = []
        
        for doc in docs:
            # Get relevance score from LLM
            prompt = self.prompts.get_prompt(
                "rerank_prompt",
                question=query,
                chunk=doc.page_content
            )
            
            try:
                raw_response = self.llm_client.invoke(prompt, mode="quick_answer")
                # Extract numeric score
                score = float(''.join(ch for ch in raw_response if ch.isdigit() or ch == '.'))
                score = max(1.0, min(10.0, score))  # Clamp to 1-10
            except Exception as e:
                logger.warning(f"Error getting rerank score: {e}, using default")
                score = 5.0
            
            ranked.append((score, doc))
        
        # Sort by score (highest first)
        ranked.sort(key=lambda x: x[0], reverse=True)
        sorted_docs = [doc for score, doc in ranked][:6]
        
        logger.info(f"Reranked {len(sorted_docs)} documents")
        return {"top_docs": sorted_docs or docs}
    
    def quick_answer_node(self, state: RAGState) -> Dict:
        """
        Generate quick answer from course material.
        
        Args:
            state: Current RAG state
        
        Returns:
            Updated state with answer
        """
        history_text = "\n".join(
            f"{h['role']}: {h['content']}" 
            for h in state.get("history", [])
        )
        
        context_text = "\n\n".join(
            doc.page_content 
            for doc in state.get("top_docs", [])
        )

        # Prepend style hint if adaptation layer provided one
        style_hint = state.get("style_hint", "")
        
        prompt = self.prompts.get_prompt(
            "qa_prompt",
            history="",
            context=context_text,
            question=state["question"]
        )

        # Inject style hint at the front of the prompt
        if style_hint:
            prompt = style_hint + prompt
        
        try:
            answer = self.llm_client.invoke(prompt, mode="quick_answer")
            logger.info("Generated quick answer")
        except Exception as e:
            logger.error(f"Error generating quick answer: {e}")
            answer = f"Error: {str(e)}"
        
        return {"answer": answer}
    
    def explain_concept_node(self, state: RAGState) -> Dict:
        """
        Explain a concept in detail.
        
        Args:
            state: Current RAG state
        
        Returns:
            Updated state with explanation
        """
        context_text = "\n\n".join(
            doc.page_content 
            for doc in state.get("top_docs", [])
        )

        style_hint = state.get("style_hint", "")
        
        prompt = self.prompts.get_prompt(
            "concept_explanation_prompt",
            context=context_text,
            question=state["question"]
        )

        if style_hint:
            prompt = style_hint + prompt
        
        try:
            answer = self.llm_client.invoke(prompt, mode="explain_concept")
            logger.info("Generated concept explanation")
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            answer = "Error generating explanation"
        
        return {"answer": answer}
    
    def step_by_step_node(self, state: RAGState) -> Dict:
        """
        Provide step-by-step solution.
        
        Args:
            state: Current RAG state
        
        Returns:
            Updated state with step-by-step guide
        """
        context_text = "\n\n".join(
            doc.page_content 
            for doc in state.get("top_docs", [])
        )

        style_hint = state.get("style_hint", "")
        
        prompt = self.prompts.get_prompt(
            "step_by_step_prompt",
            context=context_text,
            question=state["question"]
        )

        if style_hint:
            prompt = style_hint + prompt
        
        try:
            answer = self.llm_client.invoke(prompt, mode="step_by_step")
            logger.info("Generated step-by-step guide")
        except Exception as e:
            logger.error(f"Error generating step-by-step: {e}")
            answer = "Error"
        
        return {"answer": answer}
    
    def generate_practice_node(self, state: RAGState) -> Dict:
        """
        Generate practice problems.
        
        Args:
            state: Current RAG state
        
        Returns:
            Updated state with practice problems
        """
        context_text = "\n\n".join(
            doc.page_content 
            for doc in state.get("top_docs", [])
        )

        style_hint = state.get("style_hint", "")
        
        prompt = self.prompts.get_prompt(
            "practice_problem_prompt",
            context=context_text,
            question=state["question"]
        )

        if style_hint:
            prompt = style_hint + prompt
        
        try:
            answer = self.llm_client.invoke(prompt, mode="generate_practice")
            logger.info("Generated practice problems")
        except Exception as e:
            logger.error(f"Error generating practice problems: {e}")
            answer = "Error"
        
        return {"answer": answer}
    
    def summarize_chunks_node(self, state: RAGState) -> Dict:
        """
        Summarize individual document chunks (for deep analysis).
        
        Args:
            state: Current RAG state
        
        Returns:
            Updated state with chunk summaries
        """
        if state.get("mode") != "deep_analysis":
            return {"per_chunk_summaries": []}
        
        summaries = []
        
        for doc in state.get("docs", []):
            prompt = self.prompts.get_prompt(
                "chunk_summary_prompt",
                chunk=doc.page_content
            )
            
            try:
                summary = self.llm_client.invoke(prompt, mode="deep_analysis")
                summaries.append(summary)
            except Exception as e:
                logger.warning(f"Error summarizing chunk: {e}")
                continue
        
        logger.info(f"Summarized {len(summaries)} chunks")
        return {"per_chunk_summaries": summaries}
    
    def combine_summaries_node(self, state: RAGState) -> Dict:
        """
        Combine chunk summaries into final analysis.
        
        Args:
            state: Current RAG state
        
        Returns:
            Updated state with final report
        """
        summaries = state.get("per_chunk_summaries", [])
        
        if not summaries:
            logger.warning("No summaries to combine")
            return {"final_report": "No content available", "answer": "No content available"}
        
        summaries_text = "\n".join(f"- {s}" for s in summaries)
        
        prompt = self.prompts.get_prompt(
            "combine_summaries_prompt",
            question=state["question"],
            summaries=summaries_text
        )
        
        try:
            report = self.llm_client.invoke(prompt, mode="deep_analysis")
            logger.info("Combined summaries into final report")
        except Exception as e:
            logger.error(f"Error combining summaries: {e}")
            report = "Error generating report"
        
        return {"final_report": report, "answer": report}
    
    def update_history_node(self, state: RAGState) -> Dict:
        """
        Update conversation history.
        
        Args:
            state: Current RAG state
        
        Returns:
            Updated state with history
        """
        history = state.get("history", [])
        
        updated_history = history + [
            {"role": "user", "content": state["question"]},
            {"role": "assistant", "content": state.get("answer", "")}
        ]
        
        logger.debug(f"Updated history with {len(updated_history)} messages")
        return {"history": updated_history}