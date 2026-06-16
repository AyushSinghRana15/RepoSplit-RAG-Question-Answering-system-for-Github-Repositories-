import sys
import json
import os
import time
import gc
import pickle

def update_status(status_file: str, data: dict):
    with open(status_file, "w") as f:
        json.dump(data, f)

def main():
    task_id = sys.argv[1]
    status_file = sys.argv[2]
    repo_url = sys.argv[3]
    branch = sys.argv[4] or None
    user_id_str = sys.argv[5] or None

    update_status(status_file, {"status": "cloning", "repo_url": repo_url})

    try:
        from ingestion.github_ingestor import ingest_github_repo
        files = ingest_github_repo(repo_url, branch)
    except Exception as e:
        update_status(status_file, {"status": "error", "error": f"Clone failed: {e}"})
        return

    if not files:
        update_status(status_file, {"status": "error", "error": "No supported files found in repository"})
        return

    lang_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
        ".cpp": "cpp", ".c": "c", ".go": "go", ".rs": "rust",
        ".rb": "ruby", ".php": "php", ".swift": "swift", ".kt": "kotlin",
        ".md": "markdown", ".txt": "text",
    }

    update_status(status_file, {"status": "chunking", "file_count": len(files)})
    from ingestion.chunker import parse_chunks
    repo_path = os.path.commonpath(files) if files else ""
    all_chunks = []
    for idx, file_path in enumerate(files):
        ext = os.path.splitext(file_path)[1]
        language = lang_map.get(ext, "text")
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
        update_status(status_file, {"status": "chunking", "file_count": len(files), "current_file": idx + 1, "current_path": rel_path})

    if not all_chunks:
        update_status(status_file, {"status": "error", "error": "No chunks generated from repository"})
        return

    total_chunks = len(all_chunks)
    update_status(status_file, {"status": "embedding", "chunk_count": total_chunks})

    from config import PROJECT_ROOT
    CHUNKS_PATH = os.path.join(PROJECT_ROOT, "output", "chunks.json")
    VECTOR_STORE_DIR = os.path.join(PROJECT_ROOT, "vector_store")
    os.makedirs(os.path.dirname(CHUNKS_PATH), exist_ok=True)
    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f)

    texts = [f"[{c['metadata']['language']}] {c['metadata']['chunk_type']}: {c['metadata']['name']} in {c['metadata']['file_path']}\n\n{c['content']}" for c in all_chunks]

    metadata_path = os.path.join(VECTOR_STORE_DIR, "metadata.pkl")
    with open(metadata_path, "wb") as f:
        pickle.dump(all_chunks, f)
    del all_chunks
    gc.collect()

    from sentence_transformers import SentenceTransformer
    from config import EMBED_MODEL
    import faiss
    import numpy as np

    model = SentenceTransformer(EMBED_MODEL)
    gc.collect()

    start = time.time()
    embeddings = model.encode(texts, batch_size=16, show_progress_bar=False)
    elapsed = round(time.time() - start, 2)
    del texts
    gc.collect()

    embeddings = np.array(embeddings).astype("float32")
    dim = embeddings.shape[1]

    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    del embeddings
    gc.collect()

    faiss_path = os.path.join(VECTOR_STORE_DIR, "code_index.faiss")
    faiss.write_index(index, faiss_path)

    if user_id_str:
        try:
            from api.db import save_user_repo
            save_user_repo(user_id=user_id_str, repo_url=repo_url)
        except Exception:
            pass

    update_status(status_file, {
        "status": "success",
        "files_processed": len(files),
        "chunks_created": total_chunks,
        "indexing_time_s": elapsed,
        "repo_url": repo_url,
    })

if __name__ == "__main__":
    main()
