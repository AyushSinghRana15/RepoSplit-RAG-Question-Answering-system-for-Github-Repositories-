import argparse
import json
import os
from collections import Counter

from ingestion.loader import walk_repo, read_file
from ingestion.chunker import parse_chunks


def run_ingestion(repo_path, output_path):
    repo_path = os.path.abspath(repo_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Use SQLite for large repos, JSON for small ones
    import config
    from db.chunk_store import init_db, insert_chunks, count_chunks, clear_db, get_connection
    from config import SQLITE_BATCH_COMMIT, MAX_TOTAL_CHUNKS

    total_chunks = 0
    files_processed = 0
    buffer = []

    clear_db()
    init_db()
    conn = get_connection()

    try:
        for full_path, rel_path, language in walk_repo(repo_path):
            content = read_file(full_path)
            if content is None:
                continue
            chunks = parse_chunks(content, rel_path, language)
            if not chunks:
                continue

            buffer.extend(chunks)
            if len(buffer) >= SQLITE_BATCH_COMMIT:
                insert_chunks(buffer, conn)
                total_chunks += len(buffer)
                buffer = []
            files_processed += 1

            if MAX_TOTAL_CHUNKS > 0 and total_chunks >= MAX_TOTAL_CHUNKS:
                break

        if buffer:
            insert_chunks(buffer, conn)
            total_chunks += len(buffer)
            buffer = []
    finally:
        conn.close()

    total = count_chunks()
    all_chunks = []
    if total <= 50000:
        from db.chunk_store import get_all_chunks
        all_chunks = get_all_chunks()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    type_counts = Counter(c["metadata"]["chunk_type"] for c in all_chunks) if all_chunks else {}
    lang_counts = Counter(c["metadata"]["language"] for c in all_chunks) if all_chunks else {}

    print("Ingestion complete")
    print(f"  Files processed : {files_processed}")
    print(f"  Total chunks    : {total}")
    print(f"  By type         : {', '.join(f'{k}={v}' for k, v in type_counts.items())}")
    print(f"  Languages       : {', '.join(f'{k}={v}' for k, v in lang_counts.items())}")
    print(f"  Output          : {output_path}")
    if total > 50000:
        print(f"  (Large repo: chunks stored in SQLite at vector_store/chunks.db)")


def run_embedding():
    from embeddings.embedder import embed_chunks
    embed_chunks()


def run_query(query):
    from embeddings.retriever import retrieve
    print(f'Query: "{query}"')
    print("-" * 40)
    results = retrieve(query, top_k=5)
    for i, r in enumerate(results[:3], 1):
        m = r["metadata"]
        print(f"  #{i}  {m['file_path']} :: {m['name']}  [L2: {r['score']}]")
    print("-" * 40)


def run_ask(query):
    from pipeline.ask import ask
    result = ask(query, top_k=5)

    print(f'Query: "{query}"')
    print("-" * 40)
    print("Answer:")
    print(result["answer"])
    if result["sources"]:
        print("\nSources Used:")
        for s in result["sources"]:
            print(f"  • {s['file_path']} :: {s['name']}  [score: {s['score']}]")
    print(f"\nRetrieved {result['retrieved_count']} chunks")
    print("-" * 40)


def run_egg():
    print("  🥚  🥚  🥚  🥚  🥚")
    print("  🥚             🥚")
    print("  🥚   Ayush    🥚")
    print("  🥚   Singh    🥚")
    print("  🥚             🥚")
    print("  🥚  🥚  🥚  🥚  🥚")


def main():
    parser = argparse.ArgumentParser(description="CodeBase AI Assistant")
    parser.add_argument("--repo", help="Path to the repo to ingest (Step 1)")
    parser.add_argument("--output", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "chunks.json"), help="Output JSON file path")
    parser.add_argument("--embed", action="store_true", help="Run embedding step (Step 2)")
    parser.add_argument("--query", help="Test retrieval with a query")
    parser.add_argument("--ask", help="Ask a question (Step 3: LLM-powered)")
    parser.add_argument("--egg", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.egg:
        run_egg()
        return
    if args.repo:
        run_ingestion(args.repo, args.output)
    if args.embed:
        run_embedding()
    if args.query:
        run_query(args.query)
    if args.ask:
        run_ask(args.ask)
    if not any([args.repo, args.embed, args.query, args.ask]):
        parser.print_help()


if __name__ == "__main__":
    main()
