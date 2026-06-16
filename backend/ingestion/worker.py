import sys
import json
import os
import pickle
import time
import gc

MAX_FILE_SIZE = 1024 * 1024
MAX_TOTAL_CHUNKS = 3000


def update_status(status_file: str, data: dict):
    with open(status_file, "w") as f:
        json.dump(data, f)


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

    all_chunks = []
    for idx, file_path in enumerate(files):
        ext = os.path.splitext(file_path)[1]
        language = lang_map.get(ext, "text")

        try:
            if os.path.getsize(file_path) > MAX_FILE_SIZE:
                continue
        except OSError:
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
        all_chunks.extend(chunks)

        if len(all_chunks) > MAX_TOTAL_CHUNKS:
            all_chunks = all_chunks[:MAX_TOTAL_CHUNKS]
            break

        if idx % 10 == 0 or idx == 0:
            update_status(status_file, {
                "status": "chunking",
                "file_count": len(files),
                "current_file": idx + 1,
                "current_path": rel_path,
                "chunks_so_far": len(all_chunks),
            })

    try:
        cleanup_repo(repo_path)
    except Exception:
        pass

    if not all_chunks:
        update_status(status_file, {"status": "error", "error": "No chunks generated from repository"})
        return

    total_chunks = len(all_chunks)
    del files, lang_map
    gc.collect()

    try:
        from config import PROJECT_ROOT
    except Exception as e:
        update_status(status_file, {"status": "error", "error": f"Failed to load config: {e}"})
        return
    CHUNKS_PATH = os.path.join(PROJECT_ROOT, "output", "chunks.json")
    VECTOR_STORE_DIR = os.path.join(PROJECT_ROOT, "vector_store")
    os.makedirs(os.path.dirname(CHUNKS_PATH), exist_ok=True)
    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

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
