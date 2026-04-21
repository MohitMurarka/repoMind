import os
import time
import uuid
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    ScoredPoint,
)
from dotenv import load_dotenv
from graph.state import Chunk

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "repomind-cluster")
VECTOR_DIMENSION = 1536


def get_client() -> QdrantClient:
    return QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        check_compatibility=False,
        timeout=30,
    )


def _qdrant_call_with_retry(fn, retries=5, delay=3):
    """Retry a Qdrant call on connection errors."""
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if attempt == retries - 1:
                raise
            print(
                f"  Qdrant connection failed (attempt {attempt+1}/{retries}), retrying in {delay}s... ({e})"
            )
            time.sleep(delay)


def ensure_collection() -> None:
    """Create the Qdrant collection if it doesn't exist yet."""
    client = get_client()
    try:
        client.get_collection(COLLECTION_NAME)
        print(f"Collection '{COLLECTION_NAME}' already exists.")
        # Still ensure the index exists even if collection already existed
        _ensure_payload_index(client)
        return
    except Exception:
        pass

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_DIMENSION,
            distance=Distance.COSINE,
        ),
    )
    print(f"Created Qdrant collection: {COLLECTION_NAME}")
    _ensure_payload_index(client)


def _ensure_payload_index(client: QdrantClient) -> None:
    """Create payload index on repo_url for fast filtered search."""
    try:
        from qdrant_client.models import PayloadSchemaType

        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="repo_url",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    except Exception:
        pass  # Index may already exist — that's fine


def store_chunks(chunk_vector_pairs: list[tuple[Chunk, list[float]]]) -> int:
    """
    Store embedded chunks in Qdrant.
    Returns number of points stored.
    """
    client = get_client()

    # Use retry for the collection check
    _qdrant_call_with_retry(ensure_collection)

    points = []
    for chunk, vector in chunk_vector_pairs:
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "content": chunk.content,
                    "file_path": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "language": chunk.language,
                    "symbol_name": chunk.symbol_name,
                    "repo_url": chunk.repo_url,
                },
            )
        )

    batch_size = 100
    total_stored = 0

    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        _qdrant_call_with_retry(
            lambda b=batch: client.upsert(collection_name=COLLECTION_NAME, points=b)
        )
        total_stored += len(batch)
        print(f"  Stored {min(i + batch_size, len(points))}/{len(points)} points")

    # ← these two lines are OUTSIDE the for loop (no extra indent)
    print(f"Storage complete. {total_stored} chunks in Qdrant.")
    return total_stored


def search_dense(
    query_vector: list[float], repo_url: str, top_k: int = 20
) -> list[Chunk]:
    """Dense vector search filtered by repo_url."""
    client = get_client()

    results: list[ScoredPoint] = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        query_filter=Filter(
            must=[FieldCondition(key="repo_url", match=MatchValue(value=repo_url))]
        ),
        limit=top_k,
    )

    chunks = []
    for point in results:
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
                score=point.score,
            )
        )

    return chunks


def delete_repo(repo_url: str) -> None:
    """Delete all chunks for a given repo from Qdrant."""

    def _delete():
        client = get_client()
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[FieldCondition(key="repo_url", match=MatchValue(value=repo_url))]
            ),
        )
        print(f"Deleted all chunks for {repo_url}")

    _qdrant_call_with_retry(_delete)


def get_repo_chunk_count(repo_url: str) -> int:
    """How many chunks are stored for a given repo."""
    try:
        client = get_client()
        result = client.count(
            collection_name=COLLECTION_NAME,
            count_filter=Filter(
                must=[FieldCondition(key="repo_url", match=MatchValue(value=repo_url))]
            ),
        )
        return result.count
    except Exception as e:
        print(f"  Warning: Could not verify count ({e})")
        return -1
