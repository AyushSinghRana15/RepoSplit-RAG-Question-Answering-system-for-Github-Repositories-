# github_ingestor.py — Clone GitHub repos and list supported source files

import os
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional


def clone_github_repo(repo_url: str, branch: Optional[str] = None) -> str:
    temp_dir = tempfile.mkdtemp(prefix="codebase_github_")

    cmd = ["git", "clone", "--depth", "1", "--single-branch"]
    if branch:
        cmd.extend(["--branch", branch])
    cmd.extend([repo_url, temp_dir])

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
        return temp_dir
    except subprocess.CalledProcessError as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise Exception(f"Failed to clone repository: {e.stderr.decode()}")
    except subprocess.TimeoutExpired:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise Exception("Git clone timed out after 600 seconds. Try a smaller repo or a specific branch.")


def ingest_github_repo(repo_url: str, branch: Optional[str] = None) -> List[str]:
    repo_path = clone_github_repo(repo_url, branch)

    supported_extensions = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c',
        '.h', '.hpp', '.go', '.rs', '.rb', '.php', '.swift', '.kt',
        '.scala', '.cs', '.sh', '.bash', '.zsh', '.sql', '.css',
        '.scss', '.less', '.html', '.htm', '.xml', '.yaml', '.yml',
        '.toml', '.json', '.md', '.rst', '.txt',
    }

    skip_dirs = {
        '.git', 'node_modules', '__pycache__', 'venv', '.venv',
        'data', 'datasets', 'dataset', 'assets', 'static',
        'models', 'checkpoints', 'weights', '.ipynb_checkpoints',
        'dist', 'build', '.tox', '.mypy_cache', '.pytest_cache',
        '.next', '.turbo', 'out', '.cache', 'coverage', '.vercel',
        '.serverless_micro', 'public', 'output', 'vector_store',
        '.terraform', 'Pods', '.gradle', 'target', 'bin', 'obj',
        'vendor', 'third_party', 'third-party', '.bazel',
        'site-packages', '.eggs', 'eggs', '.dart_tool',
    }

    skip_extensions = {
        '.csv', '.tsv', '.jsonl', '.parquet', '.pickle', '.pkl',
        '.h5', '.hdf5', '.npy', '.npz', '.bin', '.dat', '.db',
        '.sqlite', '.sqlite3', '.arrow', '.feather',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
        '.mp4', '.avi', '.mov', '.mp3', '.wav', '.flac', '.ogg',
        '.pth', '.pt', '.onnx', '.pb', '.tflite', '.gguf',
        '.zip', '.tar', '.gz', '.bz2', '.rar', '.7z',
        '.xlsx', '.xls', '.ods', '.docx', '.pdf',
        '.ipynb', '.whl', '.egg', '.deb', '.rpm',
        '.so', '.dll', '.dylib', '.class', '.pyc', '.pyo',
    }

    files = []
    for file_path in Path(repo_path).rglob("*"):
        if not file_path.is_file():
            continue

        parts = file_path.relative_to(repo_path).parts
        if any(p in skip_dirs for p in parts):
            continue

        if file_path.suffix in skip_extensions:
            continue

        if file_path.suffix in supported_extensions:
            files.append(str(file_path))

    return files


def cleanup_repo(repo_path: str):
    shutil.rmtree(repo_path, ignore_errors=True)
