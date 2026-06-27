# config.py — single source of truth for all tunable parameters

import os
import sys

_base = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _base == "/":
    _base = os.getcwd()
PROJECT_ROOT = _base

# Embedding model
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_BATCH_SIZE = 64

# Retrieval
TOP_K_RETRIEVE = 15
TOP_K_RERANK = 5
SCORE_THRESHOLD = 2.5

# Reranking
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
ENABLE_RERANKING = True

# Query rewriting
ENABLE_LLM_REWRITE = True

# LLM
LLM_MODEL = "openai/gpt-oss-120b:free"
LLM_TEMPERATURE = 0.2
LLM_MAX_TOKENS = 2000
LLM_TOP_P = 0.9

# Context builder
MAX_CONTEXT_TOKENS = 16000
PER_CHUNK_MAX_TOKENS = 2500

# Caching
CACHE_MAX_SIZE = 200

# API
API_HOST = "0.0.0.0"
API_PORT = 8000
RATE_LIMIT = "20/minute"

# Paths
CHUNKS_PATH = os.path.join(PROJECT_ROOT, "output", "chunks.json")
FAISS_INDEX_PATH = os.path.join(PROJECT_ROOT, "vector_store", "code_index.faiss")
METADATA_PATH = os.path.join(PROJECT_ROOT, "vector_store", "metadata.pkl")
AGENT_MD_PATH = os.path.join(PROJECT_ROOT, "AGENT.md")

# Vector store directory
VECTOR_STORE_DIR = os.path.join(PROJECT_ROOT, "vector_store")

# SQLite chunk store (replaces chunks.json for large repos)
CHUNK_DB_PATH = os.path.join(VECTOR_STORE_DIR, "chunks.db")

# AST Parsing
USE_AST_PYTHON = True
USE_AST_JS = False
EXTRACT_CALLS = True
EXTRACT_DOCS = True

# Hybrid Retrieval
ENABLE_HYBRID_RETRIEVAL = True
BM25_TOP_K = 15
HYBRID_RRF_K = 60

# Query Classification
ENABLE_CLASSIFIER = True

# Context Expansion
CONTEXT_EXPANSION_ENABLED = True
CONTEXT_EXPANSION_DEPTH = 1
CONTEXT_MAX_ADDITIONS = 3

# Self-Reflection
ENABLE_REFLECTION = True
REFLECTION_MODEL = "openai/gpt-oss-120b:free"
REFLECTION_MAX_TOKENS = 600
REFLECTION_TEMPERATURE = 0.1

# Confidence Scoring
ENABLE_CONFIDENCE_SCORING = True

# ============================================================
# Scaling / Large Repo Support (5GB+)
# ============================================================

# Max file size to process (bytes) — 10MB allows large source files
# Binary files and generated artifacts are filtered separately
MAX_FILE_SIZE = 10 * 1024 * 1024

# Max total chunks: 0 means unlimited (use memory threshold instead)
# Remove the old 3000 hard cap
MAX_TOTAL_CHUNKS = 0

# FAISS index type: "flat" (IndexFlatL2, exact) or "ivf" (IndexIVFFlat, approximate)
# IVF is recommended for repos with >50k chunks (faster search, lower memory)
FAISS_INDEX_TYPE = "ivf"

# IVF parameters (only used when FAISS_INDEX_TYPE="ivf")
# nlist = number of centroids / Voronoi cells (sqrt(n) is a good rule of thumb)
# nprobe = number of cells to search at query time (higher = more accurate but slower)
IVF_NLIST = 4096
IVF_NPROBE = 10

# Whether to use memory-mapped FAISS index loading (reduces RAM usage)
# Requires FAISS >= 1.7.0
FAISS_USE_MMAP = True

# Memory threshold: fraction of total RAM to stay under during ingestion/embedding
# Set to 0.0 to disable memory monitoring
MEMORY_THRESHOLD = 0.75

# Chunk storage backend: "json" (legacy) or "sqlite" (recommended for large repos)
CHUNK_STORAGE_BACKEND = "sqlite"

# Embedding batch size — smaller values reduce peak RAM usage
EMBED_BATCH_SIZE_STREAMING = 128

# Max SQLite chunk rows to buffer before commit (for write performance)
SQLITE_BATCH_COMMIT = 500


# Attempt to compute a safe max chunk limit based on available memory
def _compute_max_chunks() -> int:
    """Return a reasonable upper bound on chunks based on available RAM."""
    try:
        import psutil
        available_gb = psutil.virtual_memory().available / (1024 ** 3)
        # Each chunk consumes ~1.5KB for content + ~1.5KB for embedding (384-dim float32)
        # Rough estimate: 1GB RAM ≈ 300k chunks
        safe_limit = int(available_gb * 200_000)
        return max(safe_limit, 50_000)
    except ImportError:
        return 0  # unlimited (no psutil available)


# Override MAX_TOTAL_CHUNKS if set to 0 (auto-detect)
if MAX_TOTAL_CHUNKS == 0:
    MAX_TOTAL_CHUNKS = _compute_max_chunks()
