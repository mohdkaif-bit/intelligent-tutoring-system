"""
Chat API Routes
Handles question answering using RAG system.
"""
import re
from fastapi import APIRouter, HTTPException, status

from app.models.chat.schemas import ChatRequest, ChatResponse
from app.storage.documents import DocumentStorage
from app.services.rag.graph.rag_graph import RAGGraph, RETRIEVAL_CONFIGS, DEFAULT_CONFIG
from app.services.rag.retriever.vector_retriever import VectorRetriever
from app.storage.user_memory import LearningMemory
from app.services.memory.adaptation import StyleAdapter, ContextRanker
from app.services.rag.eval_logger import log_interaction
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

DEFAULT_USER_ID = "default_user"

# ── mode alias normalisation ──────────────────────────────────────────────────
# Maps any client-sent mode string → canonical backend mode.
# Add new aliases here; nothing else in the file needs to change.
MODE_ALIASES: dict[str, str] = {
    "practice_problems": "generate_practice",
}

# ── singletons ────────────────────────────────────────────────────────────────
_rag_graph        = RAGGraph()
_vector_retriever = VectorRetriever(user_id=DEFAULT_USER_ID)


# ── helpers ───────────────────────────────────────────────────────────────────

def _clean_tokens(text: str) -> list[str]:
    """Strip punctuation and lowercase for BM25 token logging."""
    return [t for t in re.sub(r"[^\w\s]", "", text.lower()).split() if t]


def _log_hybrid_details(
    retriever,
    question: str,
    raw_docs: list,
    mode: str,
    k: int,
) -> None:
    """
    Log retrieval details from the ALREADY-FETCHED raw_docs.
    No extra retriever calls — counts come from the result we already have.
    Sub-retriever doc counts are estimated from the ensemble's retrievers
    only if needed for debugging, and only by checking .k not re-invoking.
    """
    logger.info("Retrieval mode=%s  k_per_retriever=%d", mode, k)
    logger.info("Hybrid RRF result: %d docs", len(raw_docs))
    logger.info("BM25 query tokens (cleaned): %s", _clean_tokens(question))

    if hasattr(retriever, "retrievers") and len(retriever.retrievers) == 2:
        bm25_ret  = retriever.retrievers[0]
        faiss_ret = retriever.retrievers[1]
        logger.info(
            "Ensemble weights — BM25: %.2f  FAISS: %.2f",
            retriever.weights[0], retriever.weights[1],
        )
        logger.info(
            "Sub-retriever k — BM25: %d  FAISS: %s",
            bm25_ret.k,
            faiss_ret.search_kwargs.get("k", "?"),
        )


@router.post("/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest):
    """
    Ask a question about course materials using RAG.
    Single retrieval pass, mode-aware from the start.
    """
    try:
        # ── 0. Normalise mode aliases ─────────────────────────────────────
        canonical_mode = MODE_ALIASES.get(request.mode, request.mode)
        if canonical_mode != request.mode:
            logger.info(
                "Mode alias resolved: %s → %s",
                request.mode, canonical_mode,
            )
        request = request.model_copy(update={"mode": canonical_mode})

        # ── 1. Resolve document path ──────────────────────────────────────
        doc_storage = DocumentStorage(user_id=DEFAULT_USER_ID)
        doc_path    = doc_storage.get_document_path(request.document_id)

        if not doc_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {request.document_id} not found",
            )

        # ── 2. Load indexes (cache hit after first request) ───────────────
        _vector_retriever.load_or_create_vectorstore(
            document_id=request.document_id,
            pdf_path=doc_path,
        )

        # ── 3. Build ONE mode-tuned retriever for this request ────────────
        #       This is the ONLY place retrieval config is applied.
        #       nodes.py fast-path will use these results directly.
        mode_cfg  = RETRIEVAL_CONFIGS.get(request.mode, DEFAULT_CONFIG)
        retriever = _vector_retriever.build_mode_ensemble(
            mode   = request.mode,
            k      = mode_cfg.k,
            bm25_w = mode_cfg.bm25_w,
        )

        # ── 4. Single retrieval call ──────────────────────────────────────
        try:
            raw_docs = list(retriever.invoke(request.question))
        except Exception as exc:
            logger.error("Retrieval failed: %s", exc)
            raw_docs = []

        # Log from already-fetched result — zero extra calls
        _log_hybrid_details(retriever, request.question, raw_docs, request.mode, mode_cfg.k)

        # ── 5. Adaptations ────────────────────────────────────────────────
        style_adapter = StyleAdapter(user_id=DEFAULT_USER_ID)

        # B — mode suggestion (advisory only, never changes request.mode)
        suggested_mode, suggestion_reason = style_adapter.suggest_mode_with_reason(
            document_id   = request.document_id,
            page_number   = request.page_number,
            requested_mode= request.mode,
        )
        if suggested_mode:
            logger.info(
                "Adaptation B: suggesting %s (was %s) page=%s reason=%s",
                suggested_mode, request.mode, request.page_number, suggestion_reason,
            )

        # A — style hint
        style_hint = style_adapter.get_style_hint(
            document_id = request.document_id,
            page_number = request.page_number,
        )
        if style_hint:
            logger.info(
                "Adaptation A: style hint applied page=%s struggle=%s",
                request.page_number,
                style_adapter.get_adaptation_summary(
                    request.document_id, request.page_number
                ).get("struggle_level"),
            )

        # C — context rerank (operates on raw_docs, no new retrieval)
        context_ranker = ContextRanker(user_id=DEFAULT_USER_ID)
        try:
            reranked_docs = context_ranker.rerank(
                docs        = raw_docs,
                document_id = request.document_id,
            )
        except Exception as exc:
            logger.warning("Context reranking failed (%s), using raw docs.", exc)
            reranked_docs = raw_docs

        # Slice to mode cap — this is the ceiling, rerank_node may reduce
        # further if score floor cuts some docs
        top_docs_for_state = reranked_docs[: mode_cfg.cap]

        logger.info(
            "Adaptation C: %d raw → %d reranked → %d top_docs  mode=%s cap=%d",
            len(raw_docs), len(reranked_docs),
            len(top_docs_for_state), request.mode, mode_cfg.cap,
        )

        # ── 6. Build state ────────────────────────────────────────────────
        initial_state = {
            "question":          request.question,
            "mode":              request.mode,
            "style_hint":        style_hint,
            # retriever kept in state so retrieve_node fallback still works
            # if top_docs is somehow empty
            "retriever":         retriever,
            "_retrieval_cap":    mode_cfg.cap,
            # Both set so:
            #   retrieve_node  → fast-paths on top_docs (correct mode-k docs)
            #   summarize_node → uses docs (full reranked set for deep_analysis)
            "docs":              reranked_docs,
            "top_docs":          top_docs_for_state,
            "answer":            "",
            "history":           request.history,
            "difficulty_level":  "intermediate",
            "show_steps":        True,
            "generate_practice": request.mode == "generate_practice",
            "page_number":       request.page_number,
            "selected_text":     None,
        }

        # ── 7. Execute graph ──────────────────────────────────────────────
        result   = _rag_graph.invoke(initial_state)
        answer   = result.get("answer", "Error generating response")
        top_docs = result.get("top_docs", top_docs_for_state)

        # ── 8. Log interaction ────────────────────────────────────────────
        log_interaction(
            session_id       = request.session_id,
            query            = request.question,
            generated_answer = answer,
            context_chunks   = [doc.page_content for doc in top_docs],
            retrieved_ids    = [
                f"{doc.metadata.get('source', 'unknown').split('/')[-1]}"
                f"__p{doc.metadata.get('page', i)}"
                for i, doc in enumerate(top_docs)
            ],
            user_id=DEFAULT_USER_ID,
        )

        # ── 9. Update learning memory ─────────────────────────────────────
        if request.page_number:
            memory = LearningMemory(user_id=DEFAULT_USER_ID)
            memory.update_explanation(
                document_id = request.document_id,
                page_number = request.page_number,
            )

        logger.info(
            "Done | mode=%s | suggestion=%s | page=%s | style_hint=%s | docs=%d",
            request.mode, suggested_mode, request.page_number,
            bool(style_hint), len(top_docs),
        )

        return ChatResponse(
            success          = True,
            answer           = answer,
            mode             = request.mode,
            error            = None,
            suggested_mode   = suggested_mode,
            suggestion_reason= suggestion_reason,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error processing chat request: %s", exc)
        return ChatResponse(
            success=False,
            answer="",
            mode=request.mode,
            error=f"Failed to process question: {str(exc)}",
        )