"""LLM-as-a-Judge for evaluating agent runs with feedback loops."""

import json
import re
import time
from typing import Optional

import requests

from aegis_agents.config import OLLAMA_CONFIG


SYSTEM_JUDGE = """You are an expert evaluator for a regulatory compliance knowledge graph agent.

The agent uses a ReAct-style loop with tools to query Neo4j via Cypher.
Given a task, the agent's execution steps, and the final answer, evaluate the quality.

Score each dimension from 1-5:
1 = Poor / Incorrect
2 = Below average
3 = Adequate / Partially correct
4 = Good / Mostly correct
5 = Excellent / Fully correct

Return a JSON object with:
{
  "scores": {
    "cypher_correctness": <int 1-5>,
    "query_effectiveness": <int 1-5>,
    "feedback_loop_benefit": <int 1-5>,
    "tool_usage": <int 1-5>,
    "reasoning_quality": <int 1-5>
  },
  "explanation": "<brief explanation of each score>"
}
"""


USER_JUDGE_TEMPLATE = """TASK: {question}

AGENT EXECUTION STEPS:
{step_history}

FINAL ANSWER: {final_answer}

EXPECTED RESULT:
{expected_result}

Evaluate the agent's performance and return JSON only."""


def format_step_history(steps: list[dict]) -> str:
    """Format agent steps for judge prompt."""
    if not steps:
        return "No execution steps recorded."

    lines = []
    for s in steps:
        attempt = s.get("attempt", "?")
        success = s.get("success", False)
        refined = s.get("refined", False)
        cypher = s.get("cypher", "N/A")
        error = s.get("error")
        row_count = s.get("row_count", 0)
        refined_info = " (refined)" if refined else ""

        if success:
            lines.append(f"Step {attempt}: SUCCESS{refined_info} - {row_count} rows - Cypher: {cypher[:80]}")
        elif error:
            lines.append(f"Step {attempt}: ERROR{refined_info} - {error[:60]} - Cypher: {cypher[:80] if cypher else 'N/A'}")
        else:
            lines.append(f"Step {attempt}: NO RESULTS{refined_info}")

    return "\n".join(lines)


def call_ollama(prompt: str, system: str = "") -> dict:
    """Call Ollama API."""
    url = f"{OLLAMA_CONFIG['base_url']}/api/generate"
    payload = {
        "model": OLLAMA_CONFIG["model"],
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 512
        }
    }
    start = time.time()
    try:
        resp = requests.post(url, json=payload, timeout=OLLAMA_CONFIG["timeout"])
        elapsed = (time.time() - start) * 1000
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}", "raw": resp.text[:300], "latency_ms": elapsed}
        data = resp.json()
        return {
            "raw": data.get("response", ""),
            "latency_ms": elapsed,
            "tokens": {
                "prompt_eval_count": data.get("prompt_eval_count", 0),
                "eval_count": data.get("eval_count", 0)
            }
        }
    except Exception as e:
        return {"error": str(e), "raw": "", "latency_ms": time.time() - start}


class AgentJudge:
    """LLM-as-a-Judge for evaluating agent runs."""

    def __init__(self):
        self.system_prompt = SYSTEM_JUDGE

    def judge(
        self,
        question: str,
        agent_result: dict,
        expected_result: Optional[dict] = None
    ) -> dict:
        """Judge a single agent run.

        Args:
            question: The original question
            agent_result: Result from AegisAgent.run()
            expected_result: Optional expected result info

        Returns:
            dict with scores, explanation, latency_ms
        """
        steps = agent_result.get("steps", [])
        step_history = format_step_history(steps)
        final_answer = agent_result.get("answer", "N/A")
        expected_text = json.dumps(expected_result, indent=2, default=str)[:1000] if expected_result else "Not specified"

        user_prompt = USER_JUDGE_TEMPLATE.format(
            question=question,
            step_history=step_history,
            final_answer=final_answer,
            expected_result=expected_text
        )

        start = time.time()
        result = call_ollama(user_prompt, system=self.system_prompt)
        latency = (time.time() - start) * 1000

        if "error" in result:
            return {
                "scores": {
                    "cypher_correctness": 1,
                    "query_effectiveness": 1,
                    "feedback_loop_benefit": 1,
                    "tool_usage": 1,
                    "reasoning_quality": 1
                },
                "explanation": f"Judge error: {result['error']}",
                "latency_ms": latency,
                "tokens": {},
                "error": result["error"]
            }

        raw = result["raw"].strip()

        # Parse JSON from response
        raw = re.sub(r"^```json\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"^```\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        raw = raw.strip()

        try:
            parsed = json.loads(raw)
            scores = parsed.get("scores", {})
            explanation = parsed.get("explanation", "")

            def clamp(val, default=3):
                try:
                    v = int(val)
                    return max(1, min(5, v))
                except (ValueError, TypeError):
                    return default

            return {
                "scores": {
                    "cypher_correctness": clamp(scores.get("cypher_correctness"), 3),
                    "query_effectiveness": clamp(scores.get("query_effectiveness"), 3),
                    "feedback_loop_benefit": clamp(scores.get("feedback_loop_benefit"), 3),
                    "tool_usage": clamp(scores.get("tool_usage"), 3),
                    "reasoning_quality": clamp(scores.get("reasoning_quality"), 3)
                },
                "explanation": explanation,
                "latency_ms": latency,
                "tokens": result.get("tokens", {}),
                "error": None
            }
        except json.JSONDecodeError:
            return {
                "scores": {
                    "cypher_correctness": 3,
                    "query_effectiveness": 3,
                    "feedback_loop_benefit": 3,
                    "tool_usage": 3,
                    "reasoning_quality": 3
                },
                "explanation": f"Failed to parse judge JSON. Raw: {raw[:500]}",
                "latency_ms": latency,
                "tokens": result.get("tokens", {}),
                "error": "JSON parse failed"
            }


def judge_agent_run(question: str, agent_result: dict, expected_result: Optional[dict] = None) -> dict:
    """Convenience function for judging an agent run."""
    judge = AgentJudge()
    return judge.judge(question, agent_result, expected_result)


if __name__ == "__main__":
    test_question = "How many clauses does GDPR have?"
    test_result = {
        "answer": "GDPR has 28 clauses.",
        "cypher": "MATCH (r:Regulation {regulationId: 'GDPR'})-[:HAS_CLAUSE]->(c:Clause) RETURN count(c) AS clauseCount;",
        "steps": [
            {
                "attempt": 1,
                "success": True,
                "cypher": "MATCH (r:Regulation {regulationId: 'GDPR'})-[:HAS_CLAUSE]->(c:Clause) RETURN count(c) AS clauseCount;",
                "error": None,
                "results": [{"clauseCount": 28}],
                "row_count": 1,
                "latency_ms": 150,
                "refined": False
            }
        ],
        "success": True,
        "attempt_count": 1
    }
    test_expected = {"row_count": 1, "columns": ["clauseCount"]}

    print("Testing judge...")
    scores = judge_agent_run(test_question, test_result, test_expected)
    print(f"Scores: {scores['scores']}")
    print(f"Explanation: {scores['explanation']}")
    print(f"Latency: {scores['latency_ms']:.0f}ms")
