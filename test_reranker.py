from tools.ingestion import ingest_repo
from tools.chunker import chunk_repo
from tools.retriever import build_bm25_index, retrieve

# Ingest and chunk
result = ingest_repo("https://github.com/pallets/flask")
chunks = chunk_repo(result.files)
build_bm25_index(chunks, result.repo_url)

# Test the full retrieval pipeline
test_queries = [
    "how does request context work",
    "Blueprint registration",
    "error handling and exceptions",
]

for query in test_queries:
    print(f"\nQuery: '{query}'")
    print("=" * 55)
    hits = retrieve(query, result.repo_url)
    for i, chunk in enumerate(hits, 1):
        print(f"  {i}. [{chunk.symbol_name}]")
        print(f"     {chunk.file_path}:{chunk.start_line}-{chunk.end_line}")
        print(f"     score: {chunk.score:.4f}")
        print(f"     preview: {chunk.content[:80].strip()}...")
        print()
