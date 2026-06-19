# CodeBase AI Assistant

> Ask natural language questions about any codebase. Get code-grounded answers with file citations.
>
> **Live demo:** [https://codebase-ai-assistant.vercel.app](https://codebase-ai-assistant.vercel.app)

## Architecture

```
User Query → Spell Check → LLM Query Rewrite → Query Classification → Weighted Hybrid Retrieval (FAISS + BM25) → Rerank → MMR Diversify → Context Assembly (tiktoken) → LLM Generate → Validate → API Response
                                                                  ↓
                                              FAISS Vector Store + BM25 Index (case-aware) + Dependency Graph
```

### Frontend (New!)
```
Browser → Next.js Frontend (localhost:3000) → API Proxy → FastAPI Backend (localhost:8000) → RAG Pipeline → Answer + Sources
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 16, TypeScript, Tailwind CSS v4, shadcn/ui |
| **Ingestion** | Python, AST parser, code-aware chunker with overlapping windows |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2, 384d) |
| **Vector Store** | FAISS (IndexFlatL2) + BM25 (case-aware) |
| **Hybrid Retrieval** | FAISS semantics + BM25 exact match, weighted RRF fusion |
| **Reranking** | CrossEncoder (ms-marco-MiniLM-L-6-v2) + MMR diversification |
| **Query Rewriting** | LLM-based query expansion (OpenRouter) |
| **LLM** | OpenRouter gpt-oss-120b (free, 32k+ context) |
| **API** | FastAPI + uvicorn, lazy-loaded models, subprocess ingest worker |
| **Validation** | Confidence scoring + keyword grounding |
| **Tokenization** | tiktoken (o200k_harmony) — exact token accounting |
| **Spell-Check** | pyspellchecker |

## Features

### Backend (Elite RAG Pipeline)
- **16k Token Context** — tiktoken-accurate context assembly, safely doubled context window
- **Spell-Check** — automatic query correction (e.g., "chunkier" → "chunker")
- **LLM Query Rewriting** — rewrites questions into search-optimized queries before retrieval
- **Code-Aware Chunking** — AST parser splits at function/class boundaries with 3-line overlap windows
- **Weighted Hybrid Retrieval** — FAISS semantics + BM25 exact match fused via intent-weighted RRF
- **Case-Aware BM25** — preserves identifier casing for better code matching
- **MMR Diversification** — Maximal Marginal Relevance prevents redundant chunks from same file
- **Query Classification** — intent-aware pipeline configuration (location/flow/explanation/debug/general)
- **Context Expansion** — multi-hop reasoning via dependency graph
- **LLM Generation** — OpenRouter gpt-oss-120b (free), 16k context, 2000 token responses
- **Validation** — confidence scoring + keyword grounding checks
- **Lazy Model Loading** — models load on first use; subprocess worker does clone+chunk without loading models
- **Query Caching** — LRU cache on FAISS retrieval for repeated queries
- **GitHub Ingestion** — clone and process any GitHub repository
- **Personalization** — optional Google OAuth (Supabase), query history, user profile

### Frontend (Next.js)
- **Chat Interface** — clean, dark-themed UI inspired by ChatGPT
- **Voice Assistant** — continuous voice mode: press mic, speak queries, hear answers read aloud with modular TTS (pluggable provider architecture in `frontend/lib/tts/`)
- **Markdown Rendering** — syntax-highlighted code blocks
- **Source References** — collapsible panel with file paths and scores
- **GitHub Integration** — ingest repos via URL
- **Loading States** — animated skeleton with rotating status messages
- **Error Handling** — retry functionality with user-friendly messages
- **Google OAuth** — optional sign-in, profile management, query history
- **Login Page** — dedicated `/login` route with animated dark mode UI, sign in/sign up tabs, Google OAuth integration

## Demo Queries

1. "Where is file loading implemented?"
2. "Explain the ingestion flow step by step"
3. "Which file handles chunking?"
4. "How does the embedding pipeline work?"
5. "What does walk_repo do?"

## Quick Start

### 1. Install Backend Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set API Key & Supabase (Google OAuth)

**Backend** — Create `.env` in the project root:
```
OPENAI_API_KEY=sk-or-v1-...
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
```

**Frontend** — Create `frontend/.env.local`:
```
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

- Get a free OpenRouter key at https://openrouter.ai
- Create a free Supabase project at https://supabase.com
- Enable Google provider in Authentication → Providers (add your Google OAuth Client ID/Secret from https://console.cloud.google.com)
- Add `https://your-project.supabase.co/auth/v1/callback` to your Google OAuth redirect URIs
- (Optional) Run `supabase_migration.sql` in Supabase SQL Editor for persistent user data

> Auth is **optional for core RAG**. Google OAuth kicks in automatically when valid Supabase keys are detected.

**Feature tiers:**

| Tier | Features | Auth Required |
|------|----------|---------------|
| **Free** | Ask questions, get code-grounded answers, voice assistant | No |
| **Logged in** | Query history, ingested repo tracking, profile management, ingest repos | Google OAuth |

> **Vercel deployment:** For Google OAuth to work on Vercel, add `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` as **Environment Variables** in your Vercel project settings (Settings → Environment Variables). Also add your Vercel domain to Supabase's allowed redirect URLs and Google Cloud's authorized JavaScript origins.

### 3. Ingest a Repository (Local)
```bash
python3 main.py --repo /path/to/repo --output output/chunks.json
python3 main.py --embed
```

### 4. Start Backend API
Make sure your virtual environment is activated and `.env` is set up:
```bash
source venv/bin/activate
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

Or run directly with the venv Python:
```bash
./venv/bin/uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

### 5. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

### 6. Ingest GitHub Repository (via Frontend)
1. Open http://localhost:3000
2. Navigate to the AI Assistant at `/agent`
3. Paste GitHub repo URL (e.g., `https://github.com/pallets/flask`)
4. Click "Ingest" — automatically clones and processes the repo
5. Start asking questions!

### 7. Test the API
- Swagger docs: http://localhost:8000/docs
- Example query:
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "Which file handles chunking?"}'
```

## Evaluation

The system has three evaluation layers:

### 1. Retrieval Accuracy (`test_queries.json` — 15 queries)
Quick FAISS-only test of search precision. Each query has an `expected_file_hint` or `expected_name_hint`.
```bash
python3 -c "from tests.test_retrieval import run_retrieval_tests; run_retrieval_tests()"
```
**Current result:** **15/15 PASS** — 12 location/explanation queries hit their target files; 3 edge cases correctly return empty.

### 2. End-to-End Pipeline (`run_eval.py` — 16 queries)
Full RAG pipeline test scoring on 4 criteria per query (file hint found, keywords in answer, groundedness, sources).
```bash
python3 eval/run_eval.py
```
Scored /64 — target: ≥ 80%.

### 3. Manual Review (`scorecard.md` — 16 queries)
Human evaluation of correctness (1–5), relevance (1–5), clarity (1–5), and hallucination.
Target: 41/48 for demo readiness.

## API Endpoints

### Backend (FastAPI - localhost:8000)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/stats` | GET | Index statistics |
| `/ask` | POST | Ask a question (returns answer + sources) |
| `/ingest/github` | POST | Clone and ingest GitHub repo (async — returns `task_id`, poll `/ingest/status/{task_id}`) |
| `/ingest/status/{task_id}` | GET | Poll ingest progress / result |
| `/auth/me` | GET | Get current user profile (auth optional) |
| `/auth/profile` | PUT | Update profile name/bio (auth required) |
| `/auth/history` | GET | User query history (auth required) |
| `/auth/repos` | GET | User connected repos (auth required) |
| `/auth/stats` | GET | User usage stats (auth required) |
| `/docs` | GET | Swagger UI |

### Frontend (Next.js - localhost:3000 / [Vercel](https://codebase-ai-assistant.vercel.app))
| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Marketing landing page |
| `/agent` | GET | AI Assistant chat interface |
| `/agent/profile` | GET | User profile page (auth required) |
| `/login` | GET | Login / Sign up page with Google OAuth |
| `/api/ask` | POST | Proxy to backend /ask |
| `/api/ingest/github` | POST | Proxy to backend /ingest/github |
| `/api/auth/[...path]` | GET, PUT | Proxy to backend /auth/* |

## Example Response

```json
{
  "answer": "File loading is implemented in `ingestion/loader.py` via the `walk_repo` function (lines 6-25), which traverses the repository and yields valid file paths. The `read_file` function (lines 28-36) reads file content as a string.",
  "sources": [
    {"file_path": "ingestion/loader.py", "name": "walk_repo", "score": 0.31, "rerank_score": 0.92},
    {"file_path": "ingestion/loader.py", "name": "read_file", "score": 0.77, "rerank_score": 0.85}
  ],
  "retrieved_count": 2,
  "rewritten_query": "ingestion loader walk_repo read_file file loading implementation",
  "validation": {"is_grounded": true, "confidence": 0.9, "warning": null},
  "latency_ms": 1234.5
}
```

## Project Structure

```
CodeBase AI Assistant/
├── api/                    # FastAPI layer
│   ├── app.py            # Routes: /ask, /health, /stats, /ingest/github, /auth/*
│   ├── auth.py           # Supabase JWT verification (active)
│   ├── db.py             # Supabase admin client (users, history, repos)
│   └── schemas.py        # Pydantic request/response models
├── pipeline/              # Core RAG pipeline
│   ├── ask.py            # Full pipeline orchestration
│   ├── query_corrector.py # Spell-checking for queries
│   ├── query_classifier.py # Intent classification
│   ├── hybrid_retriever.py # FAISS + BM25 hybrid search
│   ├── context_expander.py # Multi-hop context expansion
│   ├── reflector.py      # Self-reflection loop
│   ├── reranker.py       # CrossEncoder reranking
│   └── validator.py      # Confidence scoring + validation
├── ingestion/            # Code ingestion
│   ├── loader.py        # Filesystem walker
│   ├── chunker.py       # AST-based code chunking
│   ├── ast_parser.py    # Python AST parsing
│   ├── github_ingestor.py # GitHub repo cloning
│   ├── worker.py        # Subprocess worker (clone+chunk, no model)
│   └── utils.py         # File filtering
├── graph/                 # Dependency graph
│   └── dependency_graph.py # Multi-hop reasoning
├── embeddings/           # Vector store
│   ├── embedder.py      # Sentence-transformer + FAISS builder
│   └── retriever.py     # Similarity search
├── llm/                  # LLM integration
│   ├── generator.py     # OpenRouter API client
│   ├── context_builder.py # Token-aware context assembly
│   └── prompt_utils.py  # System prompt management
├── eval/                 # Evaluation
│   ├── ragas_eval.py    # RAGAS metrics
│   ├── run_eval.py      # Evaluation runner
│   └── test_queries.json # Query test set
├── frontend/             # Next.js frontend
│   ├── app/             # App router pages + API routes
│   ├── components/       # UI components
│   ├── context/         # Theme + Auth providers
│   ├── hooks/           # Custom React hooks
│   └── lib/             # Types, API client, Supabase, TTS providers
├── config.py             # All tunable parameters
├── documentation.md      # Detailed development log
├── supabase_migration.sql # Database schema
└── main.py               # CLI ingestion entry point
```

## System Limits & Capacity

| Constraint | Limit | Notes |
|------------|-------|-------|
| **Max Single File Size** | 500 KB | Larger files are skipped during ingestion (`ingestion/utils.py:29`) |
| **Max Chunk Size** | 150 lines | Large chunks split automatically with 3-line overlap windows |
| **Max Context Tokens** | 16,000 | tiktoken-accurate accounting (o200k_harmony encoding) |
| **Max FAISS Vectors** | ~50,000 | `IndexFlatL2` is efficient up to ~50k vectors |
| **Estimated Max Repo Size** | 1–5 GB | Depends on exclusion rules (node_modules, .git, etc.) |
| **Embedding RAM Usage** | ~1.5 GB | Model loaded on demand; subprocess isolated from main server |
| **Concurrent Queries** | 5–10 | Higher concurrency increases latency significantly |

## Documentation

The project maintains a comprehensive development log in [`documentation.md`](documentation.md). It tracks every implementation decision, code change, and bug fix chronologically.

### What's Inside `documentation.md`

| Section | Content |
|---------|---------|
| **Chronological Action Log** | Every action taken with timestamps, files affected, and reasoning |
| **Step 1: Ingestion + Chunking** | Folder structure, functions, regex patterns, chunk schema |
| **Step 2: Embeddings + Vector DB** | Model selection, FAISS index design, retrieval strategy |
| **Step 3: LLM Integration** | Context builder, prompt engineering, generator setup |
| **Step 4: Elite Upgrade** | AST parser, hybrid retrieval, multi-hop, self-reflection |
| **Step 5: Marketing Website** | Next.js landing page, 12-section layout, design system |
| **Step 6: UI Fixes** | TypeScript fixes, spell-checker corrections, ingestion improvements |

### How to Use the Documentation

- **Understanding architecture:** Read the Step sections in order and perform the steps 
- **Debugging a module:** Search for the filename in the Action Log
- **Reproducing a decision:** Each entry includes the "why" behind changes
- **Onboarding:** Start with the Project Overview, then follow Steps 1→6
