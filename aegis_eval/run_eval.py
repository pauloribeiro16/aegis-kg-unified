#!/usr/bin/env python3
"""
run_eval.py — Main evaluation runner for aegis-kg-unified using LangGraph agent + Minimax judge.

Uses:
- LangGraph agent (aegis_agents) to execute tasks
- Minimax M2.7 as LLM-as-a-Judge
- Langfuse for tracing and score logging

Usage:
    python run_eval.py --tasks eval/task_bank.yaml [--task <task_id>] [--trials 3] [--verbose]

Environment variables:
    MINIMAX_API_KEY — Minimax API key for judge
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD — Neo4j connection
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST — Langfuse config
"""

import json
import os
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from aegis_eval.config import LANGFUSE, MINIMAX
from aegis_eval.minimax_judge import judge_agent_result


RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def load_task_bank(path: str) -> list[dict]:
    """Load tasks from YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("tasks", [])


def get_langfuse_client():
    """Get or create Langfuse client."""
    if not LANGFUSE.get("public_key") or not LANGFUSE.get("secret_key"):
        print("  [Langfuse] Warning: No credentials configured")
        return None

    try:
        from langfuse import Langfuse
        return Langfuse(
            public_key=LANGFUSE["public_key"],
            secret_key=LANGFUSE["secret_key"],
            host=LANGFUSE["host"]
        )
    except Exception as e:
        print(f"  [Langfuse] Failed to create client: {e}")
        return None


def run_agent_task(question: str, verbose: bool = False) -> dict:
    """Run a task through the LangGraph agent."""
    try:
        from aegis_agents.agent import AegisAgent

        agent = AegisAgent(max_attempts=3, use_tracing=True)
        result = agent.run(question)
        return result
    except Exception as e:
        return {
            "answer": f"Agent error: {str(e)}",
            "cypher": None,
            "steps": [],
            "success": False,
            "attempt_count": 0,
            "error": str(e)
        }


def run_trial(
    task: dict,
    trial_num: int,
    langfuse,
    verbose: bool = False
) -> dict:
    """Run a single eval trial for a task."""
    trial_id = f"{task['id']}_{trial_num:03d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    question = task["question"]

    if verbose:
        print(f"\n  === Trial {trial_num}: {task['id']} ===")
        print(f"  Q: {question}")

    t0 = time.time()

    if verbose:
        print(f"  Running agent...")
    agent_result = run_agent_task(question, verbose)

    if verbose:
        print(f"  Agent done: success={agent_result.get('success')}, trace_id={agent_result.get('trace_id')}")

    if verbose:
        print(f"  Running Minimax judge...")
    judge_result = judge_agent_result(task, agent_result)

    if verbose:
        print(f"  Judge done: scores={bool(judge_result.get('scores'))}, error={judge_result.get('error')}")

    latency = (time.time() - t0) * 1000

    scores = judge_result.get("scores", {})
    avg_scores = {}
    if scores:
        dimensions = set()
        for key in scores:
            if key.endswith('_query') or key.endswith('_answer'):
                dim = key.rsplit('_', 1)[0]
                dimensions.add(dim)
        for dim in dimensions:
            q_score = scores.get(f"{dim}_query", 0)
            a_score = scores.get(f"{dim}_answer", 0)
            avg_scores[dim] = (q_score + a_score) / 2

    trace_id = agent_result.get("trace_id")
    reasoning = judge_result.get("reasoning", {})

    if langfuse and trace_id:
        try:
            # Create judge evaluation span as child of the agent trace
            judge_span = langfuse.start_observation(
                name="judge_evaluation",
                input={"task_id": task["id"], "question": question},
                output={
                    "scores": scores,
                    "avg_scores": avg_scores,
                    "reasoning": reasoning
                },
                metadata={
                    "model": "MiniMax-M2.7",
                    "task_id": task["id"],
                    "trial_id": trial_id
                }
            )
            judge_span.end()

            # Add scores with reasoning as comment (truncated to 500 chars)
            for score_name, score_value in scores.items():
                # Extract dimension from score_name (e.g., "cypher_correctness_query" -> "cypher_correctness")
                dim = score_name.rsplit("_", 1)[0] if "_query" in score_name or "_answer" in score_name else score_name
                comment = reasoning.get(dim, "")[:500] if reasoning.get(dim) else None

                langfuse.create_score(
                    trace_id=trace_id,
                    name=score_name,
                    value=float(score_value),
                    data_type="NUMERIC",
                    comment=comment
                )

            # Add dimension averages
            for dim, avg in avg_scores.items():
                comment = reasoning.get(dim, "")[:500] if reasoning.get(dim) else None
                langfuse.create_score(
                    trace_id=trace_id,
                    name=f"{dim}_avg",
                    value=float(avg),
                    data_type="NUMERIC",
                    comment=comment
                )

            langfuse.flush()
        except Exception as e:
            print(f"  [Langfuse] Error logging scores: {e}")

    return _build_result(task, trial_num, trial_id, question, agent_result, judge_result, latency)


def _build_result(task, trial_num, trial_id, question, agent_result, judge_result, latency):
    """Build result dict from agent and judge results."""
    scores = judge_result.get('scores', {})
    reasoning = judge_result.get('reasoning', {})

    # Compute avg_scores from individual scores
    avg_scores = {}
    if scores:
        dimensions = set()
        for key in scores:
            if key.endswith('_query') or key.endswith('_answer'):
                dim = key.rsplit('_', 1)[0]
                dimensions.add(dim)
        for dim in dimensions:
            q_score = scores.get(f"{dim}_query", 0)
            a_score = scores.get(f"{dim}_answer", 0)
            avg_scores[dim] = (q_score + a_score) / 2

    return {
        "trial_id": trial_id,
        "task_id": task["id"],
        "trial_number": trial_num,
        "category": task.get("category"),
        "difficulty": task.get("difficulty"),
        "question": question,
        "cypher": agent_result.get("cypher"),
        "success": agent_result.get("success", False),
        "attempt_count": agent_result.get("attempt_count", 0),
        "llm_answer": agent_result.get("answer", ""),
        "steps": agent_result.get("steps", []),
        "scores": scores,
        "avg_scores": avg_scores,
        "reasoning": reasoning,
        "latency_ms": {
            "agent": agent_result.get("latency_ms", latency * 0.4),
            "judge": judge_result.get('latency_ms', 0),
            "total": latency
        },
        "timestamp": datetime.now().isoformat()
    }


def run_eval(
    tasks: list[dict],
    trials: int = 1,
    verbose: bool = False,
    task_filter: Optional[str] = None
) -> list[dict]:
    """Run evaluation for all tasks."""
    if not MINIMAX.get("api_key"):
        api_key = os.getenv("MINIMAX_API_KEY", "")
        if not api_key:
            print("ERROR: MINIMAX_API_KEY not configured. Set the environment variable.")
            return []

    if not LANGFUSE.get("public_key") or not LANGFUSE.get("secret_key"):
        print("WARNING: LANGFUSE keys not configured. Tracing will be disabled.")
        print("  Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY environment variables.")

    langfuse = get_langfuse_client()
    if langfuse:
        print(f"Langfuse enabled: {LANGFUSE['host']}")
    else:
        print("Langfuse: Not configured (tracing disabled)")

    print(f"Judge: Minimax M2.7")

    filtered_tasks = [t for t in tasks if not task_filter or t["id"] == task_filter]

    if task_filter and not filtered_tasks:
        print(f"ERROR: Task '{task_filter}' not found in task bank.")
        return []

    print(f"\nRunning eval: {len(filtered_tasks)} tasks x {trials} trial(s)")

    all_results = []
    for task in filtered_tasks:
        for trial_num in range(1, trials + 1):
            result = run_trial(task, trial_num, langfuse, verbose)
            all_results.append(result)

            avg_scores = result.get("avg_scores", {})
            if avg_scores:
                overall_avg = sum(avg_scores.values()) / len(avg_scores)
                status = "PASS" if overall_avg >= 3 else "WARN"
                dim_scores = " ".join([f"{k[:4]}={v:.1f}" for k, v in avg_scores.items()])
                print(f"  [{status}] {result['trial_id']} | {dim_scores} | {result['latency_ms']['total']/1000:.1f}s")
            else:
                print(f"  [FAIL] {result['trial_id']} | error={result.get('error', 'N/A')}")

    if langfuse:
        langfuse.flush()

    return all_results


def save_results(results: list[dict], tasks_path: str, trials: int):
    """Save results to JSON files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tasks_name = Path(tasks_path).stem

    summary_path = RESULTS_DIR / f"summary_{tasks_name}_{timestamp}.json"
    details_path = RESULTS_DIR / f"trials_{tasks_name}_{timestamp}.jsonl"

    total = len(results)
    if total == 0:
        print("\nNo results to save.")
        return

    dimensions = ["cypher_correctness", "query_effectiveness", "feedback_loop_benefit", "tool_usage", "reasoning_quality"]

    summary = {
        "timestamp": timestamp,
        "tasks_file": tasks_path,
        "trials": trials,
        "total_trials": total,
        "by_category": {},
        "by_difficulty": {},
        "by_dimension": {},
        "avg_latency_ms": {},
        "pass_rate": 0.0
    }

    for dim in dimensions:
        query_scores = [r["scores"].get(f"{dim}_query", 0) for r in results]
        answer_scores = [r["scores"].get(f"{dim}_answer", 0) for r in results]
        avg_scores_list = [r["avg_scores"].get(dim, 0) for r in results]

        summary["by_dimension"][dim] = {
            "query_avg": sum(query_scores) / len(query_scores) if query_scores else 0,
            "answer_avg": sum(answer_scores) / len(answer_scores) if answer_scores else 0,
            "overall_avg": sum(avg_scores_list) / len(avg_scores_list) if avg_scores_list else 0
        }

    categories = set(r.get("category") for r in results if r.get("category"))
    for cat in categories:
        cat_results = [r for r in results if r.get("category") == cat]
        cat_avg = {dim: sum(r["avg_scores"].get(dim, 0) for r in cat_results) / len(cat_results) for dim in dimensions}
        summary["by_category"][cat] = {"count": len(cat_results), "avg_scores": cat_avg}

    difficulties = set(r.get("difficulty") for r in results if r.get("difficulty"))
    for diff in difficulties:
        diff_results = [r for r in results if r.get("difficulty") == diff]
        diff_avg = {dim: sum(r["avg_scores"].get(dim, 0) for r in diff_results) / len(diff_results) for dim in dimensions}
        summary["by_difficulty"][diff] = {"count": len(diff_results), "avg_scores": diff_avg}

    avg_latency = {
        k: sum(r["latency_ms"].get(k, 0) for r in results) / total
        for k in ["agent", "judge", "total"]
    }
    summary["avg_latency_ms"] = avg_latency

    pass_count = 0
    for r in results:
        avg_scores = r.get("avg_scores", {})
        if avg_scores:
            overall = sum(avg_scores.values()) / len(avg_scores)
            if overall >= 3:
                pass_count += 1
    summary["pass_rate"] = pass_count / total

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    with open(details_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, default=str) + "\n")

    print(f"\nResults saved:")
    print(f"  Summary: {summary_path}")
    print(f"  Trials:  {details_path}")
    print(f"\nPass rate: {summary['pass_rate']*100:.1f}% ({pass_count}/{total})")


@click.command()
@click.option("--tasks", default="aegis_eval/task_bank.yaml", help="Path to task_bank.yaml")
@click.option("--task", default=None, help="Run specific task ID only")
@click.option("--trials", default=1, type=int, help="Number of trials per task")
@click.option("--verbose", is_flag=True, help="Verbose output")
def main(tasks: str, task: Optional[str], trials: int, verbose: bool):
    """Run LLM-as-a-Judge evaluation using LangGraph agent + Minimax judge."""
    print(f"=== Aegis-KG Unified Eval Runner ===")
    print(f"Agent: LangGraph (aegis_agents)")
    print(f"Judge: Minimax M2.7")

    task_list = load_task_bank(tasks)
    results = run_eval(task_list, trials=trials, verbose=verbose, task_filter=task)

    if results:
        save_results(results, tasks, trials)

        print(f"\n=== Overall Dimension Averages ===")
        first_result = results[0]
        for dim in first_result.get("avg_scores", {}).keys():
            vals = [r["avg_scores"].get(dim, 0) for r in results]
            avg = sum(vals) / len(vals)
            q_vals = [r["scores"].get(f"{dim}_query", 0) for r in results]
            a_vals = [r["scores"].get(f"{dim}_answer", 0) for r in results]
            print(f"  {dim}:")
            print(f"    query_avg={sum(q_vals)/len(q_vals):.2f}, answer_avg={sum(a_vals)/len(a_vals):.2f}, overall={avg:.2f}")
    else:
        print("No results.")


if __name__ == "__main__":
    main()