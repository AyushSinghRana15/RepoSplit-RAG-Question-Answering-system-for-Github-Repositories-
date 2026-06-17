import re
from typing import Dict, List

INTENT_RULES: List[tuple] = [
    (["where is", "which file", "find", "locate", "path", "directory", "file"], "location"),
    (["how does", "explain the flow", "walk me through", "sequence", "step"], "flow"),
    (["what does", "what is", "describe", "tell me about", "what are"], "explanation"),
    (["why does", "why is", "what causes", "error", "bug", "crash", "fail", "issue", "fix"], "debug"),
    (["summarize", "overview", "architecture", "structure", "high-level", "design"], "general"),
    (["compare", "difference", "vs", "versus", "verses"], "comparison"),
    (["list", "show all", "enumerate", "all the", "every"], "enumeration"),
]

CODE_KEYWORD_WEIGHTS = {
    "location": {"func": 2, "function": 2, "def": 2, "class": 2, "method": 2, "file": 3, "where": 1},
    "debug": {"error": 3, "bug": 3, "crash": 3, "fix": 3, "issue": 3, "why": 1, "cause": 2, "problem": 2},
    "flow": {"flow": 3, "call": 2, "sequence": 2, "order": 1, "process": 1, "how": 1},
    "explanation": {"what": 1, "explain": 2, "describe": 2, "purpose": 2, "meaning": 2, "define": 2},
}


def classify_query(query: str) -> str:
    q = query.lower()

    scores: Dict[str, int] = {"location": 0, "flow": 0, "explanation": 0, "debug": 0, "comparison": 0, "enumeration": 0, "general": 0}

    for patterns, intent in INTENT_RULES:
        if any(p in q for p in patterns):
            scores[intent] += 2

    for intent, keywords in CODE_KEYWORD_WEIGHTS.items():
        for word, weight in keywords.items():
            if word in q:
                scores[intent] += weight

    q_words = set(q.split())
    for intent, keywords in CODE_KEYWORD_WEIGHTS.items():
        overlap = q_words & set(keywords.keys())
        if overlap:
            scores[intent] += len(overlap)

    max_score = max(scores.values())
    if max_score == 0:
        return "general"

    best_intents = [i for i, s in scores.items() if s == max_score]
    return best_intents[0] if best_intents else "general"


def get_pipeline_config(intent: str) -> Dict:
    configs = {
        "location":    {"top_k": 20, "bm25_weight": 0.7, "max_additions": 1, "num_variations": 2},
        "flow":        {"top_k": 15, "bm25_weight": 0.3, "max_additions": 5, "num_variations": 3},
        "explanation": {"top_k": 12, "bm25_weight": 0.4, "max_additions": 3, "num_variations": 2},
        "debug":       {"top_k": 18, "bm25_weight": 0.6, "max_additions": 4, "num_variations": 3},
        "comparison":  {"top_k": 20, "bm25_weight": 0.5, "max_additions": 4, "num_variations": 3},
        "enumeration": {"top_k": 25, "bm25_weight": 0.5, "max_additions": 2, "num_variations": 1},
        "general":     {"top_k": 10, "bm25_weight": 0.3, "max_additions": 2, "num_variations": 1},
    }
    return configs.get(intent, configs["general"])
