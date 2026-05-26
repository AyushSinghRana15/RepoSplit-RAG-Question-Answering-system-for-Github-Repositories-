import os
import re
from pathlib import Path

LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
}

EXCLUDED_DIRS = {
    "node_modules", ".git", "venv", "__pycache__",
    "dist", "build", ".next", "output", "vector_store",
}

EXCLUDED_FILES = {
    ".env",
}

EXCLUDED_EXTENSIONS = {
    ".lock", ".min.js", ".pyc", ".class", ".o", ".so",
}

MAX_FILE_SIZE = 500 * 1024


def detect_language(file_path: str) -> str | None:
    ext = Path(file_path).suffix.lower()
    return LANGUAGE_MAP.get(ext)


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


def relative_path(full_path: str, repo_root: str) -> str:
    return os.path.relpath(full_path, repo_root)
