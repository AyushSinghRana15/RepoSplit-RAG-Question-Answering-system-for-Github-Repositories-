from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
import json
from typing import Optional
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from api.middleware import limiter

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

logging.basicConfig(level=logging.INFO, format='{"time": "%(asctime)s", "level": "%(levelname)s", "msg": "%(message)s", "module": "%(module)s"}')

app = FastAPI(
    title="CodeBase AI Assistant",
    description="Natural language Q&A over code repositories",
    version="1.1.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.1.0", "developer": "Ayush Singh"}


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
        result = ask(request.query, top_k=request.top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    result["latency_ms"] = round((time.time() - start) * 1000, 1)

    if user:
        try:
            save_query_history(
                user_id=user.id,
                query=request.query,
                answer=result.get("answer", ""),
                sources=result.get("sources", []),
                latency_ms=result["latency_ms"],
            )
        except Exception as e:
            logging.warning(f"Failed to save query history: {e}")

    logging.info(json.dumps({
        "event": "query",
        "user_id": user.id if user else None,
        "query": request.query,
        "rewritten": result.get("rewritten_query"),
        "retrieved": result.get("retrieved_count"),
        "latency_ms": result["latency_ms"],
        "is_grounded": result.get("validation", {}).get("is_grounded") if result.get("validation") else None
    }))

    return result


@app.get("/stats")
def stats():
    from embeddings.retriever import _index
    return {
        "total_chunks": _index.ntotal if _index else 0,
        "index_loaded": _index is not None
    }


@app.post("/ingest/github")
def ingest_github(repo_url: str, branch: Optional[str] = None, user=Depends(get_optional_user)):
    try:
        import json
        import os
        from ingestion.chunker import parse_chunks
        from embeddings.embedder import build_embed_text, EMBED_MODEL, BATCH_SIZE, VECTOR_STORE_DIR
        from sentence_transformers import SentenceTransformer
        import faiss
        import numpy as np
        import pickle
        import time

        CHUNKS_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "chunks.json")

        lang_map = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
            ".cpp": "cpp", ".c": "c", ".go": "go", ".rs": "rust",
            ".rb": "ruby", ".php": "php", ".swift": "swift", ".kt": "kotlin",
            ".md": "markdown", ".txt": "text",
        }

        files = ingest_github_repo(repo_url, branch)
        if not files:
            raise HTTPException(status_code=400, detail="No supported files found in repository")

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
            raise HTTPException(status_code=400, detail="No chunks generated from repository")

        os.makedirs(os.path.dirname(CHUNKS_PATH), exist_ok=True)
        with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f)

        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

        logging.info(f"Loading model: {EMBED_MODEL}")
        model = SentenceTransformer(EMBED_MODEL)
        texts = [build_embed_text(c) for c in all_chunks]

        logging.info(f"Generating embeddings for {len(texts)} chunks...")
        start = time.time()
        embeddings = model.encode(texts, batch_size=BATCH_SIZE, show_progress_bar=False)
        elapsed = round(time.time() - start, 2)

        embeddings = np.array(embeddings).astype("float32")
        dim = embeddings.shape[1]

        logging.info(f"Building FAISS index (dim={dim})...")
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings)

        faiss_path = os.path.join(VECTOR_STORE_DIR, "code_index.faiss")
        metadata_path = os.path.join(VECTOR_STORE_DIR, "metadata.pkl")

        faiss.write_index(index, faiss_path)
        with open(metadata_path, "wb") as f:
            pickle.dump(all_chunks, f)

        logging.info(f"Indexing complete: {len(all_chunks)} chunks in {elapsed}s")

        if user:
            try:
                save_user_repo(user_id=user.id, repo_url=repo_url)
            except Exception as e:
                logging.warning(f"Failed to save user repo: {e}")

        return {
            "status": "success",
            "files_processed": len(files),
            "chunks_created": len(all_chunks),
            "indexing_time_s": elapsed,
            "repo_url": repo_url
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        return {"authenticated": True, "user": profile}
    except Exception as e:
        logging.warning(f"Failed to fetch user profile: {e}")
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
