"""
RAG Graph - Main workflow orchestration using LangGraph.
Refactored from rag_graph_tutoring.py with cleaner architecture.
"""
from langgraph.graph import StateGraph, START, END

from app.services.rag.graph.state import RAGState
from app.services.rag.graph.nodes import RAGNodes
from app.core.logging import get_logger

logger = get_logger(__name__)


class RAGGraph:
    """
    RAG workflow graph using LangGraph.
    Orchestrates document retrieval, reranking, and answer generation.
    """
    
    def __init__(self):
        """Initialize RAG graph with nodes."""
        self.nodes = RAGNodes()
        self.graph = self._build_graph()
        logger.info("Initialized RAG Graph")
    
    def _build_graph(self):
        """
        Build the RAG workflow graph.
        
        Returns:
            Compiled LangGraph workflow
        """
        # Create state graph
        workflow = StateGraph(RAGState)
        
        # Add nodes
        workflow.add_node("retrieve", self.nodes.retrieve_node)
        workflow.add_node("rerank", self.nodes.rerank_node)
        workflow.add_node("summarize_chunks", self.nodes.summarize_chunks_node)
        workflow.add_node("combine", self.nodes.combine_summaries_node)
        workflow.add_node("quick_answer", self.nodes.quick_answer_node)
        workflow.add_node("explain_concept", self.nodes.explain_concept_node)
        workflow.add_node("step_by_step", self.nodes.step_by_step_node)
        workflow.add_node("generate_practice", self.nodes.generate_practice_node)
        workflow.add_node("update_history", self.nodes.update_history_node)
        
        # Define flow
        workflow.add_edge(START, "retrieve")
        workflow.add_edge("retrieve", "rerank")
        
        # Mode-based routing after rerank
        workflow.add_conditional_edges(
            "rerank",
            lambda state: state.get("mode", "quick_answer"),
            {
                "quick_answer": "quick_answer",
                "explain_concept": "explain_concept",
                "step_by_step": "step_by_step",
                "practice_problems": "generate_practice",
                "deep_analysis": "summarize_chunks"
            }
        )
        
        # Deep analysis path
        workflow.add_edge("summarize_chunks", "combine")
        
        # All paths lead to history update
        workflow.add_edge("quick_answer", "update_history")
        workflow.add_edge("explain_concept", "update_history")
        workflow.add_edge("step_by_step", "update_history")
        workflow.add_edge("generate_practice", "update_history")
        workflow.add_edge("combine", "update_history")
        
        # End after history update
        workflow.add_edge("update_history", END)
        
        logger.info("Built RAG graph workflow")
        return workflow.compile()
    
    def invoke(self, state: dict) -> dict:
        """
        Execute the RAG workflow.
        
        Args:
            state: Initial state dictionary
        
        Returns:
            Final state after workflow execution
        """
        try:
            logger.info(f"Invoking RAG graph for mode: {state.get('mode', 'quick_answer')}")
            result = self.graph.invoke(state)
            logger.info("RAG graph execution completed")
            return result
        except Exception as e:
            logger.error(f"Error executing RAG graph: {e}")
            raise