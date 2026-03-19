# RepoMind — Agentic Codebase Q&A

## What it does
User pastes a GitHub URL → system indexes the codebase → 
LangGraph agent answers questions about the code with 
citations to exact files and line numbers.

## Architecture

### Indexing Pipeline (offline, runs once per repo)
1. Clone repo via GitPython to a temp folder
2. Walk file tree, filter supported languages
3. AST-aware chunking via tree-sitter (by function/class)
4. Embed each chunk via OpenAI text-embedding-3-small
5. Store vectors + metadata in Qdrant Cloud
6. Build BM25 index in memory (per repo)

### Retrieval (runs on every query)
1. Embed the user query
2. Dense search in Qdrant (top 20)
3. BM25 keyword search (top 20)
4. Reciprocal Rank Fusion → merged top 20
5. Cohere reranker → final top 5 chunks

### Agent (LangGraph)
Tools available:
- search_codebase(query) → hybrid retrieval
- get_file(path) → full file contents
- find_references(symbol) → where is this used
- summarize_module(path) → summarize a file
- finish(answer) → return final answer to user

Loop: Router → Tool Executor → Router → ... → Finish
Max iterations: 6

## State Object (ResearchState)
- repo_url: str
- query: str
- messages: list  (full conversation with agent)
- retrieved_chunks: list[Chunk]
- iteration_count: int
- final_answer: str
- cited_files: list[str]

## Chunk Schema
- content: str
- file_path: str
- start_line: int
- end_line: int
- language: str
- symbol_name: str  (function/class name)
- repo_url: str

## Deployment
- Backend: FastAPI on Render (free tier)
- Frontend: React on Vercel (free tier)
- Vector DB: Qdrant Cloud (free tier, 1GB)

## Evaluation
- 25 hand-written Q&A pairs on test repo
- RAGAS metrics: faithfulness, answer relevancy,
  context precision, context recall