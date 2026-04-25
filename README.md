# RepoMind — Agentic Codebase Q&A

Ask natural language questions about any GitHub codebase. RepoMind indexes the repository with AST-aware chunking, retrieves relevant code using hybrid search, and uses a LangGraph agent to trace across files and return cited answers.

---

## Architecture

```
GitHub URL
    │
    ▼
┌─────────────────────────────────────────────┐
│              Indexing Pipeline               │
│                                             │
│  Clone → AST Chunk → Embed → Qdrant Cloud  │
│  (tree-sitter)  (OpenAI)   (Vector Store)  │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│           Retrieval Stack                    │
│                                             │
│  Dense Search (Qdrant)                      │
│       +                                     │
│  BM25 Keyword Search                        │
│       │                                     │
│  RRF Fusion → Cohere Reranker → Top 5      │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│         LangGraph Agent (GPT-4o-mini)        │
│                                             │
│  Tools: search_codebase, get_file,          │
│         find_references                     │
│                                             │
│  Multi-hop reasoning across files           │
│  Cited answers with file:line references    │
└─────────────────────────────────────────────┘
```

---

## Stack

| Layer           | Technology                       |
| --------------- | -------------------------------- |
| LLM             | GPT-4o-mini                      |
| Agent           | LangGraph `create_react_agent`   |
| Embeddings      | OpenAI `text-embedding-3-small`  |
| Vector DB       | Qdrant Cloud                     |
| Keyword Search  | BM25 (`rank-bm25`)               |
| Reranker        | Cohere `rerank-v3.5`             |
| Code Parsing    | tree-sitter (AST-aware chunking) |
| Backend         | FastAPI + Uvicorn                |
| Frontend        | React                            |
| Backend Deploy  | Render (Docker)                  |
| Frontend Deploy | Vercel                           |

---

## Key Features

**AST-Aware Chunking** — tree-sitter parses source files into functions and classes rather than splitting by character count. Chunks are syntactically complete and semantically meaningful.

**Hybrid Search** — Dense vector search (semantic meaning) combined with BM25 keyword search (exact identifier matching) merged via Reciprocal Rank Fusion. Catches both `"how does auth work?"` and `"where is verify_jwt called?"`.

**Agentic Retrieval** — LangGraph agent decides how many times to search and what to look for next. Multi-hop reasoning traces call chains across files.

**RAGAS Evaluated** — 0.847 faithfulness on a 15-question benchmark covering routing, blueprints, context, error handling, testing, and configuration categories.

---

## RAGAS Benchmark Results

Evaluated on 15 hand-written Q&A pairs about the Flask codebase:

| Metric            | Score |
| ----------------- | ----- |
| Faithfulness      | 0.847 |
| Answer Relevancy  | 0.821 |
| Context Precision | 0.793 |
| Context Recall    | 0.712 |

---

## Project Structure

```
repoMind/
├── tools/
│   ├── ingestion.py      # GitHub cloning + file walking
│   ├── chunker.py        # AST-aware chunking with tree-sitter
│   ├── embedder.py       # OpenAI embedding batching
│   ├── vector_store.py   # Qdrant CRUD + dense search
│   ├── retriever.py      # Hybrid search + RRF + agent tools
│   ├── reranker.py       # Cohere cross-encoder reranking
│   └── pipeline.py       # Full indexing orchestration
├── graph/
│   ├── state.py          # Chunk + AgentState definitions
│   └── graph.py          # LangGraph agent construction
├── agents/
│   └── router.py         # Tool definitions + system prompt
├── api/
│   └── main.py           # FastAPI endpoints
├── eval/
│   ├── benchmark.py      # 25 hand-written Q&A pairs
│   └── ragas_eval.py     # RAGAS evaluation pipeline
├── frontend/             # React UI
├── Dockerfile
└── requirements.txt
```

---

## Local Setup

**Prerequisites:** Python 3.11, Node.js 18+, Git

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/repoMind
cd repoMind

# Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# Fill in: OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY,
#          QDRANT_COLLECTION, COHERE_API_KEY

# Run API
uvicorn api.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm start
```

API docs available at `http://localhost:8000/docs`

---

## API Endpoints

```
POST /index              Start indexing a GitHub repo
GET  /repos              List all indexed repos
GET  /repos/{url}/status Check indexing progress
POST /query              Query an indexed repo
DELETE /repos/{url}      Remove a repo from the index
GET  /health             Health check
```

---

## Evaluation

Run the RAGAS evaluation pipeline:

```bash
# Quick eval (5 questions)
python eval/ragas_eval.py --quick

# Full eval (25 questions)
python eval/ragas_eval.py --num 25

# Specific categories
python eval/ragas_eval.py --categories routing blueprints
```

Results saved to `eval/ragas_results.json`.

---

## Known Limitations

- **Module-level assignments** not extracted by AST chunker (e.g. `g = _AppCtxGlobalsProxy(...)` in Flask). Only function and class definitions are chunked.
- **External dependencies** not indexed. Questions about Flask internals that depend on Werkzeug will have partial answers.
- **BM25 index** is in-memory and rebuilt on server startup from Qdrant payloads.
- **Free tier cold starts** on Render add ~50s to the first request after inactivity.
