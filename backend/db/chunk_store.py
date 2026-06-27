# chunk_store.py — SQLite-backed chunk storage for streaming access
# Avoids loading all chunks into RAM at once (critical for 5GB+ repos)

import json
import os
import sqlite3
import time
from contextlib import closing
from typing import Any, Dict, Generator, Iterator, List, Optional, Tuple

from config import CHUNK_DB_PATH, SQLITE_BATCH_COMMIT

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content     TEXT    NOT NULL,
    file_path   TEXT    NOT NULL,
    language    TEXT,
    chunk_type  TEXT,
    name        TEXT,
    start_line  INTEGER,
    end_line    INTEGER,
    char_count  INTEGER,
    calls       TEXT,
    decorators  TEXT,
    docstring   TEXT,
    is_async    INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_chunks_file_path ON chunks(file_path);
CREATE INDEX IF NOT EXISTS idx_chunks_language ON chunks(language);
"""


def _dict_to_row(chunk: dict) -> Tuple:
    m = chunk.get("metadata", {})
    return (
        chunk["content"],
        m.get("file_path", ""),
        m.get("language"),
        m.get("chunk_type"),
        m.get("name"),
        m.get("start_line"),
        m.get("end_line"),
        m.get("char_count"),
        json.dumps(m.get("calls", [])),
        json.dumps(m.get("decorators", [])),
        m.get("docstring"),
        1 if m.get("is_async") else 0,
    )


def _row_to_chunk(row: sqlite3.Row) -> dict:
    metadata = {
        "file_path": row["file_path"],
        "language": row["language"],
        "chunk_type": row["chunk_type"],
        "name": row["name"],
        "start_line": row["start_line"],
        "end_line": row["end_line"],
        "char_count": row["char_count"],
    }
    if row["calls"]:
        metadata["calls"] = json.loads(row["calls"])
    if row["decorators"]:
        metadata["decorators"] = json.loads(row["decorators"])
    if row["docstring"]:
        metadata["docstring"] = row["docstring"]
    if row["is_async"]:
        metadata["is_async"] = True
    return {"content": row["content"], "metadata": metadata}


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(CHUNK_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(CHUNK_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA cache_size=-64000")
    return conn


def init_db():
    with closing(get_connection()) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


def insert_chunks(chunks: List[dict], conn: Optional[sqlite3.Connection] = None):
    """Insert chunks into the database. Accepts optional connection for batched use."""
    if conn is None:
        own_conn = True
        conn = get_connection()
    else:
        own_conn = False

    try:
        rows = [_dict_to_row(c) for c in chunks]
        conn.executemany(
            """INSERT INTO chunks
               (content, file_path, language, chunk_type, name,
                start_line, end_line, char_count, calls, decorators,
                docstring, is_async)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )
        conn.commit()
    finally:
        if own_conn:
            conn.close()


def stream_chunks(batch_size: int = 1000) -> Generator[List[dict], None, None]:
    """Yield chunks in batches from SQLite, without loading all into RAM."""
    with closing(get_connection()) as conn:
        cursor = conn.execute("SELECT * FROM chunks ORDER BY id")
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            yield [_row_to_chunk(r) for r in rows]


def stream_chunks_raw(batch_size: int = 1000) -> Generator[List[sqlite3.Row], None, None]:
    """Yield raw sqlite3.Row batches (lower overhead for embedding)."""
    with closing(get_connection()) as conn:
        cursor = conn.execute("SELECT id, content, file_path, language, chunk_type, name, start_line, end_line, char_count FROM chunks ORDER BY id")
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            yield rows


def count_chunks() -> int:
    with closing(get_connection()) as conn:
        return conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]


def get_all_chunks() -> List[dict]:
    """Load ALL chunks into memory. Use only when necessary (e.g. BM25 build)."""
    with closing(get_connection()) as conn:
        rows = conn.execute("SELECT * FROM chunks ORDER BY id").fetchall()
    return [_row_to_chunk(r) for r in rows]


def get_chunk_by_id(chunk_id: int) -> Optional[dict]:
    with closing(get_connection()) as conn:
        row = conn.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
    return _row_to_chunk(row) if row else None


def get_chunks_by_ids(ids: List[int]) -> List[dict]:
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    with closing(get_connection()) as conn:
        rows = conn.execute(f"SELECT * FROM chunks WHERE id IN ({placeholders}) ORDER BY id", ids).fetchall()
    return [_row_to_chunk(r) for r in rows]


def clear_db():
    """Drop all chunks (for re-ingestion)."""
    with closing(get_connection()) as conn:
        conn.execute("DROP TABLE IF EXISTS chunks")
        conn.commit()


def get_chunk_iterator_for_embedding(batch_size: int = 1000) -> Generator:
    """Yield (chunk_id, embed_text) tuples for embedding pipeline."""
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            "SELECT id, content, file_path, language, chunk_type, name FROM chunks ORDER BY id"
        )
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            batch = []
            for row in rows:
                header = f"[{row['language']}] {row['chunk_type']}: {row['name']} in {row['file_path']}"
                embed_text = f"{header}\n\n{row['content']}"
                batch.append((row["id"], embed_text))
            yield batch
