import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()

# ── In-memory state ──────────────────────────────────────────────
# Tracks indexed repos and their status
# Format: { repo_url: { "status": "indexing|ready|failed", "summary": {...} } }
_indexed_repos: dict[str, dict] = {}

# ── Startup: rebuild BM25 for any already-indexed repos ──────────
# On restart, Qdrant still has the vectors but BM25 is lost (in-memory)
# We rebuild from Qdrant payloads on startup


async def _rebuild_bm25_from_qdrant(repo_url: str) -> None:
    """Fetch chunks from Qdrant and rebuild BM25 index for a repo."""
    try:
        from tools.vector_store import get_client, COLLECTION_NAME
        from tools.retriever import build_bm25_index
        from graph.state import Chunk
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        client = get_client()
        points = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="repo_url", match=MatchValue(value=repo_url))]
            ),
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )[0]

        if not points:
            return

        chunks = []
        for point in points:
            p = point.payload
            chunks.append(
                Chunk(
                    content=p["content"],
                    file_path=p["file_path"],
                    start_line=p["start_line"],
                    end_line=p["end_line"],
                    language=p["language"],
                    symbol_name=p["symbol_name"],
                    repo_url=p["repo_url"],
                )
            )

        build_bm25_index(chunks, repo_url)
        print(f"Rebuilt BM25 index for {repo_url} ({len(chunks)} chunks)")

    except Exception as e:
        print(f"Warning: Could not rebuild BM25 for {repo_url}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: rebuild BM25 for all repos that are already in Qdrant."""
    print("RepoMind API starting up...")
    try:
        from tools.vector_store import get_client, COLLECTION_NAME

        client = get_client()
        collection = client.get_collection(COLLECTION_NAME)
        print(f"Qdrant connected. Collection has {collection.points_count} points.")

        # Find all unique repo_urls in Qdrant
        # We scroll through and collect unique repo_urls
        seen_repos = set()
        offset = None
        while True:
            result = client.scroll(
                collection_name=COLLECTION_NAME,
                limit=100,
                offset=offset,
                with_payload=["repo_url"],
                with_vectors=False,
            )
            points, offset = result
            for point in points:
                repo_url = point.payload.get("repo_url")
                if repo_url:
                    seen_repos.add(repo_url)
            if offset is None:
                break

        print(f"Found {len(seen_repos)} indexed repos. Rebuilding BM25 indices...")
        for repo_url in seen_repos:
            await _rebuild_bm25_from_qdrant(repo_url)
            _indexed_repos[repo_url] = {"status": "ready", "summary": {}}

        print(f"Startup complete. {len(seen_repos)} repos ready.")

    except Exception as e:
        print(f"Warning: Startup BM25 rebuild failed: {e}")

    yield  # App runs here

    print("RepoMind API shutting down.")


# ── App ──────────────────────────────────────────────────────────
app = FastAPI(
    title="RepoMind API",
    description="Agentic codebase Q&A system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────
class IndexRequest(BaseModel):
    repo_url: str


class QueryRequest(BaseModel):
    repo_url: str
    query: str


class IndexResponse(BaseModel):
    repo_url: str
    status: str
    message: str


class QueryResponse(BaseModel):
    repo_url: str
    query: str
    answer: str
    cited_files: list[str]
    iterations: int


class RepoInfo(BaseModel):
    repo_url: str
    status: str
    chunks_stored: Optional[int] = None


# ── Background indexing task ──────────────────────────────────────
def _run_indexing(repo_url: str) -> None:
    """Runs the full indexing pipeline in a background thread."""
    try:
        from tools.pipeline import run_indexing_pipeline

        _indexed_repos[repo_url] = {"status": "indexing", "summary": {}}
        result = run_indexing_pipeline(repo_url)

        if result.get("success"):
            _indexed_repos[repo_url] = {
                "status": "ready",
                "summary": {k: v for k, v in result.items() if k != "chunks"},
            }
        else:
            _indexed_repos[repo_url] = {
                "status": "failed",
                "summary": {"error": result.get("error", "Unknown error")},
            }

    except Exception as e:
        _indexed_repos[repo_url] = {
            "status": "failed",
            "summary": {"error": str(e)},
        }


# ── Routes ────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "name": "RepoMind API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": ["/index", "/query", "/repos", "/repos/{repo_url}/status"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/index", response_model=IndexResponse)
def index_repo(request: IndexRequest, background_tasks: BackgroundTasks):
    """
    Start indexing a GitHub repository.
    Indexing runs in the background — poll /repos/{repo_url}/status to check progress.
    """
    repo_url = request.repo_url.rstrip("/")

    # Validate it looks like a GitHub URL
    if "github.com" not in repo_url:
        raise HTTPException(status_code=400, detail="Only GitHub URLs are supported.")

    # If already indexing, don't start again
    if _indexed_repos.get(repo_url, {}).get("status") == "indexing":
        return IndexResponse(
            repo_url=repo_url,
            status="indexing",
            message="Indexing already in progress.",
        )

    # Start background indexing
    background_tasks.add_task(_run_indexing, repo_url)

    return IndexResponse(
        repo_url=repo_url,
        status="indexing",
        message="Indexing started. Poll /repos/{repo_url}/status for progress.",
    )


@app.get("/repos/{repo_url:path}/status")
def get_repo_status(repo_url: str):
    """Check the indexing status of a specific repo."""
    if repo_url not in _indexed_repos:
        raise HTTPException(status_code=404, detail="Repo not found. Index it first.")

    info = _indexed_repos[repo_url]
    return {
        "repo_url": repo_url,
        "status": info["status"],
        "summary": info.get("summary", {}),
    }


@app.get("/repos", response_model=list[RepoInfo])
def list_repos():
    """List all indexed repositories and their status."""
    result = []
    for repo_url, info in _indexed_repos.items():
        summary = info.get("summary", {})
        result.append(
            RepoInfo(
                repo_url=repo_url,
                status=info["status"],
                chunks_stored=summary.get("chunks_stored"),
            )
        )
    return result


@app.post("/query", response_model=QueryResponse)
def query_repo(request: QueryRequest):
    """
    Query an indexed repository.
    The repo must be indexed before querying.
    """
    repo_url = request.repo_url.rstrip("/")

    # Check repo is ready
    repo_info = _indexed_repos.get(repo_url)
    if not repo_info:
        raise HTTPException(
            status_code=404, detail="Repo not indexed. Call POST /index first."
        )
    if repo_info["status"] == "indexing":
        raise HTTPException(
            status_code=409,
            detail="Repo is still being indexed. Try again in a moment.",
        )
    if repo_info["status"] == "failed":
        raise HTTPException(
            status_code=500,
            detail=f"Indexing failed: {repo_info['summary'].get('error', 'unknown')}",
        )

    # Run the agent
    try:
        from graph.graph import build_graph
        import re

        graph = build_graph(repo_url)
        response = graph.invoke(
            {"messages": [HumanMessage(content=request.query)]},
            config={"recursion_limit": 50},
        )

        final_answer = response["messages"][-1].content
        iterations = len(
            [
                m
                for m in response["messages"]
                if hasattr(m, "tool_calls") and m.tool_calls
            ]
        )

        # Extract cited files
        cited_files = set()
        for msg in response["messages"]:
            content = getattr(msg, "content", "")
            if isinstance(content, str):
                matches = re.findall(r"[\w/\-]+\.(?:py|js|ts|go|java|rs)", content)
                cited_files.update(matches)

        return QueryResponse(
            repo_url=repo_url,
            query=request.query,
            answer=final_answer,
            cited_files=list(cited_files),
            iterations=iterations,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/repos/{repo_url:path}")
def delete_repo_endpoint(repo_url: str):
    """Delete all indexed data for a repository."""
    if repo_url not in _indexed_repos:
        raise HTTPException(status_code=404, detail="Repo not found.")

    try:
        from tools.vector_store import delete_repo

        delete_repo(repo_url)
        del _indexed_repos[repo_url]
        return {"message": f"Deleted {repo_url} successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
