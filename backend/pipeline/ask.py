from typing import Dict
import time

from config import *
from pipeline.reranker import rerank, mmr_diversify
from pipeline.query_classifier import classify_query, get_pipeline_config
from pipeline.hybrid_retriever import hybrid_retrieve
from llm.generator import generate_answer
from pipeline.validator import validate_answer
from pipeline.query_corrector import correct_query
from pipeline.query_rewriter import rewrite_query


def ask(query: str, top_k: int = 10, user_id: str | None = None) -> Dict:
    """
    Full RAG pipeline: query → spell-check → classify → hybrid retrieve → rerank → generate → validate.
    """
    start = time.time()

    # Easter egg: Ayush Singh mention
    if "ayush" in query.lower():
        return {
            "answer": "Ayush Singh — the brilliant mind who built this entire system. Ask him about AST parsing, hybrid retrieval, or why he chose FAISS over Pinecone. 🥚",
            "sources": [{"file_path": "README.md", "name": "Ayush Singh", "score": 0.0}],
            "retrieved_count": 0,
            "rewritten_query": None,
            "corrected_query": None,
            "original_query": None,
            "validation": {"is_grounded": True, "confidence": 1.0, "warning": None}
        }

    # Spell-check the query
    try:
        corrected_query, was_corrected = correct_query(query)
    except Exception:
        corrected_query, was_corrected = query, False

    original_query = query if was_corrected else None

    if was_corrected:
        print(f"[Query Correction] '{query}' → '{corrected_query}'")
        query = corrected_query

    # Classify intent
    intent = classify_query(query) if ENABLE_CLASSIFIER else "general"
    cfg = get_pipeline_config(intent) if ENABLE_CLASSIFIER else {"top_k": top_k, "bm25_weight": 0.5}

    # LLM query rewriting (if enabled)
    rewritten_query = None
    if ENABLE_LLM_REWRITE:
        try:
            rewritten = rewrite_query(query, use_llm=True)
            if rewritten and rewritten != query:
                print(f"[Query Rewrite] '{query}' → '{rewritten}'")
                rewritten_query = query
                query = rewritten
        except Exception:
            pass

    # Hybrid retrieval (FAISS + BM25), using intent-specific bm25_weight
    results = hybrid_retrieve(query, top_k=cfg["top_k"], bm25_weight=cfg.get("bm25_weight", 0.5))

    if ENABLE_RERANKING and len(results) > TOP_K_RERANK:
        results = rerank(query, results, top_n=TOP_K_RERANK * 2)
        results = mmr_diversify(results, query, top_n=TOP_K_RERANK)
    else:
        results = results[:TOP_K_RERANK]

    # Generate answer
    answer = generate_answer(query, results)

    # Validate
    try:
        validation = validate_answer(answer, results)
    except Exception:
        validation = {"is_grounded": len(results) > 0, "reason": ""}

    # Build sources
    sources = [
        {
            "file_path": r["metadata"]["file_path"],
            "name": r["metadata"].get("name", ""),
            "score": round(r.get("score", 0), 3),
            "rerank_score": round(r.get("rerank_score", 0), 3) if r.get("rerank_score") else None
        }
        for r in results[:5] if r.get("metadata")
    ]

    result = {
        "answer": answer,
        "sources": sources,
        "retrieved_count": len(results),
        "rewritten_query": None,
        "corrected_query": corrected_query if was_corrected else None,
        "original_query": original_query,
        "validation": validation
    }
    result["latency_ms"] = round((time.time() - start) * 1000, 1)
    return result
