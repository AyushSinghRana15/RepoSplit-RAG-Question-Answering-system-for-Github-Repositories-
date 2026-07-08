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


# Diagnostic endpoint — tests chunker inline to debug "No chunks" issues
@app.get("/debug/diagnose")
def diagnose():
    import tempfile, subprocess, shutil
    from pathlib import Path
    from ingestion.chunker import parse_chunks

    results = {}

    # 1. Check SQLite
    import sqlite3
    from config import CHUNK_DB_PATH, PROJECT_ROOT
    results["project_root"] = PROJECT_ROOT
    results["chunk_db_path"] = CHUNK_DB_PATH
    results["chunk_db_dir_exists"] = os.path.exists(os.path.dirname(CHUNK_DB_PATH))
    results["project_root_writable"] = os.access(PROJECT_ROOT, os.W_OK)
    results["chunk_db_dir_writable"] = os.access(os.path.dirname(CHUNK_DB_PATH), os.W_OK) if os.path.exists(os.path.dirname(CHUNK_DB_PATH)) else "dir_does_not_exist"

    # Test actual SQLite operations
    try:
        os.makedirs(os.path.dirname(CHUNK_DB_PATH), exist_ok=True)
        results["mkdir_success"] = True
        conn = sqlite3.connect(CHUNK_DB_PATH)
        conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, val TEXT)")
        conn.execute("INSERT INTO test (val) VALUES ('hello')")
        val = conn.execute("SELECT val FROM test LIMIT 1").fetchone()[0]
        conn.execute("DROP TABLE IF EXISTS test")
        conn.close()
        os.remove(CHUNK_DB_PATH)
        results["sqlite_test"] = val
    except Exception as e:
        results["sqlite_error"] = str(e)

    # 2. Test clone and chunk a single small file
    repo_url = "https://github.com/pallets/flask.git"
    temp_dir = tempfile.mkdtemp(prefix="codebase_diag_")
    try:
        subprocess.run(["git", "clone", "--depth", "1", "--single-branch", repo_url, temp_dir],
                       check=True, capture_output=True, timeout=120)
        results["clone_success"] = True

        py_files = list(Path(temp_dir).rglob("*.py"))
        results["total_py_files"] = len(py_files)

        if py_files:
            # Test parse_chunks on the first Python file
            fp = str(py_files[0])
            results["test_file"] = fp
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            results["test_file_size"] = len(content)
            try:
                chunks = parse_chunks(content, fp, "python")
                results["test_file_chunks"] = len(chunks)
                if chunks:
                    results["test_file_chunk_preview"] = chunks[0]["content"][:100]
            except Exception as e:
                results["parse_chunks_error"] = str(e)

            # Test on a markdown file
            md_files = list(Path(temp_dir).rglob("*.md"))
            if md_files:
                mfp = str(md_files[0])
                results["test_md_file"] = mfp
                with open(mfp, "r", encoding="utf-8", errors="ignore") as f:
                    md_content = f.read()
                results["test_md_file_size"] = len(md_content)
                try:
                    md_chunks = parse_chunks(md_content, mfp, "markdown")
                    results["test_md_chunks"] = len(md_chunks)
                except Exception as e:
                    results["test_md_error"] = str(e)
    except Exception as e:
        results["clone_or_process_error"] = str(e)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # 3. Test parse_chunks on a direct string
    try:
        direct = parse_chunks("def hello():\n    print('world')\n", "test.py", "python")
        results["direct_python_chunks"] = len(direct)
    except Exception as e:
        results["direct_python_error"] = str(e)

    try:
        direct_text = parse_chunks("Hello world, this is a test document.\n" * 10, "test.txt", "text")
        results["direct_text_chunks"] = len(direct_text)
    except Exception as e:
        results["direct_text_error"] = str(e)

    # 4. Check psutil
    try:
        import psutil
        mem = psutil.virtual_memory()
        results["memory_percent"] = mem.percent
        results["memory_available_gb"] = round(mem.available / (1024**3), 2)
        results["memory_total_gb"] = round(mem.total / (1024**3), 2)
    except Exception as e:
        results["psutil_error"] = str(e)

    return results


# Deep debug — simulates the exact worker flow for a small repo
@app.get("/debug/deep-diagnose")
def deep_diagnose():
    import tempfile, subprocess, shutil, time
    from pathlib import Path
    from config import MAX_FILE_SIZE
    from ingestion.chunker import parse_chunks

    repo_url = "https://github.com/pallets/flask.git"
    results = {"repo_url": repo_url}

    # Clone
    temp_dir = tempfile.mkdtemp(prefix="codebase_deep_")
    try:
        subprocess.run(["git", "clone", "--depth", "1", "--single-branch", repo_url, temp_dir],
                       check=True, capture_output=True, timeout=120)
        results["clone_ok"] = True

        # Simulate what ingest_github_repo does
        supported_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c',
            '.h', '.hpp', '.go', '.rs', '.rb', '.php', '.swift', '.kt',
            '.scala', '.cs', '.sh', '.bash', '.zsh', '.sql', '.css',
            '.scss', '.less', '.html', '.htm', '.xml', '.yaml', '.yml',
            '.toml', '.json', '.md', '.rst', '.txt',
        }
        skip_dirs = {
            '.git', 'node_modules', '__pycache__', 'venv', '.venv',
            'data', 'datasets', 'dataset', 'assets', 'static',
            'models', 'checkpoints', 'weights', '.ipynb_checkpoints',
            'dist', 'build', '.tox', '.mypy_cache', '.pytest_cache',
            '.next', '.turbo', 'out', '.cache', 'coverage', '.vercel',
            '.serverless_micro', 'public', 'output', 'vector_store',
            '.terraform', 'Pods', '.gradle', 'target', 'bin', 'obj',
            'vendor', 'third_party', 'third-party', '.bazel',
            'site-packages', '.eggs', 'eggs', '.dart_tool',
        }
        skip_extensions = {
            '.csv', '.tsv', '.jsonl', '.parquet', '.pickle', '.pkl',
            '.h5', '.hdf5', '.npy', '.npz', '.bin', '.dat', '.db',
            '.sqlite', '.sqlite3', '.arrow', '.feather',
        }
        results["_ingestor_loaded"] = True

        files = []
        for fp in Path(temp_dir).rglob("*"):
            if not fp.is_file():
                continue
            parts = fp.relative_to(temp_dir).parts
            if any(p in skip_dirs for p in parts):
                continue
            if fp.suffix in skip_extensions:
                continue
            if fp.suffix in supported_extensions:
                files.append(str(fp))

        results["total_files"] = len(files)

        # Process first 5 files like the worker does
        repo_path = os.path.commonpath(files) if files else ""
        results["repo_path"] = repo_path

        lang_map = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
            ".cpp": "cpp", ".c": "c", ".go": "go", ".rs": "rust",
            ".rb": "ruby", ".php": "php", ".swift": "swift", ".kt": "kotlin",
            ".md": "markdown", ".txt": "text",
        }

        sample_results = []
        for idx, file_path in enumerate(files[:5]):
            info = {"idx": idx, "path": file_path}
            ext = os.path.splitext(file_path)[1]
            language = lang_map.get(ext, "text")
            info["language"] = language
            info["ext"] = ext
            info["exists"] = os.path.exists(file_path)
            try:
                info["size"] = os.path.getsize(file_path)
            except Exception as e:
                info["size_error"] = str(e)
                sample_results.append(info)
                continue

            try:
                with open(file_path, "rb") as f:
                    raw = f.read(8192)
                info["binary"] = b"\0" in raw
            except Exception as e:
                info["read_error"] = str(e)
                sample_results.append(info)
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                info["content_len"] = len(content)
                info["content_stripped"] = len(content.strip())
            except Exception as e:
                info["read_text_error"] = str(e)
                sample_results.append(info)
                continue

            rel_path = os.path.relpath(file_path, repo_path) if repo_path else file_path
            info["rel_path"] = rel_path

            try:
                chunks = parse_chunks(file_content=content, file_path=rel_path, language=language)
                info["chunks_returned"] = len(chunks)
                if chunks:
                    info["sample_chunk"] = chunks[0]["content"][:80]
                    info["sample_chunk_len"] = len(chunks[0]["content"])
            except Exception as e:
                info["parse_error"] = str(e)

            sample_results.append(info)

        results["sample_results"] = sample_results

        # Also count total chunks from all files (but only process first 20)
        total_chunks = 0
        for idx, file_path in enumerate(files[:20]):
            ext = os.path.splitext(file_path)[1]
            language = lang_map.get(ext, "text")

            if os.path.getsize(file_path) > MAX_FILE_SIZE:
                continue

            try:
                with open(file_path, "rb") as f:
                    raw = f.read(8192)
                if b"\0" in raw:
                    continue
            except Exception:
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            rel_path = os.path.relpath(file_path, repo_path) if repo_path else file_path

            try:
                chunks = parse_chunks(content, rel_path, language)
                total_chunks += len(chunks) if chunks else 0
            except Exception:
                continue

        results["total_chunks_from_20_files"] = total_chunks

    except Exception as e:
        results["error"] = str(e)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Also run the same test in a DAEMON THREAD to reproduce the worker issue
    import threading, queue
    thread_result = queue.Queue()
    def _test_in_thread():
        """Same chunking logic but run in a daemon thread."""
        local_result = {}
        try:
            # Check importing in thread
            try:
                from ingestion.chunker import parse_chunks as pc2
                local_result["import_in_thread"] = "ok"
            except Exception as e:
                local_result["import_in_thread"] = str(e)
                thread_result.put(local_result)
                return

            # Test parse_chunks on a simple string
            try:
                c = pc2("def foo():\n    pass\n", "test.py", "python")
                local_result["thread_parse_chunks"] = len(c)
            except Exception as e:
                local_result["thread_parse_error"] = str(e)

            # Test worker's import flow
            try:
                from ingestion.worker import ingest_main
                local_result["import_worker_ok"] = True
            except Exception as e:
                local_result["import_worker_err"] = str(e)

            # Test running ingest_main in thread (use a very small repo)
            import tempfile, subprocess, shutil
            from pathlib import Path
            from ingestion.chunker import parse_chunks as pc3

            small_template = tempfile.mkdtemp(prefix="thread_small_")
            try:
                os.makedirs(os.path.join(small_template, "src"), exist_ok=True)
                with open(os.path.join(small_template, "src", "hello.py"), "w") as f:
                    f.write("def greet(name):\n    return f'Hello {name}'\n\nclass Person:\n    def __init__(self, name):\n        self.name = name\n")
                with open(os.path.join(small_template, "README.md"), "w") as f:
                    f.write("# Test Repo\n\nThis is a test.\n")

                py_files = list(Path(small_template).rglob("*.py"))
                for fp in py_files[:1]:
                    try:
                        with open(fp, "r") as f:
                            content = f.read()
                        c = pc3(content, str(fp), "python")
                        local_result["thread_chunk_small_file"] = len(c)
                    except Exception as e:
                        local_result["thread_chunk_small_err"] = str(e)

                md_files = list(Path(small_template).rglob("*.md"))
                for fp in md_files[:1]:
                    try:
                        with open(fp, "r") as f:
                            content = f.read()
                        c = pc3(content, str(fp), "markdown")
                        local_result["thread_chunk_small_md"] = len(c)
                    except Exception as e:
                        local_result["thread_chunk_small_md_err"] = str(e)

            finally:
                shutil.rmtree(small_template, ignore_errors=True)

        except Exception as e:
            local_result["thread_unexpected"] = str(e)
        thread_result.put(local_result)

    t = threading.Thread(target=_test_in_thread, daemon=True)
    t.start()
    t.join(timeout=15)
    if t.is_alive():
        results["thread_test"] = "timeout (>15s)"
    else:
        results["thread_test"] = thread_result.get(timeout=2)

    return results


# Runs the exact ingest_main function synchronously (no background thread)
@app.get("/debug/test-ingest-main")
def test_ingest_main():
    import tempfile, subprocess, shutil, uuid
    from pathlib import Path

    results = {}
    task_id = str(uuid.uuid4())
    status_file = os.path.join(INGEST_TMP_DIR, f"{task_id}.json")

    with open(status_file, "w") as f:
        json.dump({"status": "queued"}, f)

    repo_url = "https://github.com/pallets/flask.git"

    try:
        from ingestion.worker import ingest_main
        ingest_main(task_id, status_file, repo_url, None, None)
    except Exception as e:
        results["call_error"] = str(e)

    with open(status_file) as f:
        final_status = json.load(f)
    results["final_status"] = final_status

    # Clean up status file
    try:
        os.remove(status_file)
    except Exception:
        pass

    return results


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


# Repository structure endpoint — returns file tree with functions/classes and docstrings
@app.get("/ingest/repo-structure")
def repo_structure():
    from db.chunk_store import get_repo_structure
    try:
        return get_repo_structure()
    except Exception as e:
        logger.error(f"Failed to get repo structure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get repo structure: {str(e)}")


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
