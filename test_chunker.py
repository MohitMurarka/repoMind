from tools.ingestion import ingest_repo
from tools.chunker import chunk_repo

result = ingest_repo("https://github.com/pallets/flask")

if result.error:
    print(f"Ingestion error: {result.error}")
else:
    chunks = chunk_repo(result.files)

    print(f"\nTotal chunks: {len(chunks)}")
    print("\n--- Sample chunks ---")
    for chunk in chunks[:3]:
        print(f"\nFile:    {chunk.file_path}")
        print(f"Symbol:  {chunk.symbol_name}")
        print(f"Lines:   {chunk.start_line}-{chunk.end_line}")
        print(f"Lang:    {chunk.language}")
        print(f"Preview: {chunk.content[:120].strip()}...")
        print("-" * 50)
