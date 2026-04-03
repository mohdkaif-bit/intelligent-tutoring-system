"""
Chat API Routes
Handles question answering using RAG system.

Adaptations applied per request:
  A - Style hint injected into prompt based on struggle signals
  B - Mode suggestion returned in response (advisory, never forced)
  C - Context re-ranked by struggle signals before RAG graph sees it
"""
from fastapi import APIRouter, HTTPException, status

from app.models.chat.schemas import ChatRequest, ChatResponse
from app.storage.documents import DocumentStorage
from app.services.rag.graph.rag_graph import RAGGraph
from app.services.rag.retriever.vector_retriever import VectorRetriever
from app.storage.user_memory import LearningMemory
from app.services.memory.adaptation import StyleAdapter, ContextRanker
from app.services.rag.eval_logger import log_interaction
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

DEFAULT_USER_ID = "default_user"


@router.post("/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest):
    """
    Ask a question about course materials using RAG.

    The user's requested mode is always respected.
    Adaptations A and C apply silently to improve answer quality.
    Adaptation B returns a suggestion the user can choose to act on.
    """
    try:
        # ---------------------------------------------------------------- #
        # 1. Resolve document path                                          #
        # ---------------------------------------------------------------- #
        doc_storage = DocumentStorage(user_id=DEFAULT_USER_ID)
        doc_path = doc_storage.get_document_path(request.document_id)

        if not doc_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {request.document_id} not found"
            )

        # ---------------------------------------------------------------- #
        # 2. Load vector store and retriever                                #
        # ---------------------------------------------------------------- #
        vector_retriever = VectorRetriever()
        vectorstore, retriever = vector_retriever.load_or_create_vectorstore(
            document_id=request.document_id,
            pdf_path=doc_path
        )

        # ---------------------------------------------------------------- #
        # 3. Adaptation B — compute suggestion (do NOT change request.mode) #
        # ---------------------------------------------------------------- #
        style_adapter = StyleAdapter(user_id=DEFAULT_USER_ID)

        suggested_mode, suggestion_reason = style_adapter.suggest_mode_with_reason(
            document_id=request.document_id,
            page_number=request.page_number,
            requested_mode=request.mode,
        )

        if suggested_mode:
            logger.info(
                "Adaptation B: suggesting %s instead of %s for page %s | reason: %s",
                suggested_mode, request.mode, request.page_number, suggestion_reason,
            )

        # ---------------------------------------------------------------- #
        # 4. Adaptation A — style hint injected into prompt                #
        # ---------------------------------------------------------------- #
        style_hint = style_adapter.get_style_hint(
            document_id=request.document_id,
            page_number=request.page_number,
        )

        if style_hint:
            logger.info(
                "Adaptation A: style hint applied for page %s (struggle: %s)",
                request.page_number,
                style_adapter.get_adaptation_summary(
                    request.document_id, request.page_number
                ).get("struggle_level"),
            )

        # ---------------------------------------------------------------- #
        # 5. Adaptation C — pre-retrieve and rerank by struggle signals    #
        # ---------------------------------------------------------------- #
        context_ranker = ContextRanker(user_id=DEFAULT_USER_ID)

        try:
            raw_docs = list(retriever.invoke(request.question))
            reranked_docs = context_ranker.rerank(
                docs=raw_docs,
                document_id=request.document_id,
            )
        except Exception as e:
            logger.warning("Context reranking failed (%s), using empty list.", e)
            reranked_docs = []

        # ---------------------------------------------------------------- #
        # 6. Build RAG graph state — use request.mode (user's choice)      #
        # ---------------------------------------------------------------- #
        rag_graph = RAGGraph()

        initial_state = {
            "question": request.question,
            "mode": request.mode,           # always the user's requested mode
            "style_hint": style_hint,       # A: injected into prompt nodes
            "retriever": retriever,
            "docs": reranked_docs,          # C: reranked docs
            "top_docs": reranked_docs[:6],  # C: reranked top docs
            "answer": "",
            "history": request.history,
            "difficulty_level": "intermediate",
            "show_steps": True,
            "generate_practice": request.mode == "practice_problems",
            "page_number": request.page_number,
            "selected_text": None,
        }

        # ---------------------------------------------------------------- #
        # 7. Execute RAG workflow                                           #
        # ---------------------------------------------------------------- #
        result = rag_graph.invoke(initial_state)
        answer = result.get("answer", "Error generating response")
        top_docs = result.get("top_docs", reranked_docs)

        # ---------------------------------------------------------------- #
        # 8. Log interaction for evaluation                                 #
        # ---------------------------------------------------------------- #
        log_interaction(
            session_id=request.session_id,
            query=request.question,
            generated_answer=answer,
            context_chunks=[doc.page_content for doc in top_docs],
            retrieved_ids=[
                f"{doc.metadata.get('source', 'unknown').split('/')[-1]}"
                f"__p{doc.metadata.get('page', i)}"
                for i, doc in enumerate(top_docs)
            ],
            user_id=DEFAULT_USER_ID,
        )

        # ---------------------------------------------------------------- #
        # 9. Update learning memory                                         #
        # ---------------------------------------------------------------- #
        if request.page_number:
            memory = LearningMemory(user_id=DEFAULT_USER_ID)
            memory.update_explanation(
                document_id=request.document_id,
                page_number=request.page_number
            )

        logger.info(
            "Generated answer | mode=%s | suggestion=%s | page=%s | "
            "style_hint=%s | docs=%d",
            request.mode, suggested_mode, request.page_number,
            bool(style_hint), len(top_docs),
        )

        return ChatResponse(
            success=True,
            answer=answer,
            mode=request.mode,
            error=None,
            suggested_mode=suggested_mode,
            suggestion_reason=suggestion_reason,
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