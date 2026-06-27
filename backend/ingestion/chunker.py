# chunker.py — Split source code into semantic chunks with overlap for context continuity

import re
import os
from typing import Generator, List

from ingestion.ast_parser import parse_python_ast

CHUNK_MAX_LINES = 150
CHUNK_OVERLAP_LINES = 3


def create_chunk(content, start_line, end_line, chunk_type, name, file_path, language, **extra):
    meta = {
        "file_path": file_path,
        "language": language,
        "chunk_type": chunk_type,
        "name": name,
        "start_line": start_line,
        "end_line": end_line,
        "char_count": len(content),
    }
    meta.update(extra)
    return {"content": content, "metadata": meta}


def split_large_chunk(content, start_line, chunk_type, name, file_path, language, **extra):
    lines = content.split('\n')
    total = len(lines)
    if total <= CHUNK_MAX_LINES:
        return [create_chunk(content, start_line, start_line + total - 1, chunk_type, name, file_path, language, **extra)]

    sub_chunks = []
    cur_start = start_line
    idx = 0
    part = 1
    while idx < total:
        end_idx = min(idx + CHUNK_MAX_LINES, total)
        sub = lines[idx:end_idx]
        sub_content = '\n'.join(sub)
        sub_end = cur_start + len(sub) - 1
        sub_name = f"{name}_part_{part}"
        sub_chunks.append(create_chunk(sub_content, cur_start, sub_end, chunk_type, sub_name, file_path, language, **extra))
        if end_idx >= total:
            break
        idx = end_idx - CHUNK_OVERLAP_LINES
        cur_start = sub_end - CHUNK_OVERLAP_LINES + 1
        part += 1
    return sub_chunks


def parse_chunks(file_content, file_path, language) -> List[dict]:
    if not file_content.strip():
        return []

    chunks = []
    if language == 'python':
        chunks = parse_python_ast(file_content, file_path)

    if not chunks:
        lines = file_content.split('\n')
        total_lines = len(lines)

        lang_patterns = {
            'javascript': [
                (re.compile(r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\('), 'function'),
                (re.compile(r'^(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s+)?\(.*?\)\s*=>'), 'function'),
                (re.compile(r'^(?:export\s+)?class\s+(\w+)'), 'class'),
            ],
            'typescript': [
                (re.compile(r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\('), 'function'),
                (re.compile(r'^(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s+)?\(.*?\)\s*=>'), 'function'),
                (re.compile(r'^(?:export\s+)?class\s+(\w+)'), 'class'),
            ],
        }

        patterns = lang_patterns.get(language, [])
        boundaries = []

        for i, line in enumerate(lines):
            line_no = i + 1
            for pat, ctype in patterns:
                m = pat.match(line)
                if m:
                    boundaries.append((line_no, ctype, m.group(1)))
                    break

        boundaries.sort(key=lambda x: x[0])

        if not boundaries:
            name = os.path.basename(file_path)
            chunks.append(create_chunk(file_content, 1, total_lines, 'file', name, file_path, language))
        else:
            for j, (start, ctype, name) in enumerate(boundaries):
                end = boundaries[j+1][0] - 1 if j + 1 < len(boundaries) else total_lines
                content = '\n'.join(lines[start-1:end])
                chunks.append(create_chunk(content, start, end, ctype, name, file_path, language))

    if language != 'python' and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = chunks[i - 1]
            curr = chunks[i]
            prev_lines = prev["content"].split('\n')
            overlap_lines = prev_lines[-CHUNK_OVERLAP_LINES:] if len(prev_lines) >= CHUNK_OVERLAP_LINES else prev_lines
            curr["content"] = '\n'.join(overlap_lines) + '\n' + curr["content"]
            curr["metadata"]["start_line"] = max(1, curr["metadata"]["start_line"] - CHUNK_OVERLAP_LINES)
            curr["metadata"]["char_count"] = len(curr["content"])
            overlapped.append(curr)
        chunks = overlapped

    processed_chunks = []
    for c in chunks:
        content = c["content"]
        line_count = content.count('\n') + 1
        if line_count > CHUNK_MAX_LINES:
            meta = c["metadata"]
            extra = {k: v for k, v in meta.items() if k not in ["file_path", "language", "chunk_type", "name", "start_line", "end_line", "char_count"]}
            split_chunks = split_large_chunk(
                content=content,
                start_line=meta["start_line"],
                chunk_type=meta["chunk_type"],
                name=meta["name"],
                file_path=meta["file_path"],
                language=meta["language"],
                **extra
            )
            processed_chunks.extend(split_chunks)
        else:
            processed_chunks.append(c)

    final_chunks = [c for c in processed_chunks if len(c["content"]) >= 30]
    return final_chunks


def parse_chunks_streaming(file_content, file_path, language) -> Generator[dict, None, None]:
    """Generator variant of parse_chunks — yields chunks one at a time to reduce memory pressure."""
    chunks = parse_chunks(file_content, file_path, language)
    for c in chunks:
        yield c
