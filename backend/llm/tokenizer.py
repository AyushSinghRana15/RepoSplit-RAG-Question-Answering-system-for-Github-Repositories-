# tokenizer.py — Token counting and truncation with tiktoken fallback

import os
from typing import Optional

_ENCODING = None
_MODEL_ENCODING = None
_MODEL_NAME = "qwen3-coder"


# Get tiktoken encoding for the model, with fallback to o200k_base
def _get_encoding():
    global _ENCODING
    if _ENCODING is not None:
        return _ENCODING
    try:
        import tiktoken
        _ENCODING = tiktoken.encoding_for_model(_MODEL_NAME)
    except (ImportError, KeyError):
        try:
            import tiktoken
            _ENCODING = tiktoken.get_encoding("o200k_base")
        except ImportError:
            _ENCODING = None
    return _ENCODING


# Count the number of tokens in text (approximate fallback when tiktoken unavailable)
def count_tokens(text: str) -> int:
    encoding = _get_encoding()
    if encoding is not None:
        return len(encoding.encode(text, disallowed_special=()))
    return len(text) // 4


# Truncate text to fit within max_tokens (approximate char fallback if tiktoken missing)
def truncate_to_tokens(text: str, max_tokens: int) -> str:
    if max_tokens <= 0:
        return ""
    encoding = _get_encoding()
    if encoding is not None:
        tokens = encoding.encode(text, disallowed_special=())
        if len(tokens) <= max_tokens:
            return text
        return encoding.decode(tokens[:max_tokens])
    lines = text.split('\n')
    estimated_chars = max_tokens * 4
    result = []
    char_count = 0
    for line in lines:
        if char_count + len(line) + 1 > estimated_chars:
            break
        result.append(line)
        char_count += len(line) + 1
    return '\n'.join(result)
