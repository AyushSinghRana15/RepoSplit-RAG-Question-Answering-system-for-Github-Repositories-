from typing import Dict, List, Optional
import time
import logging

from config import *
from pipeline.reranker import rerank
from pipeline.query_classifier import classify_query, get_pipeline_config
from pipeline.hybrid_retriever import hybrid_retrieve
from llm.generator import generate_answer
from pipeline.validator import validate_answer, score_confidence
from pipeline.query_corrector import correct_query
from pipeline.reflector import reflect
from pipeline.query_rewriter import rewrite_query
from pipeline.language_detector import detect_language
from pipeline.entity_extractor import extract_entities
from pipeline.context_awareness import build_context_profile, enrich_query_with_context, add_to_history
from pipeline.synonym_expander import expand_synonyms
from pipeline.query_cleaner import clean_query
from pipeline.multi_query_expander import expand_queries
from pipeline.context_compressor import compress_results
from pipeline.context_expander import expand_context
from pipeline.response_personalizer import personalize_response
from pipeline.feedback_loop import record_feedback

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def build_context(results: List[dict]) -> str:
    parts = []
    for r in results:
        meta = r["metadata"]
        header = f"[{meta.get('file_path', 'unknown')}] {meta.get('chunk_type', 'unknown')}: {meta.get('name', 'unknown')}"
        content = r["content"][:PER_CHUNK_MAX_TOKENS]
        parts.append(f"--- {header} ---\n{content}")
    return "\n\n".join(parts)


def ask(
    query: str,
    top_k: int = 10,
    user_id: Optional[str] = None,
) -> Dict:
    """
    Full RAG pipeline: query → spell-check → classify → hybrid retrieve → rerank → generate → validate.
    """
    start = time.time()

    # ── Easter egg ────────────────────────────────────────────
    if "ayush" in query.lower():
        return {
            "answer": "Ayush Singh — the brilliant mind who built this entire system. Ask him about AST parsing, hybrid retrieval, or why he chose FAISS over Pinecone. 🥚",
            "sources": [{"file_path": "README.md", "name": "Ayush Singh", "score": 0.0}],
            "retrieved_count": 0,
            "rewritten_query": None,
            "corrected_query": None,
            "original_query": query,
            "entities": {},
            "language": {"natural_language": "en", "programming_language": None},
            "intent": "general",
            "validation": {"is_grounded": True, "confidence": 1.0, "warning": None},
            "latency_ms": 0,
        }

    original_query = query

    # ═══════════════════════════════════════════════════════════
    # STAGE 1: Language Detection
    # ═══════════════════════════════════════════════════════════
    pipeline_timings = {}
    t0 = time.time()
    lang_info = detect_language(query) if ENABLE_LANGUAGE_DETECTION else {"natural_language": "en", "programming_language": None}
    pipeline_timings["language_detection"] = round((time.time() - t0) * 1000, 1)

    # ═══════════════════════════════════════════════════════════
    # STAGE 2: Spell Correction
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    try:
        corrected_query, was_corrected = correct_query(query)
    except Exception:
        corrected_query, was_corrected = query, False
    if was_corrected:
        print(f"[Query Correction] '{query}' → '{corrected_query}'")
        query = corrected_query
    pipeline_timings["spell_correction"] = round((time.time() - t0) * 1000, 1)

    # ═══════════════════════════════════════════════════════════
    # STAGE 3: Intent Detection
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    intent = classify_query(query) if ENABLE_CLASSIFIER else "general"
    cfg = get_pipeline_config(intent) if ENABLE_CLASSIFIER else {"top_k": TOP_K_RETRIEVE, "bm25_weight": 0.5, "max_additions": CONTEXT_MAX_ADDITIONS, "num_variations": 1}
    pipeline_timings["intent_detection"] = round((time.time() - t0) * 1000, 1)

    # ═══════════════════════════════════════════════════════════
    # STAGE 4: Entity Extraction
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    entities = extract_entities(query) if ENABLE_ENTITY_EXTRACTION else {}
    pipeline_timings["entity_extraction"] = round((time.time() - t0) * 1000, 1)

    # ═══════════════════════════════════════════════════════════
    # STAGE 5: Context Awareness (chat history / user profile)
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    context_profile = {}
    if ENABLE_CONTEXT_AWARENESS and user_id:
        context_profile = build_context_profile(user_id, {
            "CONTEXT_HISTORY_MAX": CONTEXT_HISTORY_MAX,
            "CONTEXT_PROFILE_FIELDS": CONTEXT_PROFILE_FIELDS,
        })
        enriched = enrich_query_with_context(query, context_profile)
        if enriched != query:
            print(f"[Context Awareness] '{query}' → '{enriched}' (enriched from history)")
            query = enriched
    pipeline_timings["context_awareness"] = round((time.time() - t0) * 1000, 1)

    # ═══════════════════════════════════════════════════════════
    # STAGE 6: Synonym Expansion
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    if ENABLE_SYNONYM_EXPANSION:
        expand_synonyms(query)
    pipeline_timings["synonym_expansion"] = round((time.time() - t0) * 1000, 1)

    # ═══════════════════════════════════════════════════════════
    # STAGE 7: Query Cleaning
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    cleaned_query, was_cleaned = clean_query(query) if ENABLE_QUERY_CLEANING else (query, False)
    if was_cleaned:
        query = cleaned_query
    pipeline_timings["query_cleaning"] = round((time.time() - t0) * 1000, 1)

    # ═══════════════════════════════════════════════════════════
    # STAGE 8: LLM Rewrite
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    rewritten_query = None
    if ENABLE_LLM_REWRITE:
        rewritten_query = rewrite_query(query, use_llm=True)
        if rewritten_query and rewritten_query != query:
            print(f"[Query Rewrite] '{query}' → '{rewritten_query}'")
    else:
        rewritten_query = rewrite_query(query, use_llm=False)
    pipeline_timings["llm_rewrite"] = round((time.time() - t0) * 1000, 1)

    # ═══════════════════════════════════════════════════════════
    # STAGE 9: Multi Query Expansion
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    search_queries = [query]
    if ENABLE_MULTI_QUERY:
        num_vars = cfg.get("num_variations", MULTI_QUERY_VARIATIONS)
        search_queries = expand_queries(query, use_llm=ENABLE_LLM_REWRITE, num_variations=num_vars)
    pipeline_timings["multi_query_expansion"] = round((time.time() - t0) * 1000, 1)

    # ═══════════════════════════════════════════════════════════
    # STAGE 10: Hybrid Search (BM25 + Vector Search)
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    all_results = []
    seen_keys = set()
    for sq in search_queries:
        results = hybrid_retrieve(sq, top_k=cfg["top_k"])
        for r in results:
            key = r["metadata"].get("name", r["metadata"]["file_path"])
            if key not in seen_keys:
                seen_keys.add(key)
                all_results.append(r)
    all_results = all_results[:cfg["top_k"] * 2]
    pipeline_timings["hybrid_search"] = round((time.time() - t0) * 1000, 1)

    # ═══════════════════════════════════════════════════════════
    # STAGE 11: Reranking Model
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    if ENABLE_RERANKING and len(all_results) > TOP_K_RERANK:
        results = rerank(query, all_results, top_n=TOP_K_RERANK)
    else:
        results = all_results[:TOP_K_RERANK]
    pipeline_timings["reranking"] = round((time.time() - t0) * 1000, 1)

    # ═══════════════════════════════════════════════════════════
    # STAGE 12: Context Expansion (dependency graph)
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    if CONTEXT_EXPANSION_ENABLED and results:
        try:
            from embeddings.retriever import get_all_chunks
            from graph.dependency_graph import DependencyGraph
            all_chunks = get_all_chunks()
            graph = DependencyGraph(all_chunks)
            results = expand_context(results, graph, max_additions=cfg.get("max_additions", CONTEXT_MAX_ADDITIONS))
        except Exception:
            pass
    pipeline_timings["context_expansion"] = round((time.time() - t0) * 1000, 1)

    # ═══════════════════════════════════════════════════════════
    # STAGE 13: Context Compression / Filtering
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    if ENABLE_CONTEXT_COMPRESSION and results:
        compressed = compress_results(query, results, max_chunks=COMPRESSED_MAX_CHUNKS)
        if compressed:
            results = compressed
    pipeline_timings["context_compression"] = round((time.time() - t0) * 1000, 1)

    # ═══════════════════════════════════════════════════════════
    # STAGE 14: LLM Response Generation
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    answer = generate_answer(query, results)
    pipeline_timings["llm_generation"] = round((time.time() - t0) * 1000, 1)

    # ═══════════════════════════════════════════════════════════
    # STAGE 15: Fact Checking / Hallucination Guard
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    try:
        validation = validate_answer(answer, results)
    except Exception:
        validation = {"is_grounded": len(results) > 0, "reason": ""}
    pipeline_timings["fact_checking"] = round((time.time() - t0) * 1000, 1)

    t0 = time.time()
    if ENABLE_REFLECTION and results:
        context_str = build_context(results)
        reflected = reflect(query, answer, context_str)
        if reflected and reflected != answer:
            answer = reflected
    pipeline_timings["self_reflection"] = round((time.time() - t0) * 1000, 1)

    # Confidence scoring
    t0 = time.time()
    if ENABLE_CONFIDENCE_SCORING:
        confidence = score_confidence(results, answer, intent)
    else:
        confidence = {"level": "medium", "score": 0.5, "message": None}
    pipeline_timings["confidence_scoring"] = round((time.time() - t0) * 1000, 1)

    # ═══════════════════════════════════════════════════════════
    # STAGE 16: Response Personalization
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    if ENABLE_RESPONSE_PERSONALIZATION and context_profile.get("profile"):
        answer = personalize_response(answer, profile=context_profile["profile"], intent=intent)
    pipeline_timings["response_personalization"] = round((time.time() - t0) * 1000, 1)

    # ═══════════════════════════════════════════════════════════
    # STAGE 17: Build Sources
    # ═══════════════════════════════════════════════════════════
    sources = [
        {
            "file_path": r["metadata"]["file_path"],
            "name": r["metadata"].get("name", ""),
            "score": round(r.get("score", 0), 3),
            "rerank_score": round(r.get("rerank_score", 0), 3) if r.get("rerank_score") else None,
        }
        for r in results[:5]
    ]

    # ═══════════════════════════════════════════════════════════
    # STAGE 18: Feedback Loop (record pipeline run)
    # ═══════════════════════════════════════════════════════════
    if ENABLE_FEEDBACK_LOOP:
        try:
            record_feedback(
                query=original_query,
                answer=answer,
                sources=sources,
                user_id=user_id,
                pipeline_steps=pipeline_timings,
            )
        except Exception:
            pass

    # Save to chat history for context awareness
    if user_id and ENABLE_CONTEXT_AWARENESS:
        try:
            add_to_history(user_id, original_query, answer)
        except Exception:
            pass

    return {
        "answer": answer,
        "sources": sources,
        "retrieved_count": len(results),
        "rewritten_query": rewritten_query,
        "corrected_query": corrected_query if was_corrected else None,
        "original_query": original_query,
        "entities": entities,
        "language": lang_info,
        "intent": intent,
        "validation": validation,
        "confidence": confidence,
        "pipeline_steps": pipeline_timings,
        "latency_ms": round((time.time() - start) * 1000, 1),
    }