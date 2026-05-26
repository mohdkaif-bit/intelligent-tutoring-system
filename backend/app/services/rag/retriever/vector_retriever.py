"""
Vector Retriever - Hybrid BM25 + FAISS retrieval with caching.
Exposes vectorstore and bm25_retriever as attributes so RAGGraph /
RAGNodes can build mode-tuned EnsembleRetrievers without re-loading.
"""
import os
import copy
import shutil
import pickle
from pathlib import Path
from typing import Optional, Tuple, List

from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.retrievers import BM25Retriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.documents import Document

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class VectorRetriever:
    """
    Manages FAISS + BM25 hybrid retrieval.

    After load_or_create_vectorstore() is called:
      self.vectorstore     → FAISS instance (for building mode-tuned retrievers)
      self.bm25_retriever  → BM25Retriever instance (shallow-copied per mode)

    The default EnsembleRetriever returned by load_or_create_vectorstore uses
    settings.VECTOR_SEARCH_K and the instance-level weights. Mode-specific
    k / weights are applied externally by RAGGraph._build_retriever or
    RAGNodes._build_mode_retriever.
    """

    def __init__(self, user_id: str = "default_user"):
        os.environ["TRANSFORMERS_NO_TF"] = "1"

        self.user_id = user_id

        # Public sub-retriever references — populated after load/create
        self.vectorstore: Optional[FAISS] = None
        self.bm25_retriever: Optional[BM25Retriever] = None

        # Ensemble cache — avoids rebuilding per request for same doc+mode
        self._ensemble_cache: dict[tuple, EnsembleRetriever] = {}

        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": settings.EMBEDDING_DEVICE},
        )

        # Default ensemble weights (overridden per-mode by RAGGraph/RAGNodes)
        self.bm25_weight = 0.2
        self.faiss_weight = 0.8

        logger.info("VectorRetriever init — model: %s", settings.EMBEDDING_MODEL)
        logger.info("Default weights — BM25: %.2f  FAISS: %.2f",
                    self.bm25_weight, self.faiss_weight)

    # ── cache path helpers ────────────────────────────────────────────────────

    def _faiss_path(self, document_id: str) -> Path:
        return settings.VECTOR_STORAGE_DIR / self.user_id / document_id / "faiss"

    def _bm25_path(self, document_id: str) -> Path:
        return settings.VECTOR_STORAGE_DIR / self.user_id / document_id / "bm25.pkl"

    def has_faiss_cache(self, document_id: str) -> bool:
        return self._faiss_path(document_id).exists()

    def has_bm25_cache(self, document_id: str) -> bool:
        return self._bm25_path(document_id).exists()

    def has_full_cache(self, document_id: str) -> bool:
        return self.has_faiss_cache(document_id) and self.has_bm25_cache(document_id)

    # ── public entry point ────────────────────────────────────────────────────

    def load_or_create_vectorstore(
        self,
        document_id: str,
        pdf_path: str,
        force_recreate: bool = False,
    ) -> Tuple[FAISS, EnsembleRetriever]:
        """
        Load hybrid retriever from cache or create from PDF.

        Side-effects:
          Sets self.vectorstore and self.bm25_retriever so the instance can
          be passed into RAGGraph.invoke(vector_retriever=self) for
          mode-tuned retrieval without re-loading indexes.

        Returns:
            (faiss_vectorstore, default_ensemble_retriever)
        """
        if self.has_full_cache(document_id) and not force_recreate:
            logger.info("Loading hybrid cache for document: %s", document_id)
            try:
                vectorstore, bm25_retriever = self._load_cache(document_id)
                self.vectorstore    = vectorstore
                self.bm25_retriever = bm25_retriever
                ensemble = self._build_ensemble(vectorstore, bm25_retriever)
                logger.info("Hybrid cache loaded successfully")
                return vectorstore, ensemble
            except Exception as exc:
                logger.warning("Cache load failed (%s) — recreating index", exc)

        logger.info("Creating hybrid index for document: %s", document_id)
        return self._create_vectorstore(document_id, pdf_path)

    # ── cache load ────────────────────────────────────────────────────────────

    def _load_cache(self, document_id: str) -> Tuple[FAISS, BM25Retriever]:
        """Load FAISS and BM25 from disk. Raises on any error."""
        vectorstore = FAISS.load_local(
            str(self._faiss_path(document_id)),
            self.embeddings,
            allow_dangerous_deserialization=True,
        )
        with open(self._bm25_path(document_id), "rb") as f:
            bm25_retriever = pickle.load(f)
        return vectorstore, bm25_retriever

    # ── index creation ────────────────────────────────────────────────────────

    def _create_vectorstore(
        self,
        document_id: str,
        pdf_path: str,
    ) -> Tuple[FAISS, EnsembleRetriever]:
        """
        Build FAISS + BM25 indexes from a PDF, persist both, and expose
        sub-retrievers as instance attributes.
        """
        try:
            # Load PDF
            logger.info("Loading PDF: %s", pdf_path)
            loader = PyMuPDFLoader(pdf_path)
            pages = loader.load()
            if not pages:
                raise ValueError("No pages loaded from PDF")
            logger.info("Loaded %d pages", len(pages))

            # Chunk
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )
            chunks: List[Document] = splitter.split_documents(pages)
            logger.info("Created %d chunks", len(chunks))

            # FAISS
            logger.info("Building FAISS index...")
            vectorstore = FAISS.from_documents(chunks, self.embeddings)
            faiss_path = self._faiss_path(document_id)
            faiss_path.parent.mkdir(parents=True, exist_ok=True)
            vectorstore.save_local(str(faiss_path))
            logger.info("FAISS index saved → %s", faiss_path)

            # BM25
            logger.info("Building BM25 index...")
            bm25_retriever = BM25Retriever.from_documents(chunks)
            bm25_retriever.k = settings.VECTOR_SEARCH_K
            bm25_path = self._bm25_path(document_id)
            with open(bm25_path, "wb") as f:
                pickle.dump(bm25_retriever, f)
            logger.info("BM25 index saved → %s", bm25_path)

            # Expose for mode-tuned retrieval
            self.vectorstore    = vectorstore
            self.bm25_retriever = bm25_retriever

            ensemble = self._build_ensemble(vectorstore, bm25_retriever)
            return vectorstore, ensemble

        except Exception as exc:
            logger.error("Error creating hybrid index: %s", exc)
            raise

    # ── ensemble builder ──────────────────────────────────────────────────────

    def _build_ensemble(
        self,
        vectorstore: FAISS,
        bm25_retriever: BM25Retriever,
        k: Optional[int] = None,
        bm25_w: Optional[float] = None,
    ) -> EnsembleRetriever:
        """
        Combine FAISS and BM25 into an EnsembleRetriever (RRF merge).

        Args:
            vectorstore    : FAISS store to wrap as a retriever
            bm25_retriever : BM25Retriever (shallow-copied — never mutated)
            k              : docs fetched per sub-retriever; defaults to
                             settings.VECTOR_SEARCH_K
            bm25_w         : BM25 weight; defaults to self.bm25_weight

        Returns:
            EnsembleRetriever ready for .invoke()
        """
        _k       = k      if k      is not None else settings.VECTOR_SEARCH_K
        _bm25_w  = bm25_w if bm25_w is not None else self.bm25_weight
        _faiss_w = round(1.0 - _bm25_w, 2)

        faiss_ret = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": _k},
        )

        # Shallow-copy so we never mutate the cached instance
        bm25_copy   = copy.copy(bm25_retriever)
        bm25_copy.k = _k

        ensemble = EnsembleRetriever(
            retrievers=[bm25_copy, faiss_ret],
            weights=[_bm25_w, _faiss_w],
        )
        logger.info(
            "_build_ensemble: k=%d  BM25=%.2f  FAISS=%.2f", _k, _bm25_w, _faiss_w,
        )
        return ensemble

    # ── public mode-tuned ensemble ────────────────────────────────────────────

    def build_mode_ensemble(
        self,
        mode: str,
        k: int,
        bm25_w: float,
        document_id: str = "",    # ← added for cache keying
    ) -> EnsembleRetriever:
        """
        Return a mode-tuned EnsembleRetriever, cached by (document_id, mode).

        Requires load_or_create_vectorstore() to have been called first so
        self.vectorstore and self.bm25_retriever are populated.

        Args:
            mode        : RAG mode string (used as cache key)
            k           : docs fetched per sub-retriever
            bm25_w      : BM25 ensemble weight
            document_id : document being queried (used as cache key)

        Returns:
            EnsembleRetriever ready for .invoke()
        """
        if self.vectorstore is None or self.bm25_retriever is None:
            raise RuntimeError(
                "build_mode_ensemble called before load_or_create_vectorstore"
            )

        cache_key = (document_id, mode)
        if cache_key in self._ensemble_cache:
            logger.info(
                "build_mode_ensemble: cache hit  doc=%s mode=%s", document_id, mode
            )
            return self._ensemble_cache[cache_key]

        ensemble = self._build_ensemble(
            self.vectorstore, self.bm25_retriever, k=k, bm25_w=bm25_w
        )

        if document_id:
            self._ensemble_cache[cache_key] = ensemble

        logger.info(
            "build_mode_ensemble: built and cached  doc=%s mode=%s k=%d bm25=%.2f",
            document_id, mode, k, bm25_w,
        )
        return ensemble

    # ── deletion ──────────────────────────────────────────────────────────────

    def delete_vectorstore(self, document_id: str) -> bool:
        """
        Delete FAISS and BM25 caches for a document.
        Clears instance attributes and ensemble cache entries for this doc.
        """
        doc_dir = settings.VECTOR_STORAGE_DIR / self.user_id / document_id
        if not doc_dir.exists():
            logger.warning("delete_vectorstore: no cache found for %s", document_id)
            return False
        try:
            shutil.rmtree(doc_dir)
            self.vectorstore    = None
            self.bm25_retriever = None
            # Clear ensemble cache entries for this document
            stale = [k for k in self._ensemble_cache if k[0] == document_id]
            for k in stale:
                del self._ensemble_cache[k]
            logger.info("Deleted hybrid cache for %s", document_id)
            return True
        except Exception as exc:
            logger.error("delete_vectorstore error: %s", exc)
            return False

    # ── misc ──────────────────────────────────────────────────────────────────

    def get_embeddings_model(self) -> HuggingFaceEmbeddings:
        return self.embeddings