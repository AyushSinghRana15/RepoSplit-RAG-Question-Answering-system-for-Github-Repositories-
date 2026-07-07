# chunker.py — Split source code into semantic chunks preserving logical boundaries

import re
import os
from typing import Generator, List

import config
from ingestion.ast_parser import parse_python_ast

MAX_LINES = config.CHUNK_MAX_LINES
OVERLAP = config.CHUNK_OVERLAP_LINES
MIN_CHARS = config.CHUNK_MIN_CHARS


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


def _extract_header_lines(source_code: str) -> tuple[list[str], int]:
    """Return (header_lines, count) — the function/class signature line(s) to prepend for context."""
    lines = source_code.split('\n')
    end = 0
    for line in lines:
        stripped = line.strip()
        if stripped == '' or stripped.startswith('@'):
            end += 1
        else:
            break
    for i in range(end, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith(('def ', 'class ', 'async def ')):
            end = i + 1
            break
    for i in range(end, len(lines)):
        stripped = lines[i].strip()
        if stripped in ('"""', "'''"):
            end = i + 1
            if stripped in ('"""', "'''"):
                for j in range(i + 1, len(lines)):
                    end = j + 1
                    if lines[j].strip() == stripped:
                        break
            continue
        if stripped == '':
            end = i + 1
        else:
            break
    return lines[:end], end


def _find_split_idx(lines_0idx: list[str], start: int, max_lines: int) -> int:
    """Find best 0-indexed split position near start+max_lines (prefer blank lines)."""
    target = start + max_lines
    if target >= len(lines_0idx):
        return len(lines_0idx)
    window = min(10, max(1, max_lines // 3))
    lo = max(start + 1, target - window)
    for i in range(target, lo - 1, -1):
        if i < len(lines_0idx) and lines_0idx[i].strip() == '':
            return i + 1
    ref_indent = len(lines_0idx[start]) - len(lines_0idx[start].lstrip())
    for i in range(target, lo - 1, -1):
        stripped = lines_0idx[i].strip()
        if stripped and not stripped.startswith(('#', '//', '/*', '*', '"""', "'''", '@')):
            if len(lines_0idx[i]) - len(lines_0idx[i].lstrip()) <= ref_indent and i > start:
                return i
    return target


def split_large_chunk(content, start_line, chunk_type, name, file_path, language, **extra):
    lines = content.split('\n')
    total = len(lines)
    if total <= MAX_LINES:
        return [create_chunk(content, start_line, start_line + total - 1, chunk_type, name, file_path, language, **extra)]

    header_lines, hdr_count = _extract_header_lines(content)

    sub_chunks = []
    idx = 0
    part = 1
    cur_start = start_line

    while idx < total:
        split_at = _find_split_idx(lines, idx, MAX_LINES)
        split_at = min(split_at, total)

        sub = lines[idx:split_at]
        sub_content = '\n'.join(sub)
        sub_end = cur_start + len(sub) - 1
        sub_name = f"{name}_part_{part}"

        if part > 1 and header_lines:
            header_text = '\n'.join(header_lines)
            sub_content = header_text + '\n' + sub_content

        sub_chunks.append(create_chunk(sub_content, cur_start, sub_end, chunk_type, sub_name, file_path, language, **extra))

        if split_at >= total:
            break
        idx = split_at - OVERLAP
        cur_start = max(cur_start, sub_end - OVERLAP + 1)
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
            overlap_lines = prev_lines[-OVERLAP:] if len(prev_lines) >= OVERLAP else prev_lines
            curr["content"] = '\n'.join(overlap_lines) + '\n' + curr["content"]
            curr["metadata"]["start_line"] = max(1, curr["metadata"]["start_line"] - OVERLAP)
            curr["metadata"]["char_count"] = len(curr["content"])
            overlapped.append(curr)
        chunks = overlapped

    processed_chunks = []
    for c in chunks:
        content_str = c["content"]
        line_count = content_str.count('\n') + 1
        if line_count > MAX_LINES:
            meta = c["metadata"]
            extra = {k: v for k, v in meta.items() if k not in ["file_path", "language", "chunk_type", "name", "start_line", "end_line", "char_count"]}
            split_chunks = split_large_chunk(
                content=content_str,
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

    final_chunks = [c for c in processed_chunks if len(c["content"]) >= MIN_CHARS]
    return final_chunks


def parse_chunks_streaming(file_content, file_path, language) -> Generator[dict, None, None]:
    """Generator variant of parse_chunks — yields chunks one at a time to reduce memory pressure."""
    chunks = parse_chunks(file_content, file_path, language)
    for c in chunks:
        yield c
