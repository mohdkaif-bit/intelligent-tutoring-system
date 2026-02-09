"""
Chat API Routes
Handles question answering using RAG system.
"""
from fastapi import APIRouter, HTTPException, status

from app.models.chat.schemas import ChatRequest, ChatResponse
from app.storage.documents import DocumentStorage
from app.services.rag.graph.rag_graph import RAGGraph
from app.services.rag.retriever.vector_retriever import VectorRetriever
from app.storage.user_memory import LearningMemory
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

DEFAULT_USER_ID = "default_user"


@router.post("/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest):
    """
    Ask a question about course materials using RAG.
    
    Args:
        request: Chat request with question, mode, and context
    
    Returns:
        AI-generated answer based on course materials
    """
    try:
        # Get document
        doc_storage = DocumentStorage(user_id=DEFAULT_USER_ID)
        doc_path = doc_storage.get_document_path(request.document_id)
        
        if not doc_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {request.document_id} not found"
            )
        
        # Load vector store and retriever
        vector_retriever = VectorRetriever()
        vectorstore, retriever = vector_retriever.load_or_create_vectorstore(
            document_id=request.document_id,
            pdf_path=doc_path
        )
        
        # Initialize RAG graph
        rag_graph = RAGGraph()
        
        # Prepare state
        initial_state = {
            "question": request.question,
            "mode": request.mode,
            "retriever": retriever,
            "docs": [],
            "top_docs": [],
            "answer": "",
            "history": request.history,
            "difficulty_level": "intermediate",
            "show_steps": True,
            "generate_practice": request.mode == "practice_problems",
            "page_number": request.page_number,
            "selected_text": None
        }
        
        # Execute RAG workflow
        result = rag_graph.invoke(initial_state)
        answer = result.get("answer", "Error generating response")
        
        # Update learning memory - explanation requested
        if request.page_number:
            memory = LearningMemory(user_id=DEFAULT_USER_ID)
            memory.update_explanation(
                document_id=request.document_id,
                page_number=request.page_number
            )
        
        logger.info(f"Generated answer for question in mode: {request.mode}")
        
        return ChatResponse(
            success=True,
            answer=answer,
            mode=request.mode,
            error=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        return ChatResponse(
            success=False,
            answer="",
            mode=request.mode,
            error=f"Failed to process question: {str(e)}"
        )