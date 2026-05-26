import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict

CHUNKS_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "chunks.json")
QUERIES_PATH = os.path.join(os.path.dirname(__file__), "..", "eval", "test_queries.json")
SCORE_THRESHOLD = 1.4


def load_chunks():
    import json
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_queries():
    import json
    with open(QUERIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def retriever(query: str, top_k: int = 5) -> List[Dict]:
    """
    Retriever using FAISS vector search.
    Returns list of dicts with 'chunk' and 'score' keys.
    """
    from embeddings.retriever import retrieve
    results = retrieve(query, top_k=top_k, score_threshold=SCORE_THRESHOLD)
    return [{"chunk": r["metadata"], "score": r["score"]} for r in results if r["score"] <= SCORE_THRESHOLD]


def run_retrieval_tests():
    queries = load_queries()
    print(f"Loaded {len(queries)} test queries\n")

    for q in queries:
        query = q["query"]
        expected_file = q.get("expected_file_hint")
        expected_name = q.get("expected_name_hint")
        expect_empty = q.get("expect_empty", False)

        print(f'Query: "{query}"')
        print("-" * 50)

        results = retriever(query, top_k=5)

        if expect_empty:
            if not results:
                print("Result: ✅ PASS (no relevant results as expected)\n")
                continue
            else:
                print("Result: ❌ FAIL (expected empty but got results)\n")
                continue

        for i, r in enumerate(results[:3], 1):
            chunk = r["chunk"]
            print(f"  #{i}  {chunk['file_path']} :: {chunk['name']}  [L2: {r['score']:.4f}]")

        passed = False
        if expected_file:
            for r in results:
                if expected_file.lower() in r["chunk"]["file_path"].lower():
                    passed = True
                    break
        if expected_name and not passed:
            for r in results:
                if expected_name.lower() in r["chunk"]["name"].lower():
                    passed = True
                    break
        if not expected_file and not expected_name:
            passed = len(results) > 0

        print(f"Result: {'✅ PASS' if passed else '❌ FAIL'}")
        print()


if __name__ == "__main__":
    run_retrieval_tests()
