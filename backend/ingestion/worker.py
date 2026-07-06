# worker.py — Background worker that ingests a repo, chunks files, and builds the vector store
# Supports 5GB+ repos by streaming chunks through SQLite instead of holding them in memory.

import sys
import json
import os
import pickle
import time
import gc

from config import MAX_FILE_SIZE, MAX_TOTAL_CHUNKS, MEMORY_THRESHOLD, SQLITE_BATCH_COMMIT
from db.chunk_store import init_db, insert_chunks, count_chunks, clear_db, get_connection

# Local override for worker — imported from config but kept here for backward compat
MAX_FILE_SIZE_WORKER = MAX_FILE_SIZE


def update_status(status_file: str, data: dict):
    with open(status_file, "w") as f:
        json.dump(data, f)


def _get_memory_usage() -> float:
    """Return memory usage as fraction of total RAM (0.0–1.0). Returns 0.0 if psutil unavailable."""
    try:
        import psutil
        return psutil.virtual_memory().percent / 100.0
    except ImportError:
        return 0.0


def _is_over_memory_threshold() -> bool:
    if MEMORY_THRESHOLD <= 0.0:
        return False
    return _get_memory_usage() >= MEMORY_THRESHOLD


def ingest_main(task_id: str, status_file: str, repo_url: str, branch: str | None, user_id: str | None):
    update_status(status_file, {"status": "cloning", "repo_url": repo_url})

    try:
        from ingestion.github_ingestor import ingest_github_repo, cleanup_repo
        files = ingest_github_repo(repo_url, branch)
    except Exception as e:
        update_status(status_file, {"status": "error", "error": f"Clone failed: {e}"})
        return

    if not files:
        update_status(status_file, {"status": "error", "error": "No supported files found in repository"})
        return

    repo_path = os.path.commonpath(files) if files else ""

    lang_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
        ".cpp": "cpp", ".c": "c", ".go": "go", ".rs": "rust",
        ".rb": "ruby", ".php": "php", ".swift": "swift", ".kt": "kotlin",
        ".md": "markdown", ".txt": "text",
    }

    update_status(status_file, {"status": "chunking", "file_count": len(files)})
    try:
        from ingestion.chunker import parse_chunks
    except Exception as e:
        update_status(status_file, {"status": "error", "error": f"Failed to load chunker: {e}"})
        return

    # Initialize SQLite chunk store
    clear_db()
    init_db()
    conn = get_connection()
    total_chunks = 0
    buffer = []

    try:
        for idx, file_path in enumerate(files):
            # Memory check — stop early if we're running low
            if _is_over_memory_threshold():
                update_status(status_file, {
                    "status": "warning",
                    "message": "Memory threshold reached — stopping ingestion early",
                    "file_count": len(files),
                    "current_file": idx + 1,
                    "chunks_so_far": total_chunks,
                })
                break

            # Check max chunks limit (auto-computed from available RAM)
            if MAX_TOTAL_CHUNKS > 0 and total_chunks >= MAX_TOTAL_CHUNKS:
                update_status(status_file, {
                    "status": "warning",
                    "message": f"Max chunks limit ({MAX_TOTAL_CHUNKS}) reached — stopping",
                    "file_count": len(files),
                    "current_file": idx + 1,
                    "chunks_so_far": total_chunks,
                })
                break

            ext = os.path.splitext(file_path)[1]
            language = lang_map.get(ext, "text")

            # Skip files that are too large
            try:
                if os.path.getsize(file_path) > MAX_FILE_SIZE_WORKER:
                    continue
            except OSError:
                continue

            # Quick binary check for files not filtered by extension
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
                chunks = parse_chunks(file_content=content, file_path=rel_path, language=language)
            except Exception:
                continue

            if not chunks:
                continue

            # Write to SQLite in batches to avoid huge memory buffers
            buffer.extend(chunks)
            if len(buffer) >= SQLITE_BATCH_COMMIT:
                insert_chunks(buffer, conn)
                total_chunks += len(buffer)
                buffer = []

            if idx % 10 == 0 or idx == 0:
                update_status(status_file, {
                    "status": "chunking",
                    "file_count": len(files),
                    "current_file": idx + 1,
                    "current_path": rel_path,
                    "chunks_so_far": total_chunks + len(buffer),
                })

        # Flush remaining buffer
        if buffer:
            insert_chunks(buffer, conn)
            total_chunks += len(buffer)
            buffer = []

    finally:
        conn.close()

    try:
        cleanup_repo(repo_path)
    except Exception:
        pass

    # Re-count from DB for accuracy
    total_chunks = count_chunks()

    if total_chunks == 0:
        update_status(status_file, {"status": "error", "error": "No chunks generated from repository", "files_total": len(files)})
        return

    del files
    gc.collect()

    # Write legacy chunks.json for backward compatibility (only if small enough)
    from config import PROJECT_ROOT
    CHUNKS_PATH = os.path.join(PROJECT_ROOT, "output", "chunks.json")
    VECTOR_STORE_DIR = os.path.join(PROJECT_ROOT, "vector_store")
    os.makedirs(os.path.dirname(CHUNKS_PATH), exist_ok=True)
    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

    # For large repos, skip chunks.json and let SQLite be the primary store
    if total_chunks <= 50000:
        from db.chunk_store import get_all_chunks
        all_chunks = get_all_chunks()
        with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f)
        metadata_path = os.path.join(VECTOR_STORE_DIR, "metadata.pkl")
        with open(metadata_path, "wb") as f:
            pickle.dump(all_chunks, f)
        del all_chunks
        gc.collect()

    update_status(status_file, {"status": "chunking_complete", "chunks": total_chunks})

    if user_id:
        try:
            from api.db import save_user_repo
            save_user_repo(user_id=user_id, repo_url=repo_url)
        except Exception:
            pass

    update_status(status_file, {
        "status": "success",
        "files_processed": total_chunks,
        "chunks_created": total_chunks,
        "repo_url": repo_url,
    })


def main():
    ingest_main(
        task_id=sys.argv[1],
        status_file=sys.argv[2],
        repo_url=sys.argv[3],
        branch=sys.argv[4] or None,
        user_id=sys.argv[5] or None,
    )


if __name__ == "__main__":
    main()
