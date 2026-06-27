# embedder.py — Embed code chunks and build a FAISS vector index
# Supports large repos via: streaming from SQLite, IndexIVFFlat, memory-mapped index

import json
import os
import pickle
import time
import gc

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from config import (
    PROJECT_ROOT, EMBED_MODEL, FAISS_INDEX_TYPE, FAISS_USE_MMAP,
    IVF_NLIST, EMBED_BATCH_SIZE_STREAMING, CHUNKS_PATH, VECTOR_STORE_DIR
)


def build_embed_text_from_row(row) -> str:
    """Build embeddable text from a raw SQLite row (avoids dict overhead)."""
    header = f"[{row[3]}] {row[4]}: {row[5]} in {row[2]}"
    return f"{header}\n\n{row[1]}"


def build_embed_text(chunk: dict) -> str:
    m = chunk["metadata"]
    header = f"[{m['language']}] {m['chunk_type']}: {m['name']} in {m['file_path']}"
    return f"{header}\n\n{chunk['content']}"


def _build_faiss_index(embeddings: np.ndarray, index_type: str) -> faiss.Index:
    """Build FAISS index: IndexFlatL2 (exact) or IndexIVFFlat (approximate, scalable)."""
    dim = embeddings.shape[1]
    ntotal = embeddings.shape[0]

    if index_type == "ivf" and ntotal > 5000:
        nlist = min(IVF_NLIST, ntotal // 10)
        nlist = max(nlist, 1)
        quantizer = faiss.IndexFlatL2(dim)
        index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_L2)
        if not index.is_trained:
            # Sample up to 256k vectors for training (avoid OOM on very large datasets)
            sample_size = min(ntotal, 256_000)
            sample_indices = np.random.choice(ntotal, sample_size, replace=False)
            index.train(embeddings[sample_indices])
        index.add(embeddings)
        index.nprobe = 10
        return index
    else:
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings)
        return index


def embed_chunks():
    """Main embedding pipeline: stream chunks from SQLite → embed → build FAISS index."""
    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

    # Try SQLite first, fall back to chunks.json
    db_path = os.path.join(VECTOR_STORE_DIR, "chunks.db")
    use_sqlite = os.path.exists(db_path)

    if use_sqlite:
        from db.chunk_store import stream_chunks_raw, count_chunks
        total = count_chunks()
        print(f"Loading chunks from SQLite: {total} chunks")
        chunk_iter = stream_chunks_raw(batch_size=EMBED_BATCH_SIZE_STREAMING)
    else:
        print(f"Loading chunks from JSON: {CHUNKS_PATH}")
        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        total = len(chunks)
        print(f"  Loaded {total} chunks")

    print(f"Loading model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)
    dim = model.get_sentence_embedding_dimension()

    all_embeddings_list = []
    all_chunks = [] if not use_sqlite else None
    batch_num = 0

    start = time.time()

    if use_sqlite:
        for batch_rows in chunk_iter:
            texts = [build_embed_text_from_row(r) for r in batch_rows]
            batch_embeddings = model.encode(texts, batch_size=min(64, len(texts)), show_progress_bar=True)
            all_embeddings_list.append(np.array(batch_embeddings).astype("float32"))
            batch_num += 1
            if batch_num % 10 == 0:
                elapsed = round(time.time() - start, 2)
                processed = sum(a.shape[0] for a in all_embeddings_list)
                print(f"  Embedded {processed}/{total} chunks ({elapsed}s)")
                gc.collect()
    else:
        texts = [build_embed_text(c) for c in chunks]
        print(f"Generating embeddings (batch_size=64)...")
        embeddings = model.encode(texts, batch_size=64, show_progress_bar=True)
        all_embeddings_list.append(np.array(embeddings).astype("float32"))

    elapsed = round(time.time() - start, 2)

    if not all_embeddings_list:
        print("No embeddings generated!")
        return

    embeddings = np.vstack(all_embeddings_list)
    ntotal = embeddings.shape[0]
    del all_embeddings_list
    gc.collect()

    print(f"Building FAISS index (type={FAISS_INDEX_TYPE}, dim={dim}, n={ntotal})...")
    index = _build_faiss_index(embeddings, FAISS_INDEX_TYPE)
    del embeddings
    gc.collect()

    faiss_path = os.path.join(VECTOR_STORE_DIR, "code_index.faiss")

    # Write the FAISS index
    if FAISS_USE_MMAP:
        faiss.write_index(index, faiss_path)
    else:
        faiss.write_index(index, faiss_path)

    # Ensure clean close — re-read with mmap if configured
    del index
    gc.collect()

    # Build metadata.pkl for backward compat (only if manageable)
    if use_sqlite:
        from db.chunk_store import get_all_chunks
        all_chunks = get_all_chunks()

    metadata_path = os.path.join(VECTOR_STORE_DIR, "metadata.pkl")
    with open(metadata_path, "wb") as f:
        pickle.dump(all_chunks, f)

    del all_chunks
    gc.collect()

    print("Embeddings complete")
    print(f"  Chunks embedded  : {ntotal}")
    print(f"  Embedding dim    : {dim}")
    print(f"  FAISS index type : {FAISS_INDEX_TYPE}")
    print(f"  FAISS index size : {os.path.getsize(faiss_path) / 1024 / 1024:.1f} MB")
    print(f"  Time taken       : {elapsed}s")


if __name__ == "__main__":
    embed_chunks()
