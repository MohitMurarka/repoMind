import os
import time
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv
from graph.state import Chunk

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
BATCH_SIZE = 100  # OpenAI allows up to 2048 inputs per request, we stay conservative


def _prepare_text(chunk: Chunk) -> str:
    """
    Build the text we actually embed.
    Prepending file path + symbol name gives the model context
    about what the code does, not just the raw syntax.
    """
    return f"File:{chunk.file_path}\nSymbol : {chunk.symbol_name}\n\n{chunk.content}"


def embed_chunks(chunks: list[Chunk]) -> list[tuple[Chunk, list[float]]]:
    """
    Embed a list of chunks using OpenAI text-embedding-3-small.
    Returns list of (chunk, vector) tuples.
    Processes in batches to stay within API limits.
    """
    results = []
    total = len(chunks)

    print(f"Embedding {total} chunks in batches of {BATCH_SIZE}...")

    for i in range(0, total, BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts = [_prepare_text(chunk) for chunk in batch]

        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts,
            )
            vectors = [item.embedding for item in response.data]

            for chunk, vector in zip(batch, vectors):
                results.append((chunk, vector))

            print(f"  Embedded {min(i + BATCH_SIZE, total)}/{total}")

            # Respect rate limits — pause briefly between batches
            if i + BATCH_SIZE < total:
                time.sleep(0.5)

        except Exception as e:
            print(f"  Embedding error on batch {i//BATCH_SIZE + 1}: {e}")
            # Skip failed batch rather than crashing entire pipeline
            continue

    print(f"Embedding complete. {len(results)}/{total} chunks embedded.")
    return results


def embed_query(query: str) -> Optional[list[float]]:
    """
    Embed a single query string for retrieval.
    Uses the same model as chunk embedding — this is critical.
    """

    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[query],
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Query embedding error: {e}")
        return None
