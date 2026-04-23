import argparse
from dotenv import load_dotenv
from graph.graph import build_graph
from tools.ingestion import ingest_repo
from tools.chunker import chunk_repo
from tools.retriever import build_bm25_index
from langchain_core.messages import HumanMessage

load_dotenv()


def run_agent(repo_url: str, query: str) -> dict:
    """
    Run the RepoMind agent on a query against an indexed repo.
    """
    print(f"\nIndexing repo for BM25 (Qdrant already has vectors)...")
    result = ingest_repo(repo_url)
    chunks = chunk_repo(result.files)
    build_bm25_index(chunks, repo_url)
    print(f"BM25 ready. Running agent...\n")

    # Build graph bound to this repo
    graph = build_graph(repo_url)

    # Invoke with just the query as a HumanMessage
    response = graph.invoke(
        {"messages": [HumanMessage(content=query)]},
        config={"recursion_limit": 50},
    )

    # The last message is the final answer
    final_message = response["messages"][-1]
    final_answer = final_message.content

    # Extract cited files from all tool results in message history
    cited_files = set()
    for msg in response["messages"]:
        content = getattr(msg, "content", "")
        if isinstance(content, str):
            import re

            # Extract file paths from tool output (lines like "src/flask/app.py")
            matches = re.findall(r"[\w/\-]+\.(?:py|js|ts|go|java|rs)", content)
            cited_files.update(matches)

    return {
        "answer": final_answer,
        "cited_files": list(cited_files),
        "iterations": len(
            [
                m
                for m in response["messages"]
                if hasattr(m, "tool_calls") and m.tool_calls
            ]
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RepoMind CLI")
    parser.add_argument("repo_url", help="GitHub repo URL")
    parser.add_argument("query", help="Question about the codebase")
    args = parser.parse_args()

    result = run_agent(args.repo_url, args.query)

    print("\n" + "=" * 60)
    print("ANSWER:")
    print("=" * 60)
    print(result["answer"])
    print(f"\nCited files: {result['cited_files']}")
    print(f"Iterations:  {result['iterations']}")
