import os
from typing import Optional
from rank_bm25 import BM25Okapi
from dotenv import load_dotenv
from graph.state import Chunk
from tools.embedder import embed_query
from tools.vector_store import search_dense

load_dotenv()

# BM25 indices stored in memory, keyed by repo_url
# Format: { repo_url: { "bm25": BM25Okapi, "chunks": list[Chunk] } }
_bm25_indices: dict[str, dict] = {}

RRF_K = 60  # Standard RRF constant — dampens influence of very high ranks


def _tokenize(text: str) -> list[str]:
    """
    Simple whitespace + lowercase tokenizer for BM25.
    Splits on whitespace and common code punctuation.
    """
    import re

    # Split on whitespace and punctuation but keep identifiers intact
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*|[0-9]+", text)
    return [t.lower() for t in tokens]


def build_bm25_index(chunks: list[Chunk], repo_url: str) -> None:
    """
    Build and cache a BM25 index for a repo's chunks.
    Must be called after chunking, before any retrieval.

    Args:
        chunks: All chunks for the repo
        repo_url: Used as the cache key
    """
    print(f"Building BM25 index for {len(chunks)} chunks...")

    tokenized_corpus = []
    for chunk in chunks:
        # Combine all text fields for BM25 — same as what we embed
        text = (
            f"File: {chunk.file_path}\nSymbol: {chunk.symbol_name}\n\n{chunk.content}"
        )
        tokenized_corpus.append(_tokenize(text))

    bm25 = BM25Okapi(tokenized_corpus)

    _bm25_indices[repo_url] = {
        "bm25": bm25,
        "chunks": chunks,
    }

    print(f"BM25 index built. {len(chunks)} documents indexed.")


def _search_bm25(query: str, repo_url: str, top_k: int = 20) -> list[Chunk]:
    """
    BM25 keyword search within a repo's index.
    Returns top_k chunks ranked by BM25 score.
    """

    if repo_url not in _bm25_indices:
        print(f"Warning: No BM25 index found for {repo_url}. Skipping sparse search.")
        return []

    index_data = _bm25_indices[repo_url]
    bm25: BM25Okapi = index_data["bm25"]
    chunks: list[Chunk] = index_data["chunks"]

    query_tokens = _tokenize(query)
    scores = bm25.get_scores(query_tokens)

    # Get top_k indices sorted by score descending
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[
        :top_k
    ]

    results = []
    for idx in top_indices:
        if scores[idx] > 0:  # Skip zero-score results
            chunk = chunks[idx]
            chunk.score = float(scores[idx])
            results.append(chunk)

    return results


def _reciprocal_rank_fusion(
    dense_results: list[Chunk],
    sparse_results: list[Chunk],
    k: int = RRF_K,
) -> list[Chunk]:
    """
    Merge two ranked lists using Reciprocal Rank Fusion.

    Formula: RRF_score(chunk) = sum of 1/(rank + k) across all lists
    where rank is 1-indexed position in each list.

    Chunks appearing in both lists get contributions from both,
    naturally floating to the top.
    """

    rrf_scores: dict[str, float] = {}  # file_path:start_line → score
    chunk_map: dict[str, Chunk] = {}  # same key → Chunk object

    def chunk_key(chunk: Chunk) -> str:
        return f"{chunk.file_path}:{chunk.start_line}"

    # Score from dense results
    for rank, chunk in enumerate(dense_results, start=1):
        key = chunk_key(chunk)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (rank + k)
        chunk_map[key] = chunk

    # Score from sparse (BM25) results
    for rank, chunk in enumerate(sparse_results, start=1):
        key = chunk_key(chunk)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (rank + k)
        chunk_map[key] = chunk

    # Sort by RRF score descending
    sorted_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)

    fused = []
    for key in sorted_keys:
        chunk = chunk_map[key]
        chunk.score = rrf_scores[key]  # Overwrite with RRF score
        fused.append(chunk)

    return fused


def hybrid_search(
    query: str,
    repo_url: str,
    top_k: int = 20,
) -> list[Chunk]:
    """
    Hybrid search: dense (semantic) + sparse (BM25) merged via RRF.

    Steps:
    1. Embed query → dense search in Qdrant (top 20)
    2. Tokenize query → BM25 search in memory index (top 20)
    3. Merge both lists with RRF → unified top 20
    4. Return top_k results

    Args:
        query:   Natural language or code query
        repo_url: Which repo to search in
        top_k:   How many results to return (before reranking)
    """

    # Step 1: Dense search
    query_vector = embed_query(query)
    if query_vector is None:
        print("Warning : Query embedding failed. Falling back to BM25 only.")
        return _search_bm25(query, repo_url, top_k)

    dense_results = search_dense(query_vector, repo_url, top_k=top_k)

    # Step 2: Sparse (BM25) search
    sparse_results = _search_bm25(query, repo_url, top_k=top_k)

    # Step 3: RRF fusion
    fused_results = _reciprocal_rank_fusion(dense_results, sparse_results)

    # Step 4: Return top_k
    return fused_results[:top_k]


def get_file_chunks(file_path: str, repo_url: str) -> list[Chunk]:
    """
    Return all chunks from a specific file.
    Used by the agent's get_file() tool.
    """
    if repo_url not in _bm25_indices:
        return []

    all_chunks = _bm25_indices[repo_url]["chunks"]
    return [c for c in all_chunks if c.file_path == file_path]


def find_symbol_references(symbol_name: str, repo_url: str) -> list[Chunk]:
    """
    Find chunks where a symbol name appears — either as the symbol itself
    or in the content. Used by the agent's find_references() tool.
    """
    if repo_url not in _bm25_indices:
        return []

    all_chunks = _bm25_indices[repo_url]["chunks"]
    matches = []

    for chunk in all_chunks:
        if (
            symbol_name.lower() in chunk.symbol_name.lower()
            or symbol_name in chunk.content
        ):
            matches.append(chunk)

    return matches[:10]  # Cap at 10 to avoid overwhelming the agent
