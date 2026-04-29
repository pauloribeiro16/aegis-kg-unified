"""LLM-as-a-Judge scoring for Aegis agent."""

import json
from aegis_agents.config import OLLAMA_CONFIG


def judge_evaluation(
    question: str,
    cypher: str,
    result: dict,
    error: str | None,
) -> dict:
    """Evaluate the agent's performance using LLM-as-a-Judge.

    Returns scores for:
    - cypher_correctness: Is the Cypher correct?
    - query_effectiveness: Would the query return relevant results?
    - feedback_loop_benefit: Would refinement help?
    """
    import requests

    prompt = f"""You are an expert evaluator for a regulatory knowledge graph agent.

Evaluate the following Cypher query and execution result:

QUESTION: {question}
CYPHER: {cypher}
ROW_COUNT: {result.get('row_count', 0) if result else 0}
ERROR: {error or 'None'}

Rate the following aspects on a scale of 1-5:
1. Cypher Correctness: Is the Cypher syntactically correct and semantically appropriate?
2. Query Effectiveness: Would this query likely return relevant results for the question?
3. Feedback Loop Benefit: Would running a refinement feedback loop improve this query?

Output ONLY a JSON object with these three scores:
{{"cypher_correctness": <1-5>, "query_effectiveness": <1-5>, "feedback_loop_benefit": <1-5>}}

Do not include any explanation, only the JSON."""

    url = f"{OLLAMA_CONFIG['base_url']}/api/generate"
    payload = {
        "model": OLLAMA_CONFIG["model"],
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 256,
        }
    }

    try:
        resp = requests.post(url, json=payload, timeout=OLLAMA_CONFIG["timeout"])
        if resp.status_code != 200:
            return _default_scores()

        data = resp.json()
        raw = data.get("response", "")

        scores = _parse_judge_response(raw)
        return scores
    except Exception:
        return _default_scores()


def _parse_judge_response(raw: str) -> dict:
    """Parse judge response into scores."""
    try:
        raw = raw.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        raw = raw.strip()

        parsed = json.loads(raw)

        return {
            "cypher_correctness": _clamp_score(parsed.get("cypher_correctness", 3)),
            "query_effectiveness": _clamp_score(parsed.get("query_effectiveness", 3)),
            "feedback_loop_benefit": _clamp_score(parsed.get("feedback_loop_benefit", 3)),
        }
    except Exception:
        return _default_scores()


def _clamp_score(value, min_val=1, max_val=5):
    """Clamp score to 1-5 range."""
    try:
        score = int(value)
        return max(min_val, min(max_val, score))
    except (ValueError, TypeError):
        return 3


def _default_scores() -> dict:
    """Return default scores on error."""
    return {
        "cypher_correctness": 3,
        "query_effectiveness": 3,
        "feedback_loop_benefit": 3,
    }


def score_trace(langfuse, trace_id: str, scores: dict, observation_id: str = None):
    """Score a trace in Langfuse."""
    if not langfuse or not trace_id:
        return

    try:
        for score_name, score_value in scores.items():
            langfuse.create_score(
                trace_id=trace_id,
                observation_id=observation_id,
                name=score_name,
                value=score_value,
                data_type="NUMERIC",
            )
        langfuse.flush()
    except Exception as e:
        print(f"  [Langfuse] Score error: {e}")
