"""Integration test for 5GB+ repo support: SQLite chunk store, IVF index, streaming."""

import os
import sys
import tempfile
import shutil

import pytest


def test_sqlite_chunk_store():
    """Test SQLite chunk storage with streaming reads/writes."""
    from db.chunk_store import init_db, insert_chunks, count_chunks, stream_chunks, clear_db, get_all_chunks, get_chunks_by_ids

    tmpdir = tempfile.mkdtemp()

    import config
    config.CHUNK_DB_PATH = os.path.join(tmpdir, "test.db")

    # Reload chunk_store so it picks up the overridden path
    if "db.chunk_store" in sys.modules:
        del sys.modules["db.chunk_store"]
    from db.chunk_store import init_db, insert_chunks, count_chunks, stream_chunks, clear_db, get_all_chunks, get_chunks_by_ids

    init_db()

    chunks = [
        {"content": f"chunk {i}", "metadata": {
            "file_path": "test.py", "language": "python",
            "chunk_type": "function", "name": f"func_{i}",
            "start_line": i, "end_line": i + 1, "char_count": 10,
        }}
        for i in range(100)
    ]
    insert_chunks(chunks)
    assert count_chunks() == 100

    # Test streaming
    total = 0
    for batch in stream_chunks(batch_size=10):
        for c in batch:
            assert c["metadata"]["chunk_type"] == "function"
            total += 1
    assert total == 100

    # Test get_by_ids
    by_ids = get_chunks_by_ids([1, 2, 3])
    assert len(by_ids) == 3

    # Test get_all
    all_c = get_all_chunks()
    assert len(all_c) == 100

    clear_db()
    init_db()
    assert count_chunks() == 0

    shutil.rmtree(tmpdir)
    print("test_sqlite_chunk_store: PASSED")


def test_large_file_filtering():
    """Test that binary files and oversized files are skipped."""
    from ingestion.utils import is_binary, is_excluded, should_process_file, is_generated_or_vendor

    tmpdir = tempfile.mkdtemp()

    # Binary file test
    bin_path = os.path.join(tmpdir, "test.bin")
    with open(bin_path, "wb") as f:
        f.write(b"hello\x00world")
    assert is_binary(bin_path)

    # Text file test
    txt_path = os.path.join(tmpdir, "test.py")
    with open(txt_path, "w") as f:
        f.write("print('hello')")
    assert not is_binary(txt_path)

    # Generated/vendor detection
    vendor_path = os.path.join(tmpdir, "vendor", "lib.py")
    os.makedirs(os.path.dirname(vendor_path))
    with open(vendor_path, "w") as f:
        f.write("def lib_func(): pass")
    assert is_generated_or_vendor(vendor_path)

    shutil.rmtree(tmpdir)
    print("test_large_file_filtering: PASSED")


def test_faiss_ivf_index():
    """Test IVF FAISS index creation and search."""
    import numpy as np
    import faiss

    np.random.seed(42)
    dim = 384
    n = 10000
    embeddings = np.random.rand(n, dim).astype("float32")

    from embeddings.embedder import _build_faiss_index
    index = _build_faiss_index(embeddings, "ivf")
    assert index.ntotal == n
    assert hasattr(index, "nprobe")
    assert index.is_trained

    # Test search works
    query = np.random.rand(1, dim).astype("float32")
    distances, indices = index.search(query, 5)
    assert len(indices[0]) == 5

    # Flat index should still work too
    index_flat = _build_faiss_index(embeddings, "flat")
    assert index_flat.ntotal == n

    print("test_faiss_ivf_index: PASSED")


def test_memory_threshold():
    """Test that memory threshold config works correctly."""
    from config import MEMORY_THRESHOLD, _compute_max_chunks

    assert MEMORY_THRESHOLD > 0
    max_chunks = _compute_max_chunks()
    assert max_chunks > 0
    print(f"Auto-computed max chunks: {max_chunks}")
    print("test_memory_threshold: PASSED")


def test_chunker_streaming():
    """Test the streaming chunk generator."""
    from ingestion.chunker import parse_chunks_streaming

    content = (
        "def foo():\n"
        '    """Some docstring to make this chunk long enough."""\n'
        "    return 42\n"
        "\n"
        "def bar():\n"
        '    """Another docstring to ensure the chunk passes the 30-char filter."""\n'
        "    return 100\n"
    )
    count = 0
    for chunk in parse_chunks_streaming(content, "test.py", "python"):
        count += 1
        assert "content" in chunk
        assert "metadata" in chunk
    assert count > 0

    print("test_chunker_streaming: PASSED")
