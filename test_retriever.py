from tools.ingestion import ingest_repo
from tools.chunker import chunk_repo
from tools.retriever import build_bm25_index, hybrid_search

# Ingest and chunk (no embedding needed for this test)
result = ingest_repo("https://github.com/pallets/flask")
chunks = chunk_repo(result.files)

# Build BM25 index
build_bm25_index(chunks, result.repo_url)

# Test queries
test_queries = [
    "how does routing work",
    "verify_token authentication",
    "request context",
    "Blueprint register",
]

for query in test_queries:
    print(f"\nQuery: '{query}'")
    print("-" * 50)
    hits = hybrid_search(query, result.repo_url, top_k=5)
    for i, chunk in enumerate(hits, 1):
        print(
            f"  {i}. [{chunk.symbol_name}] {chunk.file_path}:{chunk.start_line} (score: {chunk.score:.4f})"
        )
