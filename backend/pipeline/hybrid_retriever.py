# hybrid_retriever.py — Hybrid search combining FAISS (semantic) and BM25 (keyword) via RRF fusion

import re
from typing import List, Dict


class BM25Index:
    def __init__(self, chunks: List[dict]):
        try:
            from rank_bm25 import BM25Okapi
            tokenized = [self._tokenize(c["content"]) for c in chunks]
            self.bm25 = BM25Okapi(tokenized)
            self.chunks = chunks
            self.available = True
        except ImportError:
            self.available = False

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'[a-zA-Z0-9_]+', text)

    def search(self, query: str, top_k: int = 10) -> List[dict]:
        if not self.available:
            return []
        tokens = self._tokenize(query)
        scores = self.bm25.get_scores(tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        results = []
        for i in top_indices:
            if scores[i] <= 0:
                continue
            chunk = self.chunks[i].copy()
            chunk["bm25_score"] = float(scores[i])
            results.append(chunk)
        return results


_bm25_index = None


def get_bm25_index() -> BM25Index:
    global _bm25_index
    if _bm25_index is None:
        from embeddings.retriever import get_all_chunks
        chunks = get_all_chunks()
        _bm25_index = BM25Index(chunks)
    return _bm25_index


def clear_bm25_index():
    """Clear the cached BM25 index (call after re-ingestion)."""
    global _bm25_index
    _bm25_index = None


def _chunk_key(result: dict) -> str:
    meta = result["metadata"]
    return f"{meta['file_path']}:{meta.get('name', '')}:{meta.get('start_line', 0)}"


def reciprocal_rank_fusion(
    faiss_results: List[dict],
    bm25_results: List[dict],
    k: int = 60,
    bm25_weight: float = 0.5,
) -> List[dict]:
    scores = {}
    chunk_map = {}
    faiss_weight = 1.0 - bm25_weight

    for rank, result in enumerate(faiss_results):
        key = _chunk_key(result)
        scores[key] = scores.get(key, 0) + faiss_weight / (k + rank + 1)
        chunk_map[key] = result

    for rank, result in enumerate(bm25_results):
        key = _chunk_key(result)
        scores[key] = scores.get(key, 0) + bm25_weight / (k + rank + 1)
        if key not in chunk_map:
            chunk_map[key] = result

    sorted_keys = sorted(scores.keys(), key=lambda n: scores[n], reverse=True)
    return [chunk_map[n] for n in sorted_keys]


def hybrid_retrieve(
    query: str,
    top_k: int = 15,
    bm25_weight: float = 0.5,
) -> List[dict]:
    from embeddings.retriever import retrieve
    faiss_results = retrieve(query, top_k=top_k)

    bm25 = get_bm25_index()
    if not bm25.available:
        return faiss_results[:top_k]

    bm25_results = bm25.search(query, top_k=top_k)

    if not bm25_results:
        return faiss_results[:top_k]

    fused = reciprocal_rank_fusion(faiss_results, bm25_results, bm25_weight=bm25_weight)
    return fused[:top_k]
