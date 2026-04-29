#!/usr/bin/env python3
"""
judge_prompts.py — Evaluation prompts for Minimax LLM-as-a-Judge.

Evaluates 5 dimensions, each scoring BOTH the query (Cypher) and the answer (LLM response):
- cypher_correctness: Syntax and semantic validity
- query_effectiveness: Intent alignment
- feedback_loop_benefit: Improvement across attempts
- tool_usage: Correct use of Neo4j exec_cypher
- reasoning_quality: Logical soundness

Usage:
    from judge_prompts import get_evaluation_prompt

    prompt = get_evaluation_prompt(task, agent_result)
"""

SYSTEM_JUDGE = """You are an expert evaluator for regulatory compliance knowledge graph queries.

You will evaluate both the Cypher QUERY generated and the LLM ANSWER provided.

For each dimension, you must score TWO aspects:
1. QUERY score - The quality of the Cypher query itself
2. ANSWER score - How well the LLM answer was generated from the query results

## SCORING RUBRIC (be strict and consistent)

### CYPHER_CORRECTNESS
1 = Syntax errors, query won't execute
2 = Executes but wrong node types, relationships, or properties
3 = Executes with correct node types but missing/extra properties or wrong aliases
4 = Correct query with minor formatting or ordering issues
5 = Perfect — valid syntax, correct node types, proper properties and relationships

### QUERY_EFFECTIVENESS
1 = Completely unrelated to the user's question
2 = Partially addresses the question but misses key aspects or returns wrong data
3 = Addresses the question but returns extra/irrelevant data or suboptimal structure
4 = Precisely addresses the question with minor optimization possible
5 = Perfect — optimal and efficient query that exactly matches user intent

### FEEDBACK_LOOP_BENEFIT
For single attempt: Score 3 for both query and answer.
For multiple attempts:
1 = No improvement despite retries (same or worse errors)
2 = Minor improvement but still significant issues
3 = Moderate improvement, some issues remain
4 = Good improvement, minor refinements still needed
5 = Excellent — query/answer significantly improved or already optimal

### TOOL_USAGE
1 = Tool (exec_cypher) not used or called with wrong parameters causing errors
2 = Tool used but query had errors requiring retry
3 = Tool used correctly, results processed adequately
4 = Tool used correctly with good result processing
5 = Tool used optimally, results fully and accurately processed with no issues

### REASONING_QUALITY
1 = No logical connection between query and question; answer contradicts results
2 = Weak reasoning, significant logical gaps between query and results
3 = Acceptable reasoning but could be more precise or complete
4 = Strong reasoning with minor gaps or omissions
5 = Perfect — sound logic, complete alignment between query, results, and answer

## IMPORTANT RULES
- Be STRICT: A score of 5 means NO issues whatsoever
- Compare the GENERATED CYPHER against the EXPECTED CYPHER to assess correctness
- Check if the ANSWER correctly reflects the DATABASE RESULTS
- Do NOT assume external knowledge — evaluate only what is provided
- For ambiguous cases, score LOWER (3 or below) rather than higher
- A score of 5 should be rare and earned only when everything is perfect"""


USER_EVALUATION_TEMPLATE = """## TASK
{question}

## EXPECTED CYPHER (for reference)
{expected_cypher}

## EXPECTED RESULT (for reference)
{expected_result}

## ATTEMPT HISTORY
{attempt_history}

## GENERATED CYPHER (final attempt)
{cypher}

## DATABASE RESULT
{db_result}

## LLM ANSWER
{llm_answer}

## YOUR EVALUATION

Evaluate the query and answer across these 5 dimensions using the rubric above:

### 1. CYPHER_CORRECTNESS
- QUERY: Is the Cypher syntactically valid? Does it reference valid node types, relationships, and properties? Compare against expected Cypher.
- ANSWER: Is the answer consistent with the query results? Does it correctly reflect what was returned?

### 2. QUERY_EFFECTIVENESS
- QUERY: Does the query address what the user actually asked? Does it match the user's intent?
- ANSWER: Does the answer properly convey what the query found in a way that addresses the question?

### 3. FEEDBACK_LOOP_BENEFIT
- QUERY: If multiple attempts, did the query improve? (Default 3 for single attempt)
- ANSWER: If multiple attempts, did the answer improve? (Default 3 for single attempt)

### 4. TOOL_USAGE
- QUERY: Was exec_cypher used correctly? Were correct parameters passed?
- ANSWER: Does the answer reference the actual data? Or does it hallucinate?

### 5. REASONING_QUALITY
- QUERY: Is the query logic sound? Does the MATCH/WHERE logic make sense?
- ANSWER: Does the answer reasoning justify its conclusions?

## OUTPUT FORMAT (JSON only, no markdown)

Return a single JSON object with no additional text:

{{
  "cypher_correctness": {{
    "query": <int 1-5>,
    "answer": <int 1-5>,
    "reasoning": "<explain both query and answer scores, citing specific issues>"
  }},
  "query_effectiveness": {{
    "query": <int 1-5>,
    "answer": <int 1-5>,
    "reasoning": "<explain both scores>"
  }},
  "feedback_loop_benefit": {{
    "query": <int 1-5>,
    "answer": <int 1-5>,
    "reasoning": "<explain, or state 'N/A for single attempt'>"
  }},
  "tool_usage": {{
    "query": <int 1-5>,
    "answer": <int 1-5>,
    "reasoning": "<explain both scores>"
  }},
  "reasoning_quality": {{
    "query": <int 1-5>,
    "answer": <int 1-5>,
    "reasoning": "<explain both scores>"
  }}
}}

Return JSON only. No markdown code blocks. No additional text."""


def format_attempt_history(steps: list[dict]) -> str:
    """Format attempt history for the prompt."""
    if not steps:
        return "Single attempt (no retries)"

    lines = []
    for i, step in enumerate(steps, 1):
        lines.append(f"--- Attempt {i} ---")
        lines.append(f"Cypher: {step.get('cypher', 'N/A')[:200]}")
        if step.get('error'):
            lines.append(f"Error: {step.get('error')}")
        else:
            lines.append(f"Result: {step.get('row_count', 0)} rows")
        lines.append("")

    return "\n".join(lines)


def format_db_results(results: list[dict], max_rows: int = 10) -> str:
    """Format Neo4j results for the prompt."""
    if not results:
        return "EMPTY — No data returned"

    lines = []
    for i, row in enumerate(results[:max_rows], 1):
        line = ", ".join(f"{k}={repr(v)[:40]}" for k, v in row.items())
        lines.append(f"  Row {i}: {line}")

    if len(results) > max_rows:
        lines.append(f"  ... and {len(results) - max_rows} more rows")

    return "\n".join(lines)


def get_evaluation_prompt(task: dict, agent_result: dict) -> tuple[str, str]:
    """
    Build the evaluation prompt for Minimax.

    Args:
        task: Task dict from task_bank.yaml
        agent_result: {
            'cypher': str,           # Final generated Cypher
            'steps': list[dict],     # All attempts with cypher, error, row_count, data
            'answer': str,           # Final LLM answer (also accepts 'llm_answer')
            'success': bool,
            'attempt_count': int
        }

    Returns:
        (system_prompt, user_prompt)
    """
    question = task.get("question", "")
    cypher = agent_result.get("cypher", "")
    steps = agent_result.get("steps", [])

    # Extract db_results from the last successful step (same logic as _build_result in run_eval)
    db_results = []
    if steps:
        # Try last step first, then iterate backwards
        for step in reversed(steps):
            if step.get("data"):
                db_results = step["data"]
                break

    # Handle both "answer" and "llm_answer" field names
    llm_answer = agent_result.get("answer") or agent_result.get("llm_answer", "")

    # Get expected cypher and result for reference
    expected_cypher = task.get("expected_cypher", "Not specified")
    expected_result = task.get("expected_result", {})
    if isinstance(expected_result, dict):
        expected_result_str = f"row_count: {expected_result.get('row_count', 'N/A')}, columns: {expected_result.get('columns', [])}"
    else:
        expected_result_str = str(expected_result)

    attempt_history = format_attempt_history(steps)
    db_result_text = format_db_results(db_results)

    user_prompt = USER_EVALUATION_TEMPLATE.format(
        question=question,
        expected_cypher=expected_cypher,
        expected_result=expected_result_str,
        attempt_history=attempt_history,
        cypher=cypher or "NONE",
        db_result=db_result_text,
        llm_answer=llm_answer or "NONE"
    )

    return SYSTEM_JUDGE, user_prompt


def get_dimension_names() -> list[str]:
    """Return the list of evaluation dimensions."""
    return [
        "cypher_correctness",
        "query_effectiveness",
        "feedback_loop_benefit",
        "tool_usage",
        "reasoning_quality"
    ]


def get_score_subdimensions() -> list[str]:
    """Return the subdimensions for each score (query and answer)."""
    return ["query", "answer"]


if __name__ == "__main__":
    # Test the prompts
    test_task = {
        "id": "test",
        "question": "How many clauses does GDPR have?"
    }

    test_agent_result = {
        "cypher": "MATCH (r:Regulation {regulationId: 'GDPR'})-[:HAS_CLAUSE]->(c:Clause) RETURN count(c) AS clauseCount",
        "steps": [
            {"attempt": 1, "cypher": "MATCH (r:Regulation {regulationId: 'GDPR'}) RETURN count(r)", "row_count": 1, "error": None}
        ],
        "query_result": {"data": [{"clauseCount": 28}], "error": None},
        "llm_answer": "GDPR has 28 clauses.",
        "success": True,
        "attempt_count": 1
    }

    system_prompt, user_prompt = get_evaluation_prompt(test_task, test_agent_result)

    print("=== SYSTEM PROMPT ===")
    print(system_prompt[:500])
    print("\n=== USER PROMPT ===")
    print(user_prompt)