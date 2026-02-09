"""
RAG Graph State Definition
Defines the state structure for the RAG workflow graph.
"""
from typing import Dict, List, Any, Optional
from langchain_core.documents import Document


class RAGState(Dict):
    """
    State for RAG graph workflow.
    
    This TypedDict-like class defines all state variables
    that flow through the RAG graph nodes.
    """
    # Input
    question: str                          # User's question
    mode: str                              # Tutoring mode
    retriever: Any                         # Retriever instance
    
    # Documents
    docs: List[Document]                   # Retrieved documents
    top_docs: List[Document]               # Top ranked documents
    
    # Summaries (for deep analysis)
    per_chunk_summaries: List[str]         # Individual chunk summaries
    final_report: str                      # Combined analysis
    
    # Output
    answer: str                            # Final answer
    
    # Conversation
    history: List[Dict[str, str]]          # Chat history
    
    # Configuration
    difficulty_level: str                  # Difficulty setting
    show_steps: bool                       # Show step-by-step
    generate_practice: bool                # Generate practice problems
    
    # Context (new additions)
    page_number: Optional[int]             # Current page number
    selected_text: Optional[str]           # Selected text for context