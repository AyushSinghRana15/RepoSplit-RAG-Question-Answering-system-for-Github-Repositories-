# app.py — FastAPI application: routes, middleware, and request handlers

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
import json
import uuid
import os
from typing import Optional
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from api.middleware import limiter

from config import EMBED_MODEL, RERANK_MODEL, PROJECT_ROOT

_embed_model = None
_reranker = None

# Lazy-loaded singleton models
def get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer(EMBED_MODEL)
    return _embed_model

from api.schemas import (
    QueryRequest,
    QueryResponse,
    SourceReference,
    UpdateProfileRequest,
    UserProfile,
    QueryHistoryItem,
    UserRepo,
    UserStats,
)
from pipeline.ask import ask
from ingestion.github_ingestor import ingest_github_repo, cleanup_repo
from api.auth import get_optional_user
from api.db import (
    upsert_user,
    get_user,
    update_user_profile,
    save_query_history,
    get_query_history,
    save_user_repo,
    get_user_repos,
    get_user_stats,
)
from pipeline.context_awareness import set_user_profile, get_user_profile

logging.basicConfig(level=logging.INFO, format='{"time": "%(asctime)s", "level": "%(levelname)s", "msg": "%(message)s", "module": "%(module)s"}')
logger = logging.getLogger(__name__)

# FastAPI application setup with rate limiting and CORS
app = FastAPI(
    title="RepoSplit",
    description="Natural language Q&A over code repositories",
    version="1.2.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "https://codebase-ai-assistant.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pre-warm FAISS, BM25, and tokenizer on startup
@app.on_event("startup")
def warm_models():
    global _embed_model, _reranker

    logging.info("Pre-warming FAISS index...")
    try:
        from embeddings.retriever import get_all_chunks
        count = len(get_all_chunks())
        logging.info(f"FAISS index loaded with {count} chunks")
    except Exception as e:
        logging.warning(f"Failed to pre-warm FAISS index: {e}")

    logging.info("Pre-warming BM25 index...")
    try:
        from pipeline.hybrid_retriever import get_bm25_index
        bm25 = get_bm25_index()
        if bm25.available:
            logging.info("BM25 index loaded")
        else:
            logging.warning("BM25 not available (rank-bm25 not installed)")
    except Exception as e:
        logging.warning(f"Failed to pre-warm BM25 index: {e}")

    logging.info("Pre-warming tokenizer...")
    try:
        from llm.tokenizer import count_tokens
        count_tokens("warmup")
        logging.info("Tokenizer ready")
    except Exception as e:
        logging.warning(f"Failed to pre-warm tokenizer: {e}")

    logging.info("Models pre-warmed (embedding/reranker load on demand)")


# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.2.0", "developer": "Ayush Singh"}


# Fun easter egg endpoint
@app.get("/egg")
def easter_egg():
    return {
        "message": "You found the easter egg! 🥚",
        "developer": "Ayush Singh",
        "riddle": "What has keys but can't open locks?",
        "answer": "A keyboard — and this codebase."
    }


# Main Q&A endpoint — runs the full RAG pipeline
@app.post("/ask", response_model=QueryResponse)
def ask_endpoint(
    request: QueryRequest,
    user=Depends(get_optional_user),
):
    start = time.time()
    try:
        result = ask(
            request.query,
            top_k=request.top_k,
            user_id=user.id if user else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

    elapsed = round((time.time() - start) * 1000, 1)
    result["latency_ms"] = elapsed

    # Save query history
    if user:
        try:
            save_query_history(
                user_id=user.id,
                query=request.query,
                answer=result.get("answer", ""),
                sources=result.get("sources", []),
                latency_ms=elapsed,
            )
        except Exception as e:
            logger.warning(f"Failed to save query history: {e}")

    # Sync user profile into context awareness
    if user:
        try:
            existing = get_user(user.id)
            if existing:
                set_user_profile(user.id, existing)
        except Exception:
            pass

    # Structured logging
    log_entry = {
        "event": "query",
        "user_id": user.id if user else None,
        "query": request.query,
        "rewritten": result.get("rewritten_query"),
        "corrected": result.get("corrected_query"),
        "intent": result.get("intent"),
        "entities": result.get("entities"),
        "language": result.get("language"),
        "retrieved": result.get("retrieved_count"),
        "confidence": result.get("confidence"),
        "latency_ms": elapsed,
        "pipeline_steps": result.get("pipeline_steps"),
        "is_grounded": result.get("validation", {}).get("is_grounded") if result.get("validation") else None,
    }
    logger.info(json.dumps(log_entry, default=str))

    return result


# Vector store statistics endpoint
@app.get("/stats")
def stats():
    from embeddings.retriever import _index
    if _index is None:
        from embeddings.retriever import _load
        _load()
    return {
        "total_chunks": _index.ntotal if _index else 0,
        "index_loaded": _index is not None
    }


import threading

INGEST_TMP_DIR = os.path.join(PROJECT_ROOT, ".ingest_status")
os.makedirs(INGEST_TMP_DIR, exist_ok=True)


# Background ingestion runner
def _run_ingestion(task_id: str, status_file: str, repo_url: str, branch: str, user_id: str):
    import gc
    from ingestion.worker import ingest_main
    try:
        ingest_main(task_id, status_file, repo_url, branch or None, user_id or None)
    except Exception as e:
        try:
            with open(status_file, "w") as f:
                json.dump({"status": "error", "error": str(e)}, f)
        except Exception:
            pass
    finally:
        gc.collect()


# Start a GitHub repo ingestion in the background
@app.post("/ingest/github")
def ingest_github(repo_url: str, branch: Optional[str] = None, user=Depends(get_optional_user)):
    task_id = str(uuid.uuid4())
    status_file = os.path.join(INGEST_TMP_DIR, f"{task_id}.json")
    with open(status_file, "w") as f:
        json.dump({"status": "queued", "repo_url": repo_url}, f)

    t = threading.Thread(
        target=_run_ingestion,
        args=(task_id, status_file, repo_url, branch or "", str(user.id) if user else ""),
        daemon=True,
    )
    t.start()
    return {"task_id": task_id, "status": "queued"}


# Poll ingestion task status
@app.get("/ingest/status/{task_id}")
def ingest_status(task_id: str):
    status_file = os.path.join(INGEST_TMP_DIR, f"{task_id}.json")
    if not os.path.exists(status_file):
        raise HTTPException(status_code=404, detail="Task not found")
    with open(status_file) as f:
        return json.load(f)


# Get authenticated user profile
@app.get("/auth/me")
def auth_me(user=Depends(get_optional_user)):
    if not user:
        return {"authenticated": False, "user": None}
    try:
        profile = get_user(user.id)
        if not profile:
            profile = upsert_user(
                user_id=user.id,
                email=user.email or "",
                name=user.user_metadata.get("full_name", user.email or "User"),
                avatar_url=user.user_metadata.get("avatar_url", ""),
            )
        if profile:
            set_user_profile(user.id, profile)
        return {"authenticated": True, "user": profile}
    except Exception as e:
        logger.warning(f"Failed to fetch user profile: {e}")
        return {
            "authenticated": True,
            "user": {
                "id": user.id,
                "email": user.email or "",
                "name": user.user_metadata.get("full_name", user.email or "User"),
            },
        }


# Update user profile (name, bio)
@app.put("/auth/profile")
def update_profile(request: UpdateProfileRequest, user=Depends(get_optional_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    profile = update_user_profile(
        user_id=user.id,
        name=request.name,
        bio=request.bio,
    )
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    if profile:
        set_user_profile(user.id, profile)
    return profile


# Get query history for the authenticated user
@app.get("/auth/history")
def auth_history(limit: int = 50, user=Depends(get_optional_user)):
    if not user:
        return []
    return get_query_history(user_id=user.id, limit=limit)


# Get ingested repos for the authenticated user
@app.get("/auth/repos")
def auth_repos(user=Depends(get_optional_user)):
    if not user:
        return []
    return get_user_repos(user_id=user.id)


# Get user statistics (query count, repo count)
@app.get("/auth/stats")
def auth_stats(user=Depends(get_optional_user)):
    if not user:
        return {"query_count": 0, "repo_count": 0}
    return get_user_stats(user_id=user.id)
