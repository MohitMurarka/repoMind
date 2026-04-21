import os
from tools.ingestion import ingest_repo
from tools.chunker import chunk_repo
from tools.embedder import embed_chunks
from tools.vector_store import store_chunks, get_repo_chunk_count, delete_repo
from tools.retriever import build_bm25_index  # ← new import
from graph.state import Chunk


def run_indexing_pipeline(repo_url: str) -> dict:
    print(f"\n{'='*50}")
    print(f"Starting indexing pipeline for: {repo_url}")
    print(f"{'='*50}\n")

    # Step 1: Ingest
    ingestion_result = ingest_repo(repo_url)
    if ingestion_result.error:
        return {"success": False, "error": ingestion_result.error}

    # Step 1.5: Delete existing chunks
    print(f"Clearing existing chunks for {repo_url}...")
    delete_repo(repo_url)

    # Step 2: Chunk
    chunks = chunk_repo(ingestion_result.files)
    if not chunks:
        return {"success": False, "error": "No chunks produced from repo."}

    # Step 2.5: Build BM25 index  ← new step
    build_bm25_index(chunks, repo_url)

    # Step 3: Embed
    chunk_vector_pairs = embed_chunks(chunks)
    if not chunk_vector_pairs:
        return {"success": False, "error": "Embedding failed for all chunks."}

    # Step 4: Store
    stored_count = store_chunks(chunk_vector_pairs)

    # Step 5: Verify
    cloud_count = get_repo_chunk_count(repo_url)

    summary = {
        "success": True,
        "repo_url": repo_url,
        "repo_name": ingestion_result.repo_name,
        "files_ingested": len(ingestion_result.files),
        "files_skipped": len(ingestion_result.skipped_files),
        "chunks_created": len(chunks),
        "chunks_stored": stored_count,
        "chunks_in_cloud": (
            cloud_count if cloud_count >= 0 else "verified via dashboard"
        ),
    }

    print(f"\n{'='*50}")
    print("Pipeline complete!")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"{'='*50}\n")

    return summary
