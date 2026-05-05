#!/usr/bin/env python3
"""
minimax_judge.py — Minimax-based LLM-as-a-Judge for evaluation.

Uses MiniMax M2.7 as the judge model via the Minimax API.
Scores 5 dimensions, each with query and answer sub-scores.

Usage:
    from minimax_judge import judge_agent_result

    scores = judge_agent_result(task, agent_result)
"""

import json
import re
import time
from typing import Optional

from aegis_eval.config import MINIMAX
from aegis_eval.minimax_client import call_minimax
from aegis_eval.judge_prompts import (
    get_evaluation_prompt,
    get_dimension_names,
    format_db_results
)


def judge_agent_result(task: dict, agent_result: dict) -> dict:
    """
    Judge a single agent evaluation result using Minimax.

    Args:
        task: Task dict from task_bank.yaml
        agent_result: {
            'cypher': str,
            'steps': list[dict],
            'query_result': dict,  # {'data': [...], 'error': ...}
            'llm_answer': str,
            'success': bool,
            'attempt_count': int,
            'trace_id': str  # Optional, for Langfuse logging
        }

    Returns:
        {
            'scores': {
                'cypher_correctness_query': int,
                'cypher_correctness_answer': int,
                'query_effectiveness_query': int,
                'query_effectiveness_answer': int,
                'feedback_loop_benefit_query': int,
                'feedback_loop_benefit_answer': int,
                'tool_usage_query': int,
                'tool_usage_answer': int,
                'reasoning_quality_query': int,
                'reasoning_quality_answer': int
            },
            'reasoning': {
                'cypher_correctness': str,
                'query_effectiveness': str,
                ...
            },
            'avg_scores': {
                'cypher_correctness': float,
                'query_effectiveness': float,
                ...
            },
            'latency_ms': float,
            'error': str or None
        }
    """
    dimensions = get_dimension_names()
    verbose = agent_result.get("_verbose", False)

    # Check if Minimax is configured
    if not MINIMAX.get("api_key"):
        return _error_result("MINIMAX_API_KEY not configured", dimensions)

    # Build the evaluation prompt
    system_prompt, user_prompt = get_evaluation_prompt(task, agent_result)

    if verbose:
        import os
        print(f"[judge] Calling Minimax M2.7 (prompt: {len(user_prompt)} chars)...", flush=True)
        print(f"[DEBUG] judge_agent_result: MINIMAX api_key len={len(MINIMAX.get('api_key', ''))}, os.getenv len={len(os.getenv('MINIMAX_API_KEY', ''))}", flush=True)

    # Call Minimax
    start = time.time()
    result = call_minimax(
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt
    )
    latency_ms = (time.time() - start) * 1000

    if result["error"]:
        if verbose:
            print(f"[judge] Minimax error ({latency_ms/1000:.1f}s): {result['error']}", flush=True)
        return _error_result(result["error"], dimensions, latency_ms)

    raw_content = result["content"].strip()

    if verbose:
        print(f"[judge] Response ({latency_ms/1000:.1f}s): {raw_content[:200]}", flush=True)

    # Parse the JSON response
    parsed = _parse_json_response(raw_content, dimensions)

    if parsed is None:
        if verbose:
            print(f"[judge] PARSE FAILED: {raw_content[:300]}", flush=True)
        return {
            'scores': _default_scores(dimensions),
            'reasoning': {},
            'avg_scores': {},
            'latency_ms': latency_ms,
            'error': f"Failed to parse JSON: {raw_content[:500]}"
        }

    # Extract scores and reasoning
    scores, reasoning, avg_scores = _extract_scores_and_reasoning(parsed, dimensions)

    if verbose:
        cyph = scores.get('cypher_correctness_query', 0)
        quer = scores.get('query_effectiveness_query', 0)
        feed = scores.get('feedback_loop_benefit_query', 0)
        tool = scores.get('tool_usage_query', 0)
        reas = scores.get('reasoning_quality_query', 0)
        print(f"[judge] Scores: cyph={cyph} quer={quer} feed={feed} tool={tool} reas={reas}", flush=True)

    return {
        'scores': scores,
        'reasoning': reasoning,
        'avg_scores': avg_scores,
        'latency_ms': latency_ms,
        'error': None
    }


def _parse_json_response(raw: str, dimensions: list[str]) -> Optional[dict]:
    """Parse the JSON response from Minimax."""
    # Clean up the response
    cleaned = raw.strip()

    # Remove markdown code blocks if present
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        json_match = re.search(r"\{[\s\S]*\}", cleaned)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        return None


def _extract_scores_and_reasoning(parsed: dict, dimensions: list[str]) -> tuple[dict, dict, dict]:
    """Extract scores and reasoning from parsed JSON."""
    scores = {}
    reasoning = {}
    avg_scores = {}

    for dim in dimensions:
        dim_data = parsed.get(dim, {})
        if isinstance(dim_data, dict):
            query_score = _clamp_score(dim_data.get("query", 3))
            answer_score = _clamp_score(dim_data.get("answer", 3))
            dim_reasoning = dim_data.get("reasoning", "")
        else:
            # Handle case where dimension is just a number
            score_val = _clamp_score(dim_data)
            query_score = score_val
            answer_score = score_val
            dim_reasoning = ""

        scores[f"{dim}_query"] = query_score
        scores[f"{dim}_answer"] = answer_score
        reasoning[dim] = dim_reasoning
        avg_scores[dim] = (query_score + answer_score) / 2

    return scores, reasoning, avg_scores


def _clamp_score(val, default: int = 0) -> int:
    """Clamp score to 1-5 range. Default 0 indicates failure."""
    try:
        v = int(val)
        return max(1, min(5, v))
    except (ValueError, TypeError):
        return default


def _default_scores(dimensions: list[str]) -> dict:
    """Return default scores structure — 0 indicates failure."""
    scores = {}
    for dim in dimensions:
        scores[f"{dim}_query"] = 0
        scores[f"{dim}_answer"] = 0
    return scores


def _error_result(error: str, dimensions: list[str], latency_ms: float = 0) -> dict:
    """Return an error result."""
    return {
        'scores': _default_scores(dimensions),
        'reasoning': {},
        'avg_scores': {},
        'latency_ms': latency_ms,
        'error': error
    }


def log_scores_to_langfuse(langfuse, trace_id: str, scores: dict, reasoning: dict):
    """
    Log evaluation scores to Langfuse.

    Args:
        langfuse: Langfuse client instance
        trace_id: The trace ID to attach scores to
        scores: Dict of score_name -> score_value
        reasoning: Dict of dimension -> reasoning_text
    """
    if not langfuse or not trace_id:
        return

    try:
        # Log each score as a separate Langfuse score
        for score_name, score_value in scores.items():
            # Extract dimension from score name (e.g., "cypher_correctness_query")
            parts = score_name.rsplit("_", 1)  # Split on last underscore
            if len(parts) == 2:
                dimension, subdim = parts
                comment = reasoning.get(dimension, "")
            else:
                comment = ""

            langfuse.create_score(
                trace_id=trace_id,
                name=score_name,
                value=float(score_value),
                data_type="NUMERIC",
                comment=comment[:500] if comment else None
            )

        # Also log aggregated dimension scores
        dimensions = get_dimension_names()
        for dim in dimensions:
            dim_key = dim
            query_score = scores.get(f"{dim}_query", 0)
            answer_score = scores.get(f"{dim}_answer", 0)
            avg_score = (query_score + answer_score) / 2

            langfuse.create_score(
                trace_id=trace_id,
                name=f"{dim}_avg",
                value=avg_score,
                data_type="NUMERIC",
                comment=reasoning.get(dim, "")[:500] if reasoning.get(dim) else None
            )

        langfuse.flush()
    except Exception as e:
        print(f"  [Langfuse score logging error: {e}]")


if __name__ == "__main__":
    # Test the judge
    import os
    os.environ.setdefault("MINIMAX_API_KEY", os.getenv("MINIMAX_API_KEY", ""))

    print("Testing Minimax judge...")

    test_task = {
        "id": "test_gdpr_clause_count",
        "question": "How many clauses does GDPR have?"
    }

    test_agent_result = {
        "cypher": "MATCH (r:Regulation {regulationId: 'GDPR'})-[:HAS_CLAUSE]->(c:Clause) RETURN count(c) AS clauseCount",
        "steps": [
            {
                "attempt": 1,
                "cypher": "MATCH (r:Regulation {regulationId: 'GDPR'})-[:HAS_CLAUSE]->(c:Clause) RETURN count(c) AS clauseCount",
                "row_count": 1,
                "data": [{"clauseCount": 28}],
                "error": None
            }
        ],
        "query_result": {"data": [{"clauseCount": 28}], "error": None},
        "llm_answer": "GDPR has 28 clauses according to the knowledge graph.",
        "success": True,
        "attempt_count": 1
    }

    result = judge_agent_result(test_task, test_agent_result)

    print(f"\nScores:")
    for score_name, score_value in result['scores'].items():
        print(f"  {score_name}: {score_value}")

    print(f"\nAverage scores:")
    for dim, avg in result['avg_scores'].items():
        print(f"  {dim}: {avg:.2f}")

    print(f"\nLatency: {result['latency_ms']:.0f}ms")

    if result['error']:
        print(f"Error: {result['error']}")