import os
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

def clone_github_repo(repo_url: str, branch: Optional[str] = None) -> str:
    """
    Clone a GitHub repository to a temporary directory.
    Returns the path to the cloned repository.
    """
    temp_dir = tempfile.mkdtemp(prefix="codebase_github_")

    cmd = ["git", "clone", "--depth", "1", "--single-branch"]
    if branch:
        cmd.extend(["--branch", branch])
    cmd.extend([repo_url, temp_dir])

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=180)
        return temp_dir
    except subprocess.CalledProcessError as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise Exception(f"Failed to clone repository: {e.stderr.decode()}")
    except subprocess.TimeoutExpired:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise Exception("Git clone timed out after 180 seconds. Try a smaller repo or a specific branch.")

def ingest_github_repo(repo_url: str, branch: Optional[str] = None) -> List[str]:
    """
    Clone a GitHub repo and return list of supported file paths.
    Skips dataset files and non-code directories.
    """
    repo_path = clone_github_repo(repo_url, branch)

    supported_extensions = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c',
        '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.md', '.txt'
    }

    skip_dirs = {
        '.git', 'node_modules', '__pycache__', 'venv', '.venv',
        'data', 'datasets', 'dataset', 'assets', 'static',
        'models', 'checkpoints', 'weights', '.ipynb_checkpoints',
        'dist', 'build', '.tox', '.mypy_cache', '.pytest_cache',
        '.next', '.turbo', 'out', '.cache', 'coverage', '.vercel',
        '.serverless_micro', 'public', 'output', 'vector_store',
    }

    skip_extensions = {
        '.csv', '.tsv', '.jsonl', '.parquet', '.pickle', '.pkl',
        '.h5', '.hdf5', '.npy', '.npz', '.bin', '.dat', '.db',
        '.sqlite', '.sqlite3', '.arrow', '.feather',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
        '.mp4', '.avi', '.mov', '.mp3', '.wav',
        '.pth', '.pt', '.onnx', '.pb', '.tflite', '.gguf',
        '.zip', '.tar', '.gz', '.bz2', '.rar', '.7z',
        '.xlsx', '.xls', '.ods',
        '.ipynb',
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
    """Clean up cloned repository."""
    shutil.rmtree(repo_path, ignore_errors=True)
