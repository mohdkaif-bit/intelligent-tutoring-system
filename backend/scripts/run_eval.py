"""
Full End-to-End RAG Evaluation Script
--------------------------------------
Assumes the PDF is already uploaded and indexed in FAISS + BM25.

Dataset format expected (your eval_dataset.json):
  {
    "question": "...",
    "ground_truth_answer": "...",
    "supporting_facts": ["fact1", "fact2"],
    "relevant_chunk_ids": ["5f687f61-9f7c-493c-b0bd-ff4914b65e7a"],
    "difficulty": "easy|medium|hard",
    "type": "single-hop|multi-hop"
  }

All metrics computed:
  RETRIEVAL  : Precision@K, Recall@K, MRR, Hit Rate@K
  GENERATION : Exact Match, Token F1, Semantic Similarity,
               Faithfulness, Context Utilization, Chunk Relevance,
               Answer Completeness

Usage
-----
    python scripts/run_eval.py \
        --document-id  Document1.pdf_573e60ce0399 \
        --dataset      scripts/eval_dataset.json \
        --mode         explain_concept \
        --output       scripts/eval_report.json \
        --llm-judge \
        --k 6
"""

from __future__ import annotations

import argparse
import json
import pickle
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.logging import get_logger
from app.services.rag.retriever.vector_retriever import VectorRetriever
from app.services.memory.adaptation.context_ranker import ContextRanker
from app.services.rag.graph.rag_graph import RAGGraph, RETRIEVAL_CONFIGS, DEFAULT_CONFIG
from app.services.rag.graph.nodes import RETRIEVAL_CONFIGS, DEFAULT_CONFIG
from app.services.rag.metrics import RAGEvaluator
from app.storage.documents import DocumentStorage

logger = get_logger(__name__)

# ── Fingerprint → UUID map (populated once from pkl) ─────────────────────────
_chunk_id_map: dict[str, str] = {}


# ── Doc ID builder ────────────────────────────────────────────────────────────

def make_doc_id(doc) -> str:
    """
    Look up UUID from text fingerprint map.
    Uses first 80 chars of chunk text as fingerprint key.
    Falls back to filename__page if UUID not found.
    """
    fingerprint = doc.page_content[:80].strip()
    if fingerprint in _chunk_id_map:
        return _chunk_id_map[fingerprint]

    filename = (
        str(doc.metadata.get("source", "unknown"))
        .replace("\\", "/")
        .split("/")[-1]
    )
    page = doc.metadata.get("page", 0)
    return f"{filename}__p{page}"


# ── Retrieval metrics ─────────────────────────────────────────────────────────

def calculate_retrieval_metrics(
    relevant_ids: list[str],
    retrieved_ids: list[str],
    k: int = 5,
) -> dict:
    relevant  = set(relevant_ids)
    retrieved = set(retrieved_ids[:k])
    hits      = relevant & retrieved

    precision = len(hits) / len(retrieved) if retrieved else 0.0
    recall    = len(hits) / len(relevant)  if relevant  else 0.0
    hit_rate  = 1.0 if hits else 0.0

    mrr = 0.0
    for rank, doc_id in enumerate(retrieved_ids[:k], 1):
        if doc_id in relevant:
            mrr = 1.0 / rank
            break

    return {
        "precision_at_k": round(precision, 4),
        "recall_at_k":    round(recall, 4),
        "hit_rate":       hit_rate,
        "mrr":            round(mrr, 4),
        "hits":           len(hits),
        "total_relevant": len(relevant),
    }


# ── Answer generator ──────────────────────────────────────────────────────────

def generate_answer(
    question:    str,
    vr:          VectorRetriever,
    document_id: str,
    user_id:     str,
    mode:        str,
    rag_graph:   RAGGraph,
    k:           int,           # ← ADDED: use args.k for retrieval
) -> tuple[str, list]:
    """
    Run one question through the full RAG pipeline.

    Changes from original:
      - Accepts k explicitly so --k CLI arg controls actual retrieval depth
      - Accepts vr (VectorRetriever) instead of retriever so we can call
        build_mode_ensemble() with the correct mode config — same as routes.py
      - RAGGraph instance passed in (singleton) instead of created per question
      - Retrieval logging reads from already-fetched result, no extra calls
      - _retrieval_cap injected into state so rerank_node uses correct floor+cap
      - sleep removed from here — caller controls pacing
    """
    mode_cfg  = RETRIEVAL_CONFIGS.get(mode, DEFAULT_CONFIG)

    # ── Build mode-tuned retriever (cached after first call per doc+mode) ──
    retriever = vr.build_mode_ensemble(
        mode        = mode,
        k           = k,                # ← FIXED: was mode_cfg.k (hardcoded), now args.k
        bm25_w      = mode_cfg.bm25_w,
        document_id = document_id,
    )

    # ── Single retrieval call ──────────────────────────────────────────────
    raw_docs = list(retriever.invoke(question))

    # Log from result — no extra BM25/FAISS calls
    if hasattr(retriever, "retrievers") and len(retriever.retrievers) == 2:
        logger.info(
            "  Retrieval mode=%s  k=%d  bm25=%.2f  faiss=%.2f  rrf_total=%d",
            mode,
            k,
            retriever.weights[0],
            retriever.weights[1],
            len(raw_docs),
        )

    # ── ContextRanker (Adaptation C) ──────────────────────────────────────
    ranker   = ContextRanker(user_id=user_id)
    try:
        reranked = ranker.rerank(docs=raw_docs, document_id=document_id)
    except Exception as exc:
        logger.warning("  ContextRanker failed (%s), using raw_docs", exc)
        reranked = raw_docs

    top_docs_for_state = reranked[: mode_cfg.cap]

    # ── RAG graph state ────────────────────────────────────────────────────
    state = {
        "question":          question,
        "mode":              mode,
        "style_hint":        "",
        "retriever":         retriever,
        "_retrieval_cap":    mode_cfg.cap,   # ← rerank_node uses floor+cap
        "docs":              reranked,        # ← summarize_chunks uses this
        "top_docs":          top_docs_for_state,
        "answer":            "",
        "history":           [],
        "difficulty_level":  "intermediate",
        "show_steps":        True,
        "generate_practice": mode == "generate_practice",
        "page_number":       None,
        "selected_text":     None,
    }

    result   = rag_graph.invoke(state)
    answer   = result.get("answer", "")
    top_docs = result.get("top_docs", top_docs_for_state)

    return answer, top_docs


# ── Main evaluation loop ──────────────────────────────────────────────────────

def run_evaluation(args: argparse.Namespace) -> None:

    # ── Load dataset ───────────────────────────────────────────────────────
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        logger.error("Dataset not found: %s", dataset_path)
        sys.exit(1)

    with open(dataset_path, encoding="utf-8") as f:
        dataset = json.load(f)

    logger.info("Loaded %d evaluation questions", len(dataset))

    has_chunk_ids = all("relevant_chunk_ids" in item for item in dataset)
    if has_chunk_ids:
        logger.info("relevant_chunk_ids found — using real retrieval metrics")
    else:
        logger.warning(
            "relevant_chunk_ids NOT found — retrieval metrics will be unreliable"
        )

    # ── Validate document ──────────────────────────────────────────────────
    doc_storage = DocumentStorage(user_id=args.user_id)
    doc_path    = doc_storage.get_document_path(args.document_id)

    if not doc_path:
        logger.error(
            "Document '%s' not found. Upload it via the API first.", args.document_id
        )
        sys.exit(1)

    logger.info("Document found: %s", doc_path)

    # ── Load hybrid retriever ──────────────────────────────────────────────
    logger.info("Loading hybrid retriever (FAISS + BM25) from cache...")
    vr = VectorRetriever(user_id=args.user_id)

    if not vr.has_full_cache(args.document_id):
        logger.error(
            "No hybrid cache found for '%s'. Re-upload to regenerate.", args.document_id
        )
        sys.exit(1)

    vr.load_or_create_vectorstore(
        document_id=args.document_id,
        pdf_path=doc_path,
    )
    embeddings = vr.get_embeddings_model()
    logger.info("Hybrid retriever loaded successfully")

    # ── Build fingerprint → UUID map ───────────────────────────────────────
    try:
        pkl_path = (
            settings.VECTOR_STORAGE_DIR
            / args.user_id
            / args.document_id
            / "faiss"
            / "index.pkl"
        )
        with open(pkl_path, "rb") as f:
            docstore_data = pickle.load(f)

        docstore, _ = docstore_data
        for uuid, doc in docstore._dict.items():
            fingerprint = doc.page_content[:80].strip()
            _chunk_id_map[fingerprint] = uuid

        logger.info(
            "Built chunk_id_map with %d entries", len(_chunk_id_map)
        )
    except Exception as exc:
        logger.warning(
            "Could not build chunk_id_map (%s) — falling back to page-based IDs", exc
        )

    # ── LLM judge (optional) ───────────────────────────────────────────────
    groq_client = None
    if args.llm_judge:
        from app.services.llm.groq_client import get_llm_client
        groq_client = get_llm_client()
        logger.info("LLM-as-judge enabled")

    # ── Singletons ─────────────────────────────────────────────────────────
    # RAGGraph created once — cross-encoder inside RAGNodes loads once too
    rag_graph = RAGGraph()
    evaluator = RAGEvaluator(
        retrieval_k=args.k,
        embeddings=embeddings,
        groq_client=groq_client,
    )

    # ── Per-question loop ──────────────────────────────────────────────────
    eval_dataset = []
    total        = len(dataset)

    for i, item in enumerate(dataset, 1):
        question         = item["question"]
        ground_truth     = item["ground_truth_answer"]
        supporting_facts = item.get("supporting_facts", [])
        difficulty       = item.get("difficulty", "unknown")
        q_type           = item.get("type", "unknown")
        relevant_ids     = item.get("relevant_chunk_ids", [])

        logger.info(
            "[%d/%d] %s | difficulty=%s | type=%s | relevant_chunks=%d",
            i, total, question[:65], difficulty, q_type, len(relevant_ids),
        )

        t0 = time.time()
        try:
            generated_answer, top_docs = generate_answer(
                question    = question,
                vr          = vr,
                document_id = args.document_id,
                user_id     = args.user_id,
                mode        = args.mode,
                rag_graph   = rag_graph,
                k           = args.k,       # ← ADDED: pass CLI k to retriever
            )
        except Exception as exc:
            logger.error("  Failed to generate answer: %s", exc)
            generated_answer = ""
            top_docs         = []

        elapsed = time.time() - t0

        retrieved_ids = [make_doc_id(d) for d in top_docs]

        logger.info("  retrieved_ids : %s", retrieved_ids)
        logger.info("  relevant_ids  : %s", relevant_ids)

        retrieval_metrics = calculate_retrieval_metrics(
            relevant_ids  = relevant_ids,
            retrieved_ids = retrieved_ids,
            k             = args.k,
        )

        logger.info(
            "  Done in %.1fs | answer_len=%d | retrieved=%d | "
            "hits=%d / relevant=%d | precision=%.3f | recall=%.3f | mrr=%.3f",
            elapsed,
            len(generated_answer),
            len(retrieved_ids),
            retrieval_metrics["hits"],
            retrieval_metrics["total_relevant"],
            retrieval_metrics["precision_at_k"],
            retrieval_metrics["recall_at_k"],
            retrieval_metrics["mrr"],
        )

        eval_dataset.append({
            "query":              question,
            "generated_answer":   generated_answer,
            "expected_answer":    ground_truth,
            "context_chunks":     [d.page_content for d in top_docs],
            "retrieved_ids":      retrieved_ids,
            "relevant_ids":       relevant_ids,
            "_retrieval_metrics": retrieval_metrics,
            "_difficulty":        difficulty,
            "_type":              q_type,
            "_latency_s":         round(elapsed, 2),
            "_supporting_facts":  supporting_facts,
        })

        # ── Rate limit pacing ──────────────────────────────────────────
        # Only sleep if llm_judge is on — cross-encoder uses zero tokens
        # so generation is the only API call now. Shorter sleep is fine.
        if i < total and args.llm_judge:
            time.sleep(1.5)

    # ── Compute generation metrics ─────────────────────────────────────────
    logger.info("Computing all RAG metrics across %d queries...", total)
    report = evaluator.run(eval_dataset)

    # ── Override retrieval metrics with real pre-labeled ones ──────────────
    real_precision, real_recall, real_mrr, real_hit_rate = [], [], [], []

    for pq, item in zip(report["per_query"], eval_dataset):
        rm = item["_retrieval_metrics"]

        pq["precision_at_k"]   = rm["precision_at_k"]
        pq["recall_at_k"]      = rm["recall_at_k"]
        pq["reciprocal_rank"]  = rm["mrr"]
        pq["hit_rate"]         = rm["hit_rate"]
        pq["difficulty"]       = item["_difficulty"]
        pq["type"]             = item["_type"]
        pq["latency_s"]        = item["_latency_s"]
        pq["generated_answer"] = item["generated_answer"]
        pq["expected_answer"]  = item["expected_answer"]
        pq["supporting_facts"] = item["_supporting_facts"]
        pq["relevant_matched"] = rm["hits"]
        pq["retrieved_count"]  = len(item["retrieved_ids"])
        pq["total_relevant"]   = rm["total_relevant"]

        real_precision.append(rm["precision_at_k"])
        real_recall.append(rm["recall_at_k"])
        real_mrr.append(rm["mrr"])
        real_hit_rate.append(rm["hit_rate"])

    report["retrieval"]["precision_at_k"] = round(sum(real_precision) / len(real_precision), 4)
    report["retrieval"]["recall_at_k"]    = round(sum(real_recall)    / len(real_recall),    4)
    report["retrieval"]["mrr"]            = round(sum(real_mrr)       / len(real_mrr),       4)
    report["retrieval"]["hit_rate"]       = round(sum(real_hit_rate)  / len(real_hit_rate),  4)

    # ── Breakdowns ─────────────────────────────────────────────────────────
    report["by_difficulty"] = _breakdown(report["per_query"], "difficulty")
    report["by_type"]       = _breakdown(report["per_query"], "type")

    # ── Save ───────────────────────────────────────────────────────────────
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info("Report saved to %s", output_path)

    evaluator.print_report(report)
    _print_breakdown(report)
    _print_per_query(report["per_query"])


# ── Breakdown helpers ─────────────────────────────────────────────────────────

def _breakdown(per_query: list[dict], key: str) -> dict:
    groups: dict[str, list] = {}
    for pq in per_query:
        groups.setdefault(pq.get(key, "unknown"), []).append(pq)

    result = {}
    for group, items in groups.items():
        def avg(metric: str, _items=items) -> float | None:
            vals = [item[metric] for item in _items if item.get(metric) is not None]
            return round(sum(vals) / len(vals), 4) if vals else None

        result[group] = {
            "n":                        len(items),
            "mean_precision_at_k":      avg("precision_at_k"),
            "mean_recall_at_k":         avg("recall_at_k"),
            "mean_mrr":                 avg("reciprocal_rank"),
            "mean_hit_rate":            avg("hit_rate"),
            "mean_f1":                  avg("f1_score"),
            "mean_semantic_similarity": avg("semantic_similarity"),
            "mean_faithfulness":        avg("faithfulness"),
            "mean_chunk_relevance":     avg("chunk_relevance"),
            "mean_answer_completeness": avg("answer_completeness"),
            "mean_context_utilization": avg("context_utilization"),
            "mean_latency_s":           avg("latency_s"),
        }
    return result


def _print_breakdown(report: dict) -> None:
    def _row(label: str, val) -> None:
        display = f"{val:.4f}" if isinstance(val, float) else str(val)
        print(f"    {label:<30}: {display}")

    for section_key, title in [
        ("by_difficulty", "BREAKDOWN BY DIFFICULTY"),
        ("by_type",       "BREAKDOWN BY QUESTION TYPE"),
    ]:
        print("\n" + "=" * 62)
        print(f"  {title}")
        print("=" * 62)
        for group, s in report.get(section_key, {}).items():
            print(f"\n  [{group.upper()}]  n={s['n']}")
            print("  --- Retrieval ---")
            _row("Precision@K",         s["mean_precision_at_k"])
            _row("Recall@K",            s["mean_recall_at_k"])
            _row("MRR",                 s["mean_mrr"])
            _row("Hit Rate@K",          s["mean_hit_rate"])
            print("  --- Generation ---")
            _row("Token F1",            s["mean_f1"])
            _row("Semantic Similarity", s["mean_semantic_similarity"])
            _row("Faithfulness",        s["mean_faithfulness"])
            _row("Chunk Relevance",     s["mean_chunk_relevance"])
            _row("Answer Completeness", s["mean_answer_completeness"])
            _row("Context Utilization", s["mean_context_utilization"])
            _row("Avg Latency (s)",     s["mean_latency_s"])
    print()


def _print_per_query(per_query: list[dict]) -> None:
    print("\n" + "=" * 62)
    print("  PER-QUESTION SUMMARY")
    print("=" * 62)
    for i, pq in enumerate(per_query, 1):
        print(f"\n  [{i}] {pq['query'][:70]}")
        print(f"       difficulty={pq.get('difficulty')} | type={pq.get('type')}")
        print(f"       hits={pq.get('relevant_matched')} / total_relevant={pq.get('total_relevant')} / retrieved={pq.get('retrieved_count')}")
        print(f"       precision@K={pq.get('precision_at_k', 0):.3f} | recall@K={pq.get('recall_at_k', 0):.3f} | MRR={pq.get('reciprocal_rank', 0):.3f} | hit_rate={pq.get('hit_rate', 0):.3f}")
        print(f"       F1={pq.get('f1_score', 0):.3f} | sem_sim={pq.get('semantic_similarity', 0):.3f} | faithfulness={pq.get('faithfulness', 0):.3f}")
        print(f"       chunk_relevance={pq.get('chunk_relevance', 0):.3f} | completeness={pq.get('answer_completeness', 0):.3f}")
        print(f"       latency={pq.get('latency_s')}s")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="End-to-end RAG evaluation"
    )
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--dataset",     required=True)
    parser.add_argument("--mode",        default="quick_answer",
        choices=["quick_answer", "explain_concept", "step_by_step",
                 "generate_practice", "deep_analysis"])
    parser.add_argument("--user-id",     default="default_user")
    parser.add_argument("--k",           type=int, default=5)
    parser.add_argument("--llm-judge",   action="store_true")
    parser.add_argument("--output",
        default=f"eval_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    logger.info("=" * 62)
    logger.info("RAG FULL EVALUATION")
    logger.info("  document_id : %s", args.document_id)
    logger.info("  dataset     : %s", args.dataset)
    logger.info("  mode        : %s", args.mode)
    logger.info("  k           : %d", args.k)
    logger.info("  llm_judge   : %s", args.llm_judge)
    logger.info("  output      : %s", args.output)
    logger.info("=" * 62)

    run_evaluation(args)