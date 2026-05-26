import re
from typing import Dict
from config import SCORE_THRESHOLD, ENABLE_CONFIDENCE_SCORING


def validate_answer(answer: str, results: list) -> Dict:
    """
    Checks if the answer's key claims appear in the retrieved chunks.
    Returns: {"is_grounded": bool, "confidence": float, "warning": str | None}
    """
    if not results:
        return {"is_grounded": True, "confidence": 1.0, "warning": None}

    known_names = set()
    for r in results:
        known_names.add(r["metadata"].get("name", "").lower())
        known_names.add(r["metadata"]["file_path"].lower())

    mentioned = re.findall(r'`(\w+)`', answer.lower())

    hallucinated = [m for m in mentioned if m not in known_names and len(m) > 3]

    if hallucinated:
        return {
            "is_grounded": False,
            "confidence": 0.4,
            "warning": f"Answer may reference unknown symbols: {hallucinated[:3]}"
        }
    return {"is_grounded": True, "confidence": 0.9, "warning": None}


def score_confidence(results: list, answer: str, intent: str) -> Dict:
    if not results:
        return {"level": "low", "score": 0.2, "message": "no_results"}

    best_score = min(r["score"] for r in results)   # L2 — lower = better
    rerank_top = results[0].get("rerank_score", 0)

    # Map to 0-1 confidence (relaxed threshold for all-MiniLM-L6-v2)
    l2_conf = max(0, 1 - (best_score / 2.5))     # 0 → 1.0, 2.5 → 0.0
    confidence = (l2_conf + min(rerank_top, 1)) / 2

    if confidence >= 0.5:
        level = "high"
    elif confidence >= 0.25:
        level = "medium"
    else:
        level = "low"

    return {"level": level, "score": round(confidence, 2), "message": None}


def shape_response(answer: str, confidence: dict, results: list) -> Dict:
    if confidence["level"] == "none":
        return {
            "answer": "I could not find this in the provided codebase.",
            "confidence": "none",
            "sources": []
        }

    if confidence["level"] == "low":
        top_files = list({r["metadata"]["file_path"] for r in results[:3]})
        disclaimer = f"\n\n❗ Low confidence. Potentially relevant files: {top_files}"
        return {
            "answer": answer + disclaimer,
            "confidence": "low",
            "sources": [
                {"file_path": r["metadata"]["file_path"], "name": r["metadata"].get("name", ""), "score": round(r.get("score", 0), 3)}
                for r in results[:3]
            ]
        }

    return {
        "answer": answer,
        "confidence": confidence["level"],
        "sources": [
            {"file_path": r["metadata"]["file_path"], "name": r["metadata"].get("name", ""), "score": round(r.get("score", 0), 3)}
            for r in results[:3]
        ]
    }
