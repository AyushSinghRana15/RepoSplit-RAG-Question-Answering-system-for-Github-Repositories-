# retriever.py — FAISS vector search with IVF support, memory-mapped loading, LRU caching
# Supports large repos via disk-based index access and SQLite metadata storage

import os
import pickle
import time
from functools import lru_cache

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from config import CACHE_MAX_SIZE, PROJECT_ROOT, FAISS_USE_MMAP, IVF_NPROBE, VECTOR_STORE_DIR

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_model = None
_index = None
_metadata = None
_chunks = None
_last_load_mtime = 0.0


def _get_index_mtime() -> float:
    faiss_path = os.path.join(VECTOR_STORE_DIR, "code_index.faiss")
    metadata_path = os.path.join(VECTOR_STORE_DIR, "metadata.pkl")
    t1 = os.path.getmtime(faiss_path) if os.path.exists(faiss_path) else 0
    t2 = os.path.getmtime(metadata_path) if os.path.exists(metadata_path) else 0
    return max(t1, t2)


def _read_index_mmap(faiss_path: str) -> faiss.Index:
    """Read FAISS index with memory mapping if supported."""
    try:
        if FAISS_USE_MMAP:
            return faiss.read_index(faiss_path, faiss.IO_FLAG_MMAP)
    except (AttributeError, RuntimeError, ValueError):
        pass
    return faiss.read_index(faiss_path)


def _load():
    global _model, _index, _metadata, _chunks, _last_load_mtime
    current_mtime = _get_index_mtime()
    if _model is not None and _last_load_mtime >= current_mtime:
        return

    faiss_path = os.path.join(VECTOR_STORE_DIR, "code_index.faiss")
    metadata_path = os.path.join(VECTOR_STORE_DIR, "metadata.pkl")
    db_path = os.path.join(VECTOR_STORE_DIR, "chunks.db")

    _last_load_mtime = current_mtime

    if _model is not None:
        _cached_retrieve.cache_clear()

    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)

    # Load FAISS index (memory-mapped if configured and available)
    if os.path.exists(faiss_path):
        _index = _read_index_mmap(faiss_path)
        # Set nprobe for IVF indexes
        if hasattr(_index, 'nprobe'):
            _index.nprobe = IVF_NPROBE
    else:
        # Fallback: rebuild from metadata.pkl
        with open(metadata_path, "rb") as f:
            _metadata = pickle.load(f)
        chunks = _metadata
        texts = []
        for c in chunks:
            m = c["metadata"]
            texts.append(f"[{m['language']}] {m['chunk_type']}: {m['name']} in {m['file_path']}\n\n{c['content']}")
        embeddings = _model.encode(texts, batch_size=16, show_progress_bar=False)
        embeddings = np.array(embeddings).astype("float32")
        dim = embeddings.shape[1]
        _index = faiss.IndexFlatL2(dim)
        _index.add(embeddings)
        faiss.write_index(_index, faiss_path)

    # Load metadata from SQLite if available (more memory efficient for large repos),
    # otherwise fall back to metadata.pkl
    if os.path.exists(db_path):
        try:
            from db.chunk_store import get_all_chunks
            _metadata = get_all_chunks()
            _chunks = _metadata
        except Exception:
            _metadata = []
            _chunks = []
    else:
        if _metadata is None and os.path.exists(metadata_path):
            with open(metadata_path, "rb") as f:
                _metadata = pickle.load(f)
            _chunks = _metadata


def _encode_query(query: str) -> np.ndarray:
    return _model.encode([query]).astype("float32")


@lru_cache(maxsize=CACHE_MAX_SIZE)
def _cached_retrieve(query: str, top_k: int, score_threshold: float) -> tuple:
    if _index is None or _index.ntotal == 0:
        return ()

    query_vec = _encode_query(query)
    search_k = max(top_k * 2, 20)
    distances, indices = _index.search(query_vec, search_k)

    if len(distances) == 0 or len(indices) == 0:
        return ()

    all_results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(_metadata):
            continue
        chunk = _metadata[idx]
        all_results.append((
            chunk["content"],
            tuple(sorted(chunk["metadata"].items())),
            round(float(dist), 4),
        ))

    threshold_results = [r for r in all_results if r[2] <= score_threshold]
    if len(threshold_results) >= top_k:
        results = threshold_results[:top_k]
    else:
        results = all_results[:top_k]

    return tuple(results)


def dictify_result(r: tuple) -> dict:
    content, meta_items, score = r
    return {"content": content, "metadata": dict(meta_items), "score": score}


def has_indexed_data() -> bool:
    """Check if the vector store has any indexed chunks (lightweight, no model load)."""
    faiss_path = os.path.join(VECTOR_STORE_DIR, "code_index.faiss")
    metadata_path = os.path.join(VECTOR_STORE_DIR, "metadata.pkl")
    return os.path.exists(faiss_path) or os.path.exists(metadata_path)


def retrieve(query: str, top_k: int = 10, score_threshold: float = 2.5) -> list:
    """Retrieve chunks by semantic similarity. Returns top results even if above threshold."""
    _load()
    start = time.time()

    results = [dictify_result(r) for r in _cached_retrieve(query, top_k, score_threshold)]

    elapsed = round((time.time() - start) * 1000, 2)
    print(f"Retrieved {len(results)} chunks in {elapsed}ms (threshold={score_threshold})")
    return results


def retrieve_with_threshold(query: str, top_k: int = 5, max_l2: float = 2.5) -> list:
    results = retrieve(query, top_k=top_k)
    if not results:
        return []
    return results


def get_all_chunks() -> list:
    """Return all indexed chunks for BM25 indexing. Uses SQLite if available."""
    global _chunks
    _load()
    if _chunks is None:
        db_path = os.path.join(VECTOR_STORE_DIR, "chunks.db")
        if os.path.exists(db_path):
            from db.chunk_store import get_all_chunks as get_db_chunks
            _chunks = get_db_chunks()
        else:
            return []
    return _chunks
