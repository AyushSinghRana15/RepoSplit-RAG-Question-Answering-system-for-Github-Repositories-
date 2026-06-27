# utils.py — Shared helpers for ingestion: language detection, exclusion rules, path utilities

import os
import re
from pathlib import Path

from config import MAX_FILE_SIZE as CFG_MAX_FILE_SIZE

# Backward-compat alias used by loader.py
MAX_FILE_SIZE = CFG_MAX_FILE_SIZE

# Map file extensions to language identifiers
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".m": "objective-c",
    ".mm": "objective-c",
    ".cs": "csharp",
    ".r": "r",
    ".lua": "lua",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".sql": "sql",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".html": "html",
    ".htm": "html",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".md": "markdown",
    ".rst": "rst",
    ".txt": "text",
}

# Directories always skipped during repo walking
EXCLUDED_DIRS = {
    "node_modules", ".git", "venv", "__pycache__",
    "dist", "build", ".next", "output", "vector_store",
    ".venv", "env", ".env", ".tox", ".eggs", "eggs",
    "site-packages", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".hypothesis", ".coverage",
    "htmlcov", ".serverless", ".terraform",
    ".bazel", "bazel-out", ".dart_tool",
    "Pods", ".build", "DerivedData",
    ".gradle", "gradle", "target", "bin", "obj",
    ".stack-work", "_build", "deps",
    "third_party", "third-party", "vendor",
    ".svn", ".hg", ".DS_Store",
}

# Specific files always skipped
EXCLUDED_FILES = {
    ".env", ".env.example", ".env.local",
    ".DS_Store", "Thumbs.db",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Gemfile.lock", "Cargo.lock", "poetry.lock",
    ".gitignore", ".gitattributes",
}

# File extensions always skipped
EXCLUDED_EXTENSIONS = {
    ".lock", ".min.js", ".pyc", ".class", ".o", ".so",
    ".dll", ".dylib", ".lib", ".a", ".obj",
    ".exe", ".msi", ".bin", ".wasm",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".ico", ".webp", ".svg",
    ".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".webm",
    ".mp3", ".wav", ".flac", ".ogg", ".wma", ".aac", ".m4a",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".whl", ".egg", ".deb", ".rpm",
    ".pyo", ".pyd",
    ".DS_Store",
    ".min.css",
    ".map",
    ".pb", ".proto.bin",
}


def detect_language(file_path: str) -> str | None:
    ext = Path(file_path).suffix.lower()
    return LANGUAGE_MAP.get(ext)


def is_binary(path: str) -> bool:
    """Detect if a file is binary by checking for null bytes in the first 8KB."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
        return b"\0" in chunk
    except Exception:
        return True


def is_generated_or_vendor(path: str) -> bool:
    """Detect common generated/copied vendored code paths."""
    name = Path(path).name.lower()
    low_path = path.lower()
    generated_patterns = [
        "generated", "vendor/", "vendored",
        "pb.go", "_pb2.py", "_pb.py",
        ".grpc.pb", "autogen", "auto_gen",
        "migrations/", "alembic/",
    ]
    parts = Path(path).parts
    # Check for generated dirs in path
    for part in parts:
        pl = part.lower()
        if pl in {"generated", "vendor", "vendored", "third_party", "third-party",
                   "protobuf", "grpc-gen", "swagger", "openapi"}:
            return True
    for pat in generated_patterns:
        if pat in low_path:
            return True
    return False


def is_excluded(path: str) -> bool:
    parts = Path(path).parts
    for part in parts:
        if part in EXCLUDED_DIRS:
            return True
    name = os.path.basename(path)
    if name in EXCLUDED_FILES:
        return True
    ext = Path(path).suffix.lower()
    if ext in EXCLUDED_EXTENSIONS:
        return True
    return False


def should_process_file(file_path: str) -> bool:
    """Combined check: exclusion rules, binary detection, size limit, supported language."""
    if is_excluded(file_path):
        return False
    if is_generated_or_vendor(file_path):
        return False
    if detect_language(file_path) is None:
        return False
    if os.path.getsize(file_path) > CFG_MAX_FILE_SIZE:
        return False
    if is_binary(file_path):
        return False
    return True


def relative_path(full_path: str, repo_root: str) -> str:
    return os.path.relpath(full_path, repo_root)
