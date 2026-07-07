# test_chunking.py — Unit tests for chunk content, metadata structure, and formatting

import json
import os
import pytest

CHUNKS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "output", "chunks.json")
KNOWN_LANGUAGES = {
    "python", "javascript", "typescript", "java", "go", "ruby", "c", "cpp",
    "rust", "php", "swift", "kotlin", "markdown", "text", "json", "yaml",
    "html", "css", "shell", "dockerfile"
}
CHUNK_TYPES = {"function", "class", "file"}
METADATA_KEYS = ["file_path", "language", "chunk_type", "name", "start_line", "end_line", "char_count"]


# Load all chunks from the JSON file once per test session
@pytest.fixture(scope="module")
def chunks():
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# Verify every chunk has non-empty string content
def test_has_content(chunks):
    for c in chunks:
        assert isinstance(c.get("content"), str) and len(c["content"].strip()) > 0


# Check that all required metadata keys exist on every chunk
def test_has_all_metadata_keys(chunks):
    for c in chunks:
        m = c.get("metadata", {})
        for key in METADATA_KEYS:
            assert key in m, f"Missing key '{key}' in {m.get('name', '?')}"


# Ensure file_path values are relative (never absolute paths)
def test_file_path_is_relative(chunks):
    for c in chunks:
        fp = c["metadata"]["file_path"]
        assert not os.path.isabs(fp), f"Absolute path found: {fp}"


# Verify every chunk has a recognized language identifier
def test_language_is_known(chunks):
    for c in chunks:
        lang = c["metadata"]["language"]
        assert lang in KNOWN_LANGUAGES, f"Unknown language: {lang}"


# Verify every chunk has a valid chunk_type (function, class, or file)
def test_chunk_type_is_valid(chunks):
    for c in chunks:
        ct = c["metadata"]["chunk_type"]
        assert ct in CHUNK_TYPES, f"Invalid chunk_type: {ct}"


# Reject chunks with fewer than 30 characters
def test_no_tiny_chunks(chunks):
    for c in chunks:
        assert c["metadata"]["char_count"] >= 30, f"Tiny chunk: {c['metadata']['name']}"


# Reject chunks exceeding 160 lines
def test_no_huge_chunks(chunks):
    for c in chunks:
        line_count = c["content"].count("\n") + 1
        assert line_count <= 160, f"Huge chunk: {c['metadata']['name']} ({line_count} lines)"


# Python function chunks must start with "def " or "async def "
def test_function_starts_with_def(chunks):
    for c in chunks:
        m = c["metadata"]
        if m["chunk_type"] == "function" and m["language"] == "python":
            content = c["content"].strip()
            assert content.startswith(("def ", "async def ")), f"Function {m['name']} doesn't start with def"


# Class chunks must start with "class "
def test_class_starts_with_class(chunks):
    for c in chunks:
        m = c["metadata"]
        if m["chunk_type"] == "class":
            content = c["content"].strip()
            assert content.startswith("class "), f"Class {m['name']} doesn't start with class"
