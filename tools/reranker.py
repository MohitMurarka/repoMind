import os
from dotenv import load_dotenv
import cohere
from graph.state import Chunk

load_dotenv()

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
RERANK_MODEL = "rerank-v3.5"
TOP_N = 5  # Final chunks passed to the LLM


def rerank(query: str, chunks: list[Chunk], top_n: int = TOP_N) -> list[Chunk]:
    """
    Rerank a list of candidate chunks using Cohere's cross-encoder.

    Takes top 20 hybrid search results, returns top_n most relevant.
    Each chunk is scored by reading query + chunk content together —
    much more accurate than vector similarity alone.

    Args:
        query:   The user's original question
        chunks:  Candidate chunks from hybrid search (top 20)
        top_n:   How many to return after reranking (default 5)

    Returns:
        Top top_n chunks reordered by reranker score, highest first.
    """

    if not chunks:
        return []

    if not COHERE_API_KEY:
        print(
            "Warning: No COHERE_API_KEY found. Skipping rerank, returning top_n as-is."
        )
        return chunks[:top_n]

    client = cohere.ClientV2(api_key=COHERE_API_KEY)

    # Build document strings — same format as what we embed
    # Giving the reranker file path + symbol name + content
    # gives it the same context the embedding model had

    documents = [
        f"File: {chunk.file_path}\nSymbol: {chunk.symbol_name}\n\n{chunk.content}"
        for chunk in chunks
    ]

    try:
        response = client.rerank(
            model=RERANK_MODEL,
            query=query,
            documents=documents,
            top_n=top_n,
        )

        # response.results is sorted by relevance score descending
        reranked_chunks = []
        for result in response.results:
            chunk = chunks[result.index]  # result.index maps back to original list
            chunk.score = result.relevance_score
            reranked_chunks.append(chunk)

        return reranked_chunks

    except Exception as e:
        print(f"Reranker error: {e}. Falling back to top {top_n} hybrid results.")
        return chunks[:top_n]


def rerank_with_scores(
    query: str, chunks: list[Chunk], top_n: int = TOP_N
) -> list[tuple[Chunk, float]]:
    """
    Same as rerank() but returns (chunk, score) tuples.
    Useful for debugging and evaluation.
    """

    reranked = rerank(query, chunks, top_n)
    return [(chunk, chunk.score) for chunk in reranked]
