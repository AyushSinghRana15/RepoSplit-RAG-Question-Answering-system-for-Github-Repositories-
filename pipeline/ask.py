from typing import Dict
from functools import lru_cache
from typing import Dict, List, Optional
import time
import logging
from urllib import response

from config import *
from pipeline.reranker import rerank
from pipeline.query_classifier import classify_query, get_pipeline_config
from pipeline.hybrid_retriever import hybrid_retrieve
from llm.generator import generate_answer
from pipeline.validator import validate_answer
from pipeline.query_corrector import correct_query
from pipeline.reflector import reflect
from pipeline.validator import validate_answer, score_confidence, shape_response
from pipeline.query_corrector import correct_query, get_query_suggestions
from pipeline.query_rewriter import rewrite_query
from pipeline.language_detector import detect_language
from pipeline.entity_extractor import extract_entities
from pipeline.context_awareness import build_context_profile, enrich_query_with_context, add_to_history
from pipeline.synonym_expander import expand_synonyms
from pipeline.query_cleaner import clean_query
from pipeline.multi_query_expander import expand_queries
from pipeline.context_compressor import compress_results
from pipeline.response_personalizer import personalize_response
from pipeline.feedback_loop import record_feedback
from pipeline.language_detector import detect_language

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def normalize_query(q: str) -> str:
    return q.lower().strip().rstrip("?")


@lru_cache(maxsize=CACHE_MAX_SIZE)
def cached_ask(query: str) -> Dict:
    return _ask_impl(query)


def build_context(results: List[dict]) -> str:
    parts = []
    for r in results:
        meta = r["metadata"]
        header = f"[{meta.get('file_path', 'unknown')}] {meta.get('chunk_type', 'unknown')}: {meta.get('name', 'unknown')}"
        content = r["content"][:PER_CHUNK_MAX_TOKENS]
        parts.append(f"--- {header} ---\n{content}")
    return "\n\n".join(parts)


def _log_step(step: str, duration: float, details: dict = None):
    msg = f"[Pipeline] {step} took {duration:.1f}ms"
    if details:
        msg += f" | {details}"
    logger.info(msg)


def _ask_impl(query: str) -> Dict:
    start = time.time()
    pipeline_steps = {}

    # 1. Classify intent
    t0 = time.time()
    intent = classify_query(query) if ENABLE_CLASSIFIER else "general"
    cfg = get_pipeline_config(intent) if ENABLE_CLASSIFIER else {"top_k": TOP_K_RETRIEVE, "bm25_weight": 0.5, "max_additions": CONTEXT_MAX_ADDITIONS, "num_variations": 1}
    pipeline_steps["intent_classification"] = round((time.time() - t0) * 1000, 1)

    # 2. Retrieve (hybrid FAISS + BM25)
    t0 = time.time()
    results = hybrid_retrieve(query, top_k=cfg["top_k"])
    pipeline_steps["hybrid_retrieval"] = round((time.time() - t0) * 1000, 1)

    # 3. Rerank
    t0 = time.time()
    if ENABLE_RERANKING and len(results) > TOP_K_RERANK:
        results = rerank(query, results, top_n=TOP_K_RERANK)
    else:
        results = results[:TOP_K_RERANK]
    pipeline_steps["reranking"] = round((time.time() - t0) * 1000, 1)

    # 4. Build context and generate answer
    context = build_context(results)
    t0 = time.time()
    answer = generate_answer(query, results)
    pipeline_steps["llm_generation"] = round((time.time() - t0) * 1000, 1)

    # 5. Validate
    t0 = time.time()
    validation = validate_answer(answer, results)
    pipeline_steps["validation"] = round((time.time() - t0) * 1000, 1)

    # 6. Build sources
    sources = [
        {
            "file_path": r["metadata"]["file_path"],
            "name": r["metadata"].get("name", ""),
            "score": round(r.get("score", 0), 3),
            "rerank_score": round(r.get("rerank_score", 0), 3) if r.get("rerank_score") else None
        }
        for r in results[:5]
    ]

    total = round((time.time() - start) * 1000, 1)

    response = {
        "answer": answer,
        "sources": sources,
        "retrieved_count": len(results),
        "validation": validation,
        "rewritten_query": None,
        "corrected_query": None,
        "original_query": query,
        "entities": {},
        "language": {"natural_language": "en", "programming_language": None},
        "intent": intent,
        "pipeline_steps": pipeline_steps,
        "latency_ms": total,
    }
    return response


def ask(
    query: str,
    top_k: int = 10,
    user_id: Optional[str] = None,
) -> Dict:
    """
    Full RAG pipeline: query → spell-check → classify → hybrid retrieve → rerank → generate → validate.
    """
    start = time.time()

    # Easter egg: Ayush Singh mention
    #Full 18-stage RAG pipeline:
    #Language Detection → Spell Correction → Intent Detection → Entity Extraction → Context Awareness
    #→ Synonym Expansion → Query Cleaning → LLM Rewrite → Multi Query Expansion → Hybrid Search
    #→ Reranking → Context Compression → LLM Response → Fact Checking → Response Personalization
    #→ Caching & Feedback Loop
    """
    pipeline_start = time.time()
    pipeline_timings: Dict[str, float] = {}
    pipeline_log: Dict[str, dict] = {}
    """
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
    pipeline_log = {}
    pipeline_timings = {}
    t0 = time.time()
    lang_info = detect_language(query) if ENABLE_LANGUAGE_DETECTION else {"natural_language": "en", "programming_language": None}
    pipeline_timings["language_detection"] = round((time.time() - t0) * 1000, 1)
    pipeline_log["language"] = lang_info

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

    # Classify intent
    intent = classify_query(query) if ENABLE_CLASSIFIER else "general"
    cfg = get_pipeline_config(intent) if ENABLE_CLASSIFIER else {"top_k": top_k}

    # Hybrid retrieval (FAISS + BM25)
    results = hybrid_retrieve(query, top_k=cfg["top_k"])

    if ENABLE_RERANKING and len(results) > TOP_K_RERANK:
        results = rerank(query, results, top_n=TOP_K_RERANK)
    pipeline_timings["spell_correction"] = round((time.time() - t0) * 1000, 1)
    pipeline_log["spell_correction"] = {"original": original_query, "corrected": corrected_query, "was_corrected": was_corrected}

    # ═══════════════════════════════════════════════════════════
    # STAGE 3: Intent Detection
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    intent = classify_query(query) if ENABLE_CLASSIFIER else "general"
    cfg = get_pipeline_config(intent) if ENABLE_CLASSIFIER else {"top_k": TOP_K_RETRIEVE, "bm25_weight": 0.5, "max_additions": CONTEXT_MAX_ADDITIONS, "num_variations": 1}
    pipeline_timings["intent_detection"] = round((time.time() - t0) * 1000, 1)
    pipeline_log["intent"] = intent

    # ═══════════════════════════════════════════════════════════
    # STAGE 4: Entity Extraction
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    entities = extract_entities(query) if ENABLE_ENTITY_EXTRACTION else {}
    pipeline_timings["entity_extraction"] = round((time.time() - t0) * 1000, 1)
    pipeline_log["entities"] = entities

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
    synonym_variations = expand_synonyms(query) if ENABLE_SYNONYM_EXPANSION else [query]
    pipeline_timings["synonym_expansion"] = round((time.time() - t0) * 1000, 1)
    pipeline_log["synonyms"] = synonym_variations

    # ═══════════════════════════════════════════════════════════
    # STAGE 7: Query Cleaning
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    cleaned_query, was_cleaned = clean_query(query) if ENABLE_QUERY_CLEANING else (query, False)
    if was_cleaned:
        query = cleaned_query
    pipeline_timings["query_cleaning"] = round((time.time() - t0) * 1000, 1)
    pipeline_log["cleaned"] = was_cleaned

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
    pipeline_log["rewritten"] = rewritten_query

    # ═══════════════════════════════════════════════════════════
    # STAGE 9: Multi Query Expansion
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    search_queries = [query]
    if ENABLE_MULTI_QUERY:
        num_vars = cfg.get("num_variations", MULTI_QUERY_VARIATIONS)
        search_queries = expand_queries(query, use_llm=ENABLE_LLM_REWRITE, num_variations=num_vars)
    pipeline_timings["multi_query_expansion"] = round((time.time() - t0) * 1000, 1)
    pipeline_log["search_queries"] = search_queries

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
    pipeline_log["retrieved_raw"] = len(all_results)

    # ═══════════════════════════════════════════════════════════
    # STAGE 11: Reranking Model
    # ═══════════════════════════════════════════════════════════
    t0 = time.time()
    if ENABLE_RERANKING and len(all_results) > TOP_K_RERANK:
        results = rerank(query, all_results, top_n=TOP_K_RERANK)
    else:
        results = results[:TOP_K_RERANK]

    # Generate answer
        results = all_results[:TOP_K_RERANK]
    pipeline_timings["reranking"] = round((time.time() - t0) * 1000, 1)
    pipeline_log["reranked"] = len(results)

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
    pipeline_log["compressed"] = len(results)

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

    result = {
    # ═══════════════════════════════════════════════════════════
    # STAGE 18: Feedback Loop (record pipeline run)
    # ═══════════════════════════════════════════════════════════
    total_latency = round((time.time() - pipeline_start) * 1000, 1)
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

    response = {
        "answer": answer,
        "sources": sources,
        "retrieved_count": len(results),
        "rewritten_query": rewritten_query,
        "corrected_query": corrected_query if was_corrected else None,
        "original_query": original_query,
        "validation": validation
    }
    result["latency_ms"] = round((time.time() - start) * 1000, 1)
    return result
        "original_query": original_query if was_corrected else None,
        "entities": entities,
        "language": lang_info,
        "intent": intent,
        "validation": validation,
        "confidence": confidence,
        "pipeline_steps": pipeline_timings,
        "latency_ms": total_latency,
    }
    return response