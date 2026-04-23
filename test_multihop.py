import time
from main import run_agent

REPO_URL = "https://github.com/pallets/flask"

# These queries require multi-hop reasoning across multiple files
MULTIHOP_QUERIES = [
    {
        "id": 1,
        "query": "How does Flask's Blueprint system work end to end — from registration to URL routing?",
        "expect_files": ["blueprints.py", "app.py"],
        "difficulty": "medium",
    },
    {
        "id": 2,
        "query": "What happens step by step when an unhandled exception is raised during a Flask request?",
        "expect_files": ["app.py", "ctx.py"],
        "difficulty": "hard",
    },
    {
        "id": 3,
        "query": "How does Flask's test client work and how does it simulate HTTP requests?",
        "expect_files": ["testing.py", "app.py"],
        "difficulty": "medium",
    },
    {
        "id": 4,
        "query": "How does the flask CLI discover and register commands from the application?",
        "expect_files": ["cli.py", "app.py"],
        "difficulty": "medium",
    },
    {
        "id": 5,
        "query": "What is the g object in Flask, where is it defined and how does it get reset between requests?",
        "expect_files": ["globals.py", "ctx.py"],
        "difficulty": "easy",
    },
]


def evaluate_result(result: dict, expected_files: list) -> dict:
    """Check if the result cited the expected files."""
    cited = result.get("cited_files", [])
    hits = []
    misses = []
    for expected in expected_files:
        found = any(expected in f for f in cited)
        if found:
            hits.append(expected)
        else:
            misses.append(expected)
    return {
        "hits": hits,
        "misses": misses,
        "coverage": len(hits) / len(expected_files) if expected_files else 0,
    }


def run_multihop_tests():
    print(f"\n{'='*65}")
    print("RepoMind Multi-Hop Stress Test")
    print(f"Repo: {REPO_URL}")
    print(f"{'='*65}\n")

    # Build BM25 once for all queries
    from tools.ingestion import ingest_repo
    from tools.chunker import chunk_repo
    from tools.retriever import build_bm25_index
    from graph.graph import build_graph
    from langchain_core.messages import HumanMessage

    print("Building BM25 index once for all queries...")
    ingestion = ingest_repo(REPO_URL)
    chunks = chunk_repo(ingestion.files)
    build_bm25_index(chunks, REPO_URL)
    graph = build_graph(REPO_URL)
    print(f"Ready. Running {len(MULTIHOP_QUERIES)} queries...\n")

    results = []

    for test in MULTIHOP_QUERIES:
        print(f"\nQuery {test['id']} [{test['difficulty'].upper()}]:")
        print(f"  {test['query']}")
        print(f"  Expected files: {test['expect_files']}")
        print("-" * 65)

        start = time.time()

        response = graph.invoke(
            {"messages": [HumanMessage(content=test["query"])]},
            config={"recursion_limit": 50},
        )

        elapsed = time.time() - start
        final_answer = response["messages"][-1].content
        iterations = len(
            [
                m
                for m in response["messages"]
                if hasattr(m, "tool_calls") and m.tool_calls
            ]
        )

        # Extract cited files
        import re

        cited_files = set()
        for msg in response["messages"]:
            content = getattr(msg, "content", "")
            if isinstance(content, str):
                matches = re.findall(r"[\w/\-]+\.(?:py|js|ts|go|java|rs)", content)
                cited_files.update(matches)

        eval_result = evaluate_result(
            {"cited_files": list(cited_files)}, test["expect_files"]
        )

        print(f"  Answer preview: {final_answer[:200].strip()}...")
        print(f"  Cited files:    {list(cited_files)[:5]}")
        print(
            f"  File coverage:  {eval_result['coverage']*100:.0f}%"
            f" (hits: {eval_result['hits']}, misses: {eval_result['misses']})"
        )
        print(f"  Iterations:     {iterations}")
        print(f"  Time:           {elapsed:.1f}s")

        results.append(
            {
                "id": test["id"],
                "difficulty": test["difficulty"],
                "coverage": eval_result["coverage"],
                "iterations": iterations,
                "time": elapsed,
                "hits": eval_result["hits"],
                "misses": eval_result["misses"],
            }
        )

    # Summary
    print(f"\n{'='*65}")
    print("SUMMARY")
    print(f"{'='*65}")
    avg_coverage = sum(r["coverage"] for r in results) / len(results)
    avg_iterations = sum(r["iterations"] for r in results) / len(results)
    avg_time = sum(r["time"] for r in results) / len(results)

    print(f"Average file coverage:  {avg_coverage*100:.0f}%")
    print(f"Average iterations:     {avg_iterations:.1f}")
    print(f"Average time per query: {avg_time:.1f}s")
    print(f"\nPer-query results:")
    for r in results:
        status = "PASS" if r["coverage"] >= 0.5 else "FAIL"
        print(
            f"  Q{r['id']} [{r['difficulty']:6}] {status} — "
            f"coverage: {r['coverage']*100:.0f}%, "
            f"iters: {r['iterations']}, "
            f"time: {r['time']:.1f}s"
        )

    return results


if __name__ == "__main__":
    run_multihop_tests()
