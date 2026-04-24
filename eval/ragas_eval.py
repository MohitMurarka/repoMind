"""
RAGAS evaluation pipeline for RepoMind.

Runs the agent against the benchmark Q&A pairs and computes:
  - Faithfulness:       Is the answer grounded in retrieved context?
  - Answer Relevancy:   Does the answer address the question?
  - Context Precision:  Were the retrieved chunks actually useful?
  - Context Recall:     Did we retrieve enough to answer the question?
"""

import os
import sys
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

# Fix import path — add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.benchmark import FLASK_BENCHMARK
from graph.graph import build_graph
from tools.ingestion import ingest_repo
from tools.chunker import chunk_repo
from tools.retriever import build_bm25_index

load_dotenv()

REPO_URL = "https://github.com/pallets/flask"
RESULTS_FILE = "eval/ragas_results.json"


def get_ragas_components():
    """
    Build RAGAS LLM and embeddings for collections metrics.

    collections metrics require an InstructorLLM from llm_factory().
    Must use AsyncOpenAI so ascore() can call agenerate() internally.
    """
    from openai import AsyncOpenAI
    from ragas.llms import llm_factory
    from ragas.embeddings import OpenAIEmbeddings as RagasOpenAIEmbeddings

    async_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    ragas_llm = llm_factory("gpt-4o-mini", client=async_client)
    ragas_embeddings = RagasOpenAIEmbeddings(
        model="text-embedding-3-small",
        client=async_client,
    )
    return ragas_llm, ragas_embeddings


async def _score_sample_async(metrics, sample):
    """
    Score one sample across all metrics using explicit per-metric calls.
    Each collections metric has a fixed signature — we pass args directly
    rather than relying on inspect() which breaks when ascore uses **kwargs.
    """
    from ragas.metrics.collections import (
        Faithfulness,
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
    )

    results = {}
    question = sample["question"]
    answer = sample["answer"]
    contexts = sample["contexts"]
    reference = sample["ground_truth"]

    for metric in metrics:
        name = metric.__class__.__name__
        key_map = {
            "Faithfulness": "faithfulness",
            "AnswerRelevancy": "answer_relevancy",
            "ContextPrecision": "context_precision",
            "ContextRecall": "context_recall",
        }
        key = key_map.get(name, name.lower())

        try:
            if isinstance(metric, Faithfulness):
                # requires: user_input, response, retrieved_contexts
                score = await metric.ascore(
                    user_input=question,
                    response=answer,
                    retrieved_contexts=contexts,
                )
            elif isinstance(metric, AnswerRelevancy):
                # requires: user_input, response  (no retrieved_contexts)
                score = await metric.ascore(
                    user_input=question,
                    response=answer,
                )
            elif isinstance(metric, ContextPrecision):
                # requires: user_input, retrieved_contexts, reference
                score = await metric.ascore(
                    user_input=question,
                    retrieved_contexts=contexts,
                    reference=reference,
                )
            elif isinstance(metric, ContextRecall):
                # requires: user_input, retrieved_contexts, reference
                score = await metric.ascore(
                    user_input=question,
                    retrieved_contexts=contexts,
                    reference=reference,
                )
            else:
                print(f"    Warning: unknown metric {name}, skipping.")
                results[key] = 0.0
                continue

            results[key] = float(score) if score is not None else 0.0

        except Exception as e:
            print(f"    Warning: {name} failed: {e}")
            results[key] = 0.0

    return results


def compute_ragas_scores(valid_results: list[dict]) -> tuple[dict, list[dict]]:
    """
    Compute RAGAS scores using the per-sample async API.
    Returns (overall_scores, per_sample_scores).
    """
    import asyncio
    from ragas.metrics.collections import (
        Faithfulness,
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
    )

    ragas_llm, ragas_embeddings = get_ragas_components()

    metrics = [
        Faithfulness(llm=ragas_llm),
        AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings),
        ContextPrecision(llm=ragas_llm),
        ContextRecall(llm=ragas_llm),
    ]

    async def score_all():
        per_sample = []
        for i, result in enumerate(valid_results):
            print(f"  Scoring sample {i+1}/{len(valid_results)}...")
            scores = await _score_sample_async(metrics, result)
            per_sample.append(scores)
        return per_sample

    per_sample_scores = asyncio.run(score_all())

    metric_keys = [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
    ]
    overall = {}
    for key in metric_keys:
        values = [s[key] for s in per_sample_scores if key in s]
        overall[key] = round(sum(values) / len(values), 3) if values else 0.0

    return overall, per_sample_scores


def setup_repo() -> None:
    """Clone repo and build BM25 index once before running all evaluations."""
    print("Setting up repo for evaluation...")
    result = ingest_repo(REPO_URL)
    chunks = chunk_repo(result.files)
    build_bm25_index(chunks, REPO_URL)
    print(f"Ready. {len(chunks)} chunks indexed.\n")


def run_single_query(graph, question: str) -> dict:
    """
    Run the agent on a single question.
    Returns the answer and the retrieved context chunks.
    """
    response = graph.invoke(
        {"messages": [HumanMessage(content=question)]},
        config={"recursion_limit": 50},
    )

    final_answer = response["messages"][-1].content

    contexts = []
    for msg in response["messages"]:
        if hasattr(msg, "type") and msg.type == "tool":
            content = getattr(msg, "content", "")
            if content and content != "No results found.":
                contexts.append(content)

    return {"answer": final_answer, "contexts": contexts}


def run_evaluation(
    num_questions: int = 25,
    categories: list[str] = None,
    save_results: bool = True,
) -> dict:
    """Main evaluation function."""
    benchmark = FLASK_BENCHMARK
    if categories:
        benchmark = [q for q in benchmark if q["category"] in categories]
    benchmark = benchmark[:num_questions]

    print(f"\n{'='*60}")
    print(f"RepoMind RAGAS Evaluation")
    print(f"Questions: {len(benchmark)}")
    print(f"Repo: {REPO_URL}")
    print(f"{'='*60}\n")

    setup_repo()
    graph = build_graph(REPO_URL)

    raw_results = []
    for i, item in enumerate(benchmark, 1):
        print(f"[{i}/{len(benchmark)}] {item['category']} — {item['question'][:60]}...")
        start = time.time()

        try:
            result = run_single_query(graph, item["question"])
            elapsed = time.time() - start
            raw_results.append(
                {
                    "id": item["id"],
                    "category": item["category"],
                    "question": item["question"],
                    "answer": result["answer"],
                    "contexts": result["contexts"],
                    "ground_truth": item["ground_truth"],
                    "time": elapsed,
                    "error": None,
                }
            )
            print(
                f"  Done in {elapsed:.1f}s — answer: {result['answer'][:80].strip()}..."
            )

        except Exception as e:
            elapsed = time.time() - start
            print(f"  Error: {e}")
            raw_results.append(
                {
                    "id": item["id"],
                    "category": item["category"],
                    "question": item["question"],
                    "answer": "",
                    "contexts": [],
                    "ground_truth": item["ground_truth"],
                    "time": elapsed,
                    "error": str(e),
                }
            )

    valid_results = [r for r in raw_results if not r["error"] and r["answer"]]
    print(f"\n{len(valid_results)}/{len(raw_results)} questions answered successfully.")

    if not valid_results:
        print("No valid results to evaluate.")
        return {}

    print("\nRunning RAGAS metrics (this takes a few minutes)...")
    scores, per_sample_scores = compute_ragas_scores(valid_results)

    category_scores = {r["category"]: [] for r in valid_results}
    for i, r in enumerate(valid_results):
        category_scores[r["category"]].append(per_sample_scores[i])

    category_averages = {}
    for cat, cat_scores in category_scores.items():
        if cat_scores:
            category_averages[cat] = {
                metric: round(
                    sum(s.get(metric, 0) for s in cat_scores) / len(cat_scores), 3
                )
                for metric in [
                    "faithfulness",
                    "answer_relevancy",
                    "context_precision",
                    "context_recall",
                ]
            }

    final_results = {
        "timestamp": datetime.now().isoformat(),
        "repo_url": REPO_URL,
        "num_questions": len(valid_results),
        "overall_scores": {k: round(v, 3) for k, v in scores.items()},
        "category_scores": category_averages,
        "per_question": raw_results,
        "avg_time_per_query": round(
            sum(r["time"] for r in raw_results) / len(raw_results), 1
        ),
    }

    print(f"\n{'='*60}")
    print("RAGAS EVALUATION RESULTS")
    print(f"{'='*60}")
    print(f"Questions evaluated: {len(valid_results)}")
    print(f"\nOverall Scores:")
    print(f"  Faithfulness:      {scores['faithfulness']:.3f}")
    print(f"  Answer Relevancy:  {scores['answer_relevancy']:.3f}")
    print(f"  Context Precision: {scores['context_precision']:.3f}")
    print(f"  Context Recall:    {scores['context_recall']:.3f}")
    print(f"\nCategory Breakdown:")
    for cat, avg in category_averages.items():
        print(
            f"  {cat:20} F:{avg['faithfulness']:.2f} "
            f"AR:{avg['answer_relevancy']:.2f} "
            f"CP:{avg['context_precision']:.2f} "
            f"CR:{avg['context_recall']:.2f}"
        )
    print(f"\nAvg time per query: {final_results['avg_time_per_query']}s")
    print(f"{'='*60}")

    if save_results:
        os.makedirs("eval", exist_ok=True)
        with open(RESULTS_FILE, "w") as f:
            json.dump(final_results, f, indent=2)
        print(f"\nResults saved to {RESULTS_FILE}")

    return final_results


def quick_eval(num_questions: int = 5) -> dict:
    """Quick evaluation — one question per category."""
    categories = ["routing", "blueprints", "context", "error_handling", "cli"]
    return run_evaluation(
        num_questions=num_questions,
        categories=categories,
        save_results=True,
    )


if __name__ == "__main__":
    import argparse
    import asyncio
    from ragas.metrics.collections import (
        Faithfulness,
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
    )

    parser = argparse.ArgumentParser(description="RepoMind RAGAS Evaluation")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick eval (5 questions, one per category)",
    )
    parser.add_argument(
        "--num",
        type=int,
        default=25,
        help="Number of questions to evaluate (default: 25)",
    )
    parser.add_argument("--categories", nargs="+", help="Filter by categories")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Test RAGAS scoring only — no agent, no API costs",
    )
    args = parser.parse_args()

    if args.smoke:
        ragas_llm, ragas_embeddings = get_ragas_components()
        metrics = [
            Faithfulness(llm=ragas_llm),
            AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings),
            ContextPrecision(llm=ragas_llm),
            ContextRecall(llm=ragas_llm),
        ]

        sample = {
            "question": "How do you register a URL route in Flask?",
            "answer": "Routes are registered using @app.route() which calls add_url_rule() in app.py.",
            "contexts": [
                "add_url_rule() is defined in src/flask/app.py and registers URLs with Werkzeug's Map."
            ],
            "ground_truth": "Routes are registered using @app.route() or app.add_url_rule() defined in app.py.",
        }

        print("Running RAGAS smoke test (fake data, no agent)...")
        scores = asyncio.run(_score_sample_async(metrics, sample))
        print("\nSmoke test scores:")
        for k, v in scores.items():
            print(f"  {k}: {v:.3f}")
        print("\nRAGAS smoke test passed!")

    elif args.quick:
        results = quick_eval()

    else:
        results = run_evaluation(
            num_questions=args.num,
            categories=args.categories,
        )
