#!/usr/bin/env python3
"""
run_agent_eval.py — Evaluation harness for LangChain agent with feedback loops.

Evaluates the AegisAgent against task_bank.yaml tasks, with LLM-as-a-Judge scoring.
Uses Langfuse for tracing and score logging following best practices.

Usage:
    python run_agent_eval.py --tasks aegis_eval/task_bank.yaml [--task <id>] [--trials 1] [--verbose]
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

sys.path.insert(0, str(Path(__file__).parent.parent))
from aegis_agents.agent import AegisAgent
from aegis_agents.judge.agent_judge import judge_agent_run
from aegis_agents.config import LANGFUSE_CONFIG, OLLAMA_CONFIG, PROJECT_NAME, TRACE_NAME
from aegis_agents.config import LANGFUSE_CONFIG, PROJECT_NAME, TRACE_NAME


RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def load_task_bank(path: str) -> list[dict]:
    """Load tasks from YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("tasks", [])


def run_single_eval(task: dict, trial_num: int, max_attempts: int = 3, verbose: bool = False) -> dict:
    """Run a single evaluation trial for a task with full Langfuse tracing."""
    trial_id = f"{task['id']}_{trial_num:03d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    question = task["question"]

    if verbose:
        print(f"\n  === Trial {trial_num}: {task['id']} ===")
        print(f"  Q: {question}")

    t0 = time.time()

    # Get Langfuse client
    langfuse = get_langfuse_client()
    if not langfuse:
        # Fallback without Langfuse
        agent = AegisAgent(max_attempts=max_attempts, use_tracing=False)
        agent_result = agent.run(question)
        expected = task.get("expected_result", {})
        judge_result = judge_agent_run(question, agent_result, expected)
        latency = (time.time() - t0) * 1000

        if verbose:
            print(f"  Agent success: {agent_result['success']}")
            print(f"  Judge scores: {judge_result['scores']}")

        return {
            "trial_id": trial_id,
            "task_id": task["id"],
            "category": task.get("category"),
            "difficulty": task.get("difficulty"),
            "question": question,
            "agent_result": {
                "success": agent_result["success"],
                "cypher": agent_result.get("cypher"),
                "answer": agent_result.get("answer"),
                "attempt_count": agent_result.get("attempt_count"),
                "steps": agent_result.get("steps", [])
            },
            "scores": judge_result["scores"],
            "explanation": judge_result.get("explanation", ""),
            "latency_ms": latency,
            "judge_latency_ms": judge_result.get("latency_ms", 0),
            "timestamp": datetime.now().isoformat()
        }

    # With Langfuse tracing
    try:
        with langfuse.start_as_current_observation(
            as_type="span",
            name=f"agent_eval_{task['id']}",
            input={"question": question},
            metadata={
                "task_id": task["id"],
                "task_category": task.get("category"),
                "task_difficulty": task.get("difficulty"),
                "max_attempts": max_attempts,
                "trace_name": TRACE_NAME,
                "project_name": PROJECT_NAME
            }
        ) as span:
            # Run agent
            agent = AegisAgent(max_attempts=max_attempts, use_tracing=False)
            agent_result = agent.run(question)

            # Judge
            expected = task.get("expected_result", {})
            judge_result = judge_agent_run(question, agent_result, expected)

            latency = (time.time() - t0) * 1000

            # Log scores to Langfuse
            for score_name, score_value in judge_result["scores"].items():
                langfuse.score_current_trace(
                    name=score_name,
                    value=score_value,
                    data_type="NUMERIC"
                )

            # Update span with results
            span.update(
                output={
                    "success": agent_result["success"],
                    "answer": agent_result.get("answer", ""),
                    "cypher": agent_result.get("cypher", ""),
                    "attempt_count": agent_result.get("attempt_count", 0),
                    "scores": judge_result["scores"]
                }
            )

            # Log generation for cypher
            with langfuse.start_as_current_observation(
                as_type="generation",
                name="cypher_generation",
                input={"question": question},
                output={
                    "cypher": agent_result.get("cypher", ""),
                    "success": agent_result["success"]
                },
                model=OLLAMA_CONFIG["model"],
                metadata={"task_id": task["id"]}
            ) as gen:
                pass

            # Log generation for answer
            with langfuse.start_as_current_observation(
                as_type="generation",
                name="answer_generation",
                input={"question": question, "results": agent_result.get("data", [])},
                output={"answer": agent_result.get("answer", "")},
                model=OLLAMA_CONFIG["model"],
                metadata={"task_id": task["id"]}
            ) as gen:
                pass

            if verbose:
                print(f"  Agent success: {agent_result['success']}")
                print(f"  Attempts: {agent_result['attempt_count']}")
                print(f"  Cypher: {agent_result.get('cypher', 'N/A')[:60]}...")
                print(f"  Judge scores: {judge_result['scores']}")

            return {
                "trial_id": trial_id,
                "task_id": task["id"],
                "category": task.get("category"),
                "difficulty": task.get("difficulty"),
                "question": question,
                "agent_result": {
                    "success": agent_result["success"],
                    "cypher": agent_result.get("cypher"),
                    "answer": agent_result.get("answer"),
                    "attempt_count": agent_result.get("attempt_count"),
                    "steps": agent_result.get("steps", [])
                },
                "scores": judge_result["scores"],
                "explanation": judge_result.get("explanation", ""),
                "latency_ms": latency,
                "judge_latency_ms": judge_result.get("latency_ms", 0),
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        print(f"  [Langfuse tracing error: {e}]")
        # Fallback on error
        agent = AegisAgent(max_attempts=max_attempts, use_tracing=False)
        agent_result = agent.run(question)
        expected = task.get("expected_result", {})
        judge_result = judge_agent_run(question, agent_result, expected)
        latency = (time.time() - t0) * 1000

        return {
            "trial_id": trial_id,
            "task_id": task["id"],
            "category": task.get("category"),
            "difficulty": task.get("difficulty"),
            "question": question,
            "agent_result": {
                "success": agent_result["success"],
                "cypher": agent_result.get("cypher"),
                "answer": agent_result.get("answer"),
                "attempt_count": agent_result.get("attempt_count"),
                "steps": agent_result.get("steps", [])
            },
            "scores": judge_result["scores"],
            "explanation": judge_result.get("explanation", ""),
            "latency_ms": latency,
            "judge_latency_ms": judge_result.get("latency_ms", 0),
            "timestamp": datetime.now().isoformat()
        }


def run_baseline_eval(task: dict, trial_num: int, verbose: bool = False) -> dict:
    """Run baseline (single-shot, no feedback) evaluation."""
    trial_id = f"{task['id']}_baseline_{trial_num:03d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    question = task["question"]

    if verbose:
        print(f"  [BASELINE] Q: {question[:60]}...")

    t0 = time.time()

    # Run agent with no feedback (single shot)
    agent = AegisAgent(max_attempts=1, use_tracing=False)
    agent_result = agent.run(question)

    # Judge
    expected = task.get("expected_result", {})
    judge_result = judge_agent_run(question, agent_result, expected)

    latency = (time.time() - t0) * 1000

    return {
        "trial_id": trial_id,
        "task_id": task["id"],
        "category": task.get("category"),
        "difficulty": task.get("difficulty"),
        "question": question,
        "agent_result": {
            "success": agent_result["success"],
            "cypher": agent_result.get("cypher"),
            "answer": agent_result.get("answer"),
            "attempt_count": agent_result.get("attempt_count"),
            "steps": agent_result.get("steps", [])
        },
        "scores": judge_result["scores"],
        "explanation": judge_result.get("explanation", ""),
        "latency_ms": latency,
        "judge_latency_ms": judge_result.get("latency_ms", 0),
        "timestamp": datetime.now().isoformat()
    }


def get_langfuse_client():
    """Get Langfuse client singleton with explicit credentials."""
    try:
        from langfuse import Langfuse
        return Langfuse(
            public_key=LANGFUSE_CONFIG["public_key"],
            secret_key=LANGFUSE_CONFIG["secret_key"],
            host=LANGFUSE_CONFIG["host"],
        )
    except ImportError:
        return None


def run_eval(
    tasks: list[dict],
    trials: int = 1,
    max_attempts: int = 3,
    baseline: bool = False,
    verbose: bool = False,
    task_filter: Optional[str] = None
) -> tuple[list[dict], list[dict]]:
    """Run evaluation for all tasks."""
    filtered_tasks = [t for t in tasks if not task_filter or t["id"] == task_filter]

    if task_filter and not filtered_tasks:
        print(f"ERROR: Task '{task_filter}' not found in task bank.")
        return [], []

    print(f"\nRunning agent eval: {len(filtered_tasks)} tasks x {trials} trial(s)")
    print(f"Max attempts per task: {max_attempts}")
    if baseline:
        print("Baseline comparison: ENABLED")

    # Initialize Langfuse client
    langfuse = get_langfuse_client()
    if langfuse:
        print(f"Langfuse tracing: ENABLED ({LANGFUSE_CONFIG['host']})")
    else:
        print("WARNING: Langfuse not configured. Tracing disabled.")

    agent_results = []
    baseline_results = []

    for task in filtered_tasks:
        for trial_num in range(1, trials + 1):
            # Agent eval
            result = run_single_eval(task, trial_num, max_attempts, verbose)
            agent_results.append(result)

            avg_score = sum(result["scores"].values()) / len(result["scores"])
            status = "PASS" if avg_score >= 3 else "WARN"
            print(f"  [{status}] {result['trial_id']} | "
                  f"c={result['scores']['cypher_correctness']} "
                  f"q={result['scores']['query_effectiveness']} "
                  f"f={result['scores']['feedback_loop_benefit']} "
                  f"t={result['scores']['tool_usage']} "
                  f"r={result['scores']['reasoning_quality']} | "
                  f"{result['latency_ms']/1000:.1f}s")

            # Baseline eval (if enabled)
            if baseline:
                baseline_result = run_baseline_eval(task, trial_num, verbose)
                baseline_results.append(baseline_result)

                b_avg = sum(baseline_result["scores"].values()) / len(baseline_result["scores"])
                b_status = "PASS" if b_avg >= 3 else "WARN"
                print(f"  [{b_status}_BASELINE] {baseline_result['trial_id']} | "
                      f"c={baseline_result['scores']['cypher_correctness']} "
                      f"q={baseline_result['scores']['query_effectiveness']} | "
                      f"{baseline_result['latency_ms']/1000:.1f}s")

    # Flush Langfuse at end
    if langfuse:
        langfuse.flush()

    return agent_results, baseline_results


def save_results(agent_results: list[dict], baseline_results: list[dict], tasks_path: str, trials: int):
    """Save results to JSON files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tasks_name = Path(tasks_path).stem

    summary_path = RESULTS_DIR / f"agent_summary_{tasks_name}_{timestamp}.json"
    details_path = RESULTS_DIR / f"agent_trials_{tasks_name}_{timestamp}.jsonl"

    total = len(agent_results)
    if total == 0:
        print("\nNo results to save.")
        return

    score_keys = ["cypher_correctness", "query_effectiveness", "feedback_loop_benefit", "tool_usage", "reasoning_quality"]

    summary = {
        "timestamp": timestamp,
        "tasks_file": tasks_path,
        "trials": trials,
        "total_trials": total,
        "baseline_trials": len(baseline_results),
        "by_category": {},
        "by_difficulty": {},
        "by_score": {},
        "avg_latency_ms": {},
        "pass_rate": 0.0
    }

    # Score averages
    for score_key in score_keys:
        vals = [r["scores"][score_key] for r in agent_results]
        summary["by_score"][score_key] = {
            "avg": sum(vals) / len(vals),
            "min": min(vals),
            "max": max(vals)
        }

    # By category
    categories = set(r["category"] for r in agent_results)
    for cat in categories:
        cat_results = [r for r in agent_results if r["category"] == cat]
        avg_scores = {k: sum(r["scores"][k] for r in cat_results) / len(cat_results) for k in score_keys}
        summary["by_category"][cat] = {"count": len(cat_results), "avg_scores": avg_scores}

    # By difficulty
    difficulties = set(r["difficulty"] for r in agent_results)
    for diff in difficulties:
        diff_results = [r for r in agent_results if r["difficulty"] == diff]
        avg_scores = {k: sum(r["scores"][k] for r in diff_results) / len(diff_results) for k in score_keys}
        summary["by_difficulty"][diff] = {"count": len(diff_results), "avg_scores": avg_scores}

    # Latency averages
    agent_latencies = [r.get("latency_ms", 0) for r in agent_results]
    judge_latencies = [r.get("judge_latency_ms", 0) for r in agent_results]
    total_latencies = [a + b for a, b in zip(agent_latencies, judge_latencies)]
    summary["avg_latency_ms"] = {
        "agent": sum(agent_latencies) / total if agent_latencies else 0,
        "judge": sum(judge_latencies) / total if judge_latencies else 0,
        "total": sum(total_latencies) / total if total_latencies else 0
    }

    # Pass rate
    pass_count = 0
    for r in agent_results:
        avg_score = sum(r["scores"].values()) / len(r["scores"])
        if avg_score >= 3:
            pass_count += 1
    summary["pass_rate"] = pass_count / total

    # Baseline comparison
    if baseline_results:
        summary["baseline_comparison"] = {}
        for score_key in score_keys:
            agent_avg = sum(r["scores"][score_key] for r in agent_results) / total
            baseline_avg = sum(r["scores"][score_key] for r in baseline_results) / len(baseline_results)
            summary["baseline_comparison"][score_key] = {
                "agent_avg": agent_avg,
                "baseline_avg": baseline_avg,
                "delta": agent_avg - baseline_avg
            }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    with open(details_path, "w", encoding="utf-8") as f:
        for r in agent_results:
            f.write(json.dumps(r, default=str) + "\n")

    if baseline_results:
        baseline_details_path = RESULTS_DIR / f"baseline_trials_{tasks_name}_{timestamp}.jsonl"
        with open(baseline_details_path, "w", encoding="utf-8") as f:
            for r in baseline_results:
                f.write(json.dumps(r, default=str) + "\n")

    print(f"\nResults saved:")
    print(f"  Summary: {summary_path}")
    print(f"  Agent trials: {details_path}")
    if baseline_results:
        print(f"  Baseline trials: {baseline_details_path}")
    print(f"\nPass rate: {summary['pass_rate']*100:.1f}% ({pass_count}/{total})")


@click.command()
@click.option("--tasks", default="aegis_eval/task_bank.yaml", help="Path to task_bank.yaml")
@click.option("--task", default=None, help="Run specific task ID only")
@click.option("--trials", default=1, type=int, help="Number of trials per task")
@click.option("--max-attempts", default=3, type=int, help="Max feedback loop attempts")
@click.option("--baseline", is_flag=True, help="Also run baseline (single-shot) comparison")
@click.option("--verbose", is_flag=True, help="Verbose output")
def main(tasks: str, task: Optional[str], trials: int, max_attempts: int, baseline: bool, verbose: bool):
    """Run LLM-as-a-Judge evaluation for the Aegis LangChain agent."""
    print(f"=== Aegis Agent Eval Runner ===")
    print(f"Model: {os.getenv('OLLAMA_MODEL', 'ministral-3:latest')}")
    print(f"Tasks: {tasks}")

    task_list = load_task_bank(tasks)
    agent_results, baseline_results = run_eval(
        task_list,
        trials=trials,
        max_attempts=max_attempts,
        baseline=baseline,
        verbose=verbose,
        task_filter=task
    )

    if agent_results:
        save_results(agent_results, baseline_results, tasks, trials)

        print(f"\nOverall Agent scores:")
        for k in agent_results[0]["scores"].keys():
            avg = sum(r["scores"][k] for r in agent_results) / len(agent_results)
            print(f"  {k}: {avg:.2f}")

        if baseline_results:
            print(f"\nBaseline comparison (delta = agent - baseline):")
            for k in agent_results[0]["scores"].keys():
                agent_avg = sum(r["scores"][k] for r in agent_results) / len(agent_results)
                baseline_avg = sum(r["scores"][k] for r in baseline_results) / len(baseline_results)
                delta = agent_avg - baseline_avg
                print(f"  {k}: {agent_avg:.2f} vs {baseline_avg:.2f} (delta={delta:+.2f})")
    else:
        print("No results.")


if __name__ == "__main__":
    main()
