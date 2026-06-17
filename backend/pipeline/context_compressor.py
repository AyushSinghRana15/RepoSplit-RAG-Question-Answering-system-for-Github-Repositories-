from typing import List, Dict
from llm.context_builder import approx_tokens


MAX_CONTEXT_TOKENS = 6000


def compress_results(
    query: str,
    results: List[Dict],
    max_tokens: int = MAX_CONTEXT_TOKENS,
    max_chunks: int = 8,
) -> List[Dict]:
    if not results:
        return results

    scored = []
    for r in results:
        score = r.get("rerank_score") or (1.0 - min(r.get("score", 0) / 2.5, 1.0))
        tok_count = approx_tokens(r.get("content", ""))
        efficiency = score / max(tok_count, 1)
        scored.append((efficiency, score, r))

    scored.sort(key=lambda x: -x[0])

    compressed = []
    total_tokens = 0
    for _, _, r in scored:
        tok_count = approx_tokens(r.get("content", ""))
        if total_tokens + tok_count > max_tokens:
            continue
        if len(compressed) >= max_chunks:
            break
        compressed.append(r)
        total_tokens += tok_count

    if not compressed and results:
        compressed = results[:1]

    return compressed
