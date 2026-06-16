from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
import json
import asyncio
import uuid
from typing import Optional
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from api.middleware import limiter

from config import EMBED_MODEL, RERANK_MODEL, PROJECT_ROOT

_embed_model = None
_reranker = None

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

app = FastAPI(
    title="CodeBase AI Assistant",
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


@app.on_event("startup")
def warm_models():
    global _embed_model, _reranker

    logging.info("Pre-warming embedding model...")
    try:
        _embed_model = get_embed_model()
        logging.info(f"Embedding model '{EMBED_MODEL}' loaded")
    except Exception as e:
        logging.warning(f"Failed to pre-warm embedding model: {e}")

    logging.info("Pre-warming reranker model...")
    try:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(RERANK_MODEL)
        logging.info(f"Reranker model '{RERANK_MODEL}' loaded")
    except Exception as e:
        logging.warning(f"Failed to pre-warm reranker model: {e}")

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

    logging.info("All models pre-warmed")


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.2.0", "developer": "Ayush Singh"}


@app.get("/egg")
def easter_egg():
    return {
        "message": "You found the easter egg! 🥚",
        "developer": "Ayush Singh",
        "riddle": "What has keys but can't open locks?",
        "answer": "A keyboard — and this codebase."
    }


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
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

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


@app.get("/stats")
def stats():
    from embeddings.retriever import _index
    return {
        "total_chunks": _index.ntotal if _index else 0,
        "index_loaded": _index is not None
    }


_ingest_tasks: dict = {}
_executor = None

def get_executor():
    global _executor
    if _executor is None:
        from concurrent.futures import ThreadPoolExecutor
        _executor = ThreadPoolExecutor(max_workers=1)
    return _executor

def run_ingest_sync(task_id: str, repo_url: str, branch: Optional[str], user_id: Optional[str]):
    import os, json, pickle, time
    from ingestion.chunker import parse_chunks
    from embeddings.embedder import build_embed_text, EMBED_MODEL, BATCH_SIZE, VECTOR_STORE_DIR
    import faiss
    import numpy as np

    lang_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
        ".cpp": "cpp", ".c": "c", ".go": "go", ".rs": "rust",
        ".rb": "ruby", ".php": "php", ".swift": "swift", ".kt": "kotlin",
        ".md": "markdown", ".txt": "text",
    }

    try:
        _ingest_tasks[task_id] = {"status": "cloning", "repo_url": repo_url}

        files = ingest_github_repo(repo_url, branch)
        if not files:
            _ingest_tasks[task_id] = {"status": "error", "error": "No supported files found in repository"}
            return

        _ingest_tasks[task_id] = {"status": "chunking", "file_count": len(files)}
        repo_path = os.path.commonpath(files) if files else ""
        all_chunks = []
        for file_path in files:
            ext = os.path.splitext(file_path)[1]
            language = lang_map.get(ext, "text")
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            rel_path = os.path.relpath(file_path, repo_path) if repo_path else file_path
            chunks = parse_chunks(file_content=content, file_path=rel_path, language=language)
            all_chunks.extend(chunks)

        if not all_chunks:
            _ingest_tasks[task_id] = {"status": "error", "error": "No chunks generated from repository"}
            return

        CHUNKS_PATH = os.path.join(PROJECT_ROOT, "output", "chunks.json")
        os.makedirs(os.path.dirname(CHUNKS_PATH), exist_ok=True)
        with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f)

        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

        _ingest_tasks[task_id] = {"status": "embedding", "chunk_count": len(all_chunks)}
        model = get_embed_model()
        texts = [build_embed_text(c) for c in all_chunks]

        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        start = time.time()
        embeddings = model.encode(texts, batch_size=BATCH_SIZE, show_progress_bar=False)
        elapsed = round(time.time() - start, 2)

        embeddings = np.array(embeddings).astype("float32")
        dim = embeddings.shape[1]

        logger.info(f"Building FAISS index (dim={dim})...")
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings)

        faiss_path = os.path.join(VECTOR_STORE_DIR, "code_index.faiss")
        metadata_path = os.path.join(VECTOR_STORE_DIR, "metadata.pkl")

        faiss.write_index(index, faiss_path)
        with open(metadata_path, "wb") as f:
            pickle.dump(all_chunks, f)

        logger.info(f"Indexing complete: {len(all_chunks)} chunks in {elapsed}s")

        if user_id:
            try:
                save_user_repo(user_id=user_id, repo_url=repo_url)
            except Exception as e:
                logger.warning(f"Failed to save user repo: {e}")

        _ingest_tasks[task_id] = {
            "status": "success",
            "files_processed": len(files),
            "chunks_created": len(all_chunks),
            "indexing_time_s": elapsed,
            "repo_url": repo_url,
        }
    except Exception as e:
        logger.error(f"Ingest task failed: {e}", exc_info=True)
        _ingest_tasks[task_id] = {"status": "error", "error": str(e)}


@app.post("/ingest/github")
async def ingest_github_async(repo_url: str, branch: Optional[str] = None, user=Depends(get_optional_user)):
    task_id = str(uuid.uuid4())
    _ingest_tasks[task_id] = {"status": "queued", "repo_url": repo_url}
    loop = asyncio.get_event_loop()
    loop.run_in_executor(get_executor(), run_ingest_sync, task_id, repo_url, branch, user.id if user else None)
    return {"task_id": task_id, "status": "queued"}


@app.get("/ingest/status/{task_id}")
def ingest_status(task_id: str):
    task = _ingest_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


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


@app.get("/auth/history")
def auth_history(limit: int = 50, user=Depends(get_optional_user)):
    if not user:
        return []
    return get_query_history(user_id=user.id, limit=limit)


@app.get("/auth/repos")
def auth_repos(user=Depends(get_optional_user)):
    if not user:
        return []
    return get_user_repos(user_id=user.id)


@app.get("/auth/stats")
def auth_stats(user=Depends(get_optional_user)):
    if not user:
        return {"query_count": 0, "repo_count": 0}
    return get_user_stats(user_id=user.id)
