import json
import os
import pickle
import time

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

from config import PROJECT_ROOT

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 16
VECTOR_STORE_DIR = os.path.join(PROJECT_ROOT, "vector_store")
CHUNKS_PATH = os.path.join(PROJECT_ROOT, "output", "chunks.json")


def build_embed_text(chunk: dict) -> str:
    m = chunk["metadata"]
    header = f"[{m['language']}] {m['chunk_type']}: {m['name']} in {m['file_path']}"
    return f"{header}\n\n{chunk['content']}"


def embed_chunks():
    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

    print("Loading chunks...")
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"  Loaded {len(chunks)} chunks")

    print(f"Loading model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)

    texts = [build_embed_text(c) for c in chunks]

    print(f"Generating embeddings (batch_size={BATCH_SIZE})...")
    start = time.time()
    embeddings = model.encode(texts, batch_size=BATCH_SIZE, show_progress_bar=True)
    elapsed = round(time.time() - start, 2)

    embeddings = np.array(embeddings).astype("float32")
    dim = embeddings.shape[1]

    print(f"Building FAISS index (dim={dim})...")
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss_path = os.path.join(VECTOR_STORE_DIR, "code_index.faiss")
    metadata_path = os.path.join(VECTOR_STORE_DIR, "metadata.pkl")

    faiss.write_index(index, faiss_path)
    with open(metadata_path, "wb") as f:
        pickle.dump(chunks, f)

    print("Embeddings complete")
    print(f"  Chunks embedded  : {len(chunks)}")
    print(f"  Embedding dim    : {dim}")
    print(f"  FAISS index size : {index.ntotal} vectors")
    print(f"  Saved to         : {faiss_path}")
    print(f"  Metadata saved   : {metadata_path}")
    print(f"  Time taken       : {elapsed}s")


if __name__ == "__main__":
    embed_chunks()
