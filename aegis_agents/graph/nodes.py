"""LangGraph nodes for Aegis agent with feedback loop."""

import re
import time
import requests

from aegis_agents.config import OLLAMA_CONFIG
from aegis_agents.graph.prompts import get_prompt
from aegis_agents.graph.state import AgentState
from aegis_agents.tools.schema_tool import SCHEMA_DESCRIPTION
from aegis_agents.tracing import log_generation
from aegis_agents.circuit_breaker import neo4j_cb, CircuitOpenError
from aegis_agents.query_linter import validate_cypher
from aegis_agents.fallback_queries import find_fallback


def extract_cypher(raw_output: str) -> str | None:
    """Extract the first valid Cypher statement from LLM output.

    ministral-3 produces explanatory text alongside Cypher. This function:
    1. Strips think tags and markdown fences
    2. Finds the first line starting with a Cypher keyword
    3. Collects subsequent lines that are pure Cypher (no normal English sentences)
    4. Stops when a line contains common English explanation patterns
    """
    raw_output = re.sub(r"<think[\s\S]*?</think\s*>", "", raw_output, flags=re.IGNORECASE)
    raw_output = raw_output.strip()

    raw_output = re.sub(r"```cypher\s*", "", raw_output, flags=re.IGNORECASE)
    raw_output = re.sub(r"```\s*", "", raw_output)

    ENGLISH_STOP = re.compile(
        r'\b(This query|will return|provides|gives you|shows|you can use|'
        r'count of|number of|all distinct|if you want|based on your|'
        r'in the graph|alternatively|for example|to get the|'
        r'which means|here is|layout)\b',
        re.IGNORECASE
    )

    lines = raw_output.split("\n")
    cypher_lines = []
    found_start = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if not found_start:
            if re.match(r'^\s*(MATCH|RETURN|CREATE|MERGE|WITH|UNWIND)\b', stripped, re.IGNORECASE):
                found_start = True
                cypher_lines.append(stripped)
        else:
            if ENGLISH_STOP.search(stripped):
                break
            cypher_lines.append(stripped)
            if stripped.endswith(";"):
                break

    if not cypher_lines:
        return None

    cypher = " ".join(cypher_lines)
    cypher = re.sub(r"`+", "", cypher)
    cypher = cypher.strip()

    if not cypher or len(cypher) < 10:
        return None
    if "MATCH" not in cypher and "RETURN" not in cypher:
        return None
    if not cypher.endswith(";"):
        cypher += ";"

    return cypher


def exec_cypher(statement: str, params: dict = None, verbose: bool = False) -> dict:
    """Execute Cypher against Neo4j with circuit breaker and linter."""
    is_valid, reason = validate_cypher(statement)
    if not is_valid:
        if verbose:
            print(f"[agent] Linter REJECTED: {reason}", flush=True)
        return {"error": f"Query rejected: {reason}", "data": [], "row_count": 0}

    if neo4j_cb.is_open:
        if verbose:
            print(f"[agent] Circuit breaker OPEN — Neo4j unavailable", flush=True)
        return {"error": "Circuit breaker OPEN — Neo4j unavailable", "data": [], "row_count": 0}

    import requests as req
    from aegis_agents.config import NEO4J_CONFIG

    url = f"{NEO4J_CONFIG['http_url']}/db/{NEO4J_CONFIG['database']}/tx/commit"
    auth = (NEO4J_CONFIG["user"], NEO4J_CONFIG["password"])
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}

    try:
        resp = req.post(url, auth=auth, json=payload, timeout=10)
        if resp.status_code != 200:
            neo4j_cb._on_failure()
            return {"error": f"HTTP {resp.status_code}", "data": [], "row_count": 0}
        result = resp.json()
        if result.get("errors"):
            return {"error": result["errors"][0]["message"], "data": [], "row_count": 0}
        rows = []
        for res in result.get("results", []):
            if "data" in res:
                cols = res.get("columns", [])
                for row in res["data"]:
                    rows.append(dict(zip(cols, row["row"])))
        neo4j_cb._on_success()
        return {"error": None, "data": rows, "row_count": len(rows)}
    except Exception as e:
        neo4j_cb._on_failure()
        return {"error": str(e), "data": [], "row_count": 0}


def generate_and_execute(state: AgentState) -> AgentState:
    """Generate Cypher query and execute it in one step.

    Node: generate_and_execute
    Type: LLM (generation) + Tool (execution)
    """
    question = state["question"]
    attempt = state.get("attempt", 1)
    previous_cypher = state.get("cypher")
    previous_error = None
    verbose = state.get("verbose", False)

    if state.get("steps"):
        last_step = state["steps"][-1]
        previous_error = last_step.get("error")
        previous_cypher = last_step.get("cypher")

    if attempt >= state.get("max_attempts", 3):
        fallback_cypher = find_fallback(question)
        if fallback_cypher:
            result = exec_cypher(fallback_cypher, verbose=verbose)
            if result.get("row_count", 0) > 0:
                if verbose:
                    print(f"[agent] FALLBACK triggered: {fallback_cypher[:100]}", flush=True)
                step = {
                    "attempt": attempt,
                    "cypher": fallback_cypher,
                    "error": None,
                    "data": result.get("data", []),
                    "row_count": result.get("row_count", 0),
                    "latency_ms": 0,
                    "fallback": True,
                }
                log_generation(
                    name="fallback_query",
                    input_data={"question": question, "fallback": True},
                    output_data={"cypher": fallback_cypher, "row_count": result.get("row_count", 0)},
                    model="fallback-template",
                    latency_ms=0,
                    metadata={"attempt": attempt, "task": "fallback"}
                )
                return {
                    "steps": state.get("steps", []) + [step],
                    "attempt": attempt + 1,
                    "cypher": fallback_cypher,
                    "fallback_used": True,
                }

    if attempt == 1:
        prompt = get_prompt("cypher_generation", schema=SCHEMA_DESCRIPTION, question=question)
    else:
        prompt = get_prompt(
            "refinement",
            previous_cypher=previous_cypher or "N/A",
            error=previous_error or "Empty results",
            schema=SCHEMA_DESCRIPTION,
            question=question,
        )

    if verbose:
        print(f"[agent] Attempt {attempt}: Calling Ollama...", flush=True)

    url = f"{OLLAMA_CONFIG['base_url']}/api/generate"
    payload = {
        "model": OLLAMA_CONFIG["model"],
        "prompt": prompt,
        "system": "You are a Neo4j Cypher query generator. Output ONLY the Cypher query. No explanations, no markdown, no commentary. Start with MATCH.",
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 2500}
    }

    start = time.time()
    try:
        resp = requests.post(url, json=payload, timeout=OLLAMA_CONFIG["timeout"])
        elapsed = (time.time() - start) * 1000

        if resp.status_code != 200:
            if verbose:
                print(f"[agent] Ollama HTTP {resp.status_code} ({elapsed/1000:.1f}s)", flush=True)
            step = {
                "attempt": attempt,
                "cypher": None,
                "error": f"Ollama HTTP {resp.status_code}",
                "data": [],
                "row_count": 0,
                "latency_ms": elapsed,
            }
            return {"steps": state.get("steps", []) + [step], "attempt": attempt + 1}

        data = resp.json()
        raw = data.get("response", "")

        cypher = extract_cypher(raw)
        if not cypher:
            if verbose:
                print(f"[agent] Ollama FAILED: couldn't extract Cypher ({elapsed/1000:.1f}s)", flush=True)
            step = {
                "attempt": attempt,
                "cypher": raw[:200],
                "error": "Failed to extract valid Cypher",
                "data": [],
                "row_count": 0,
                "latency_ms": elapsed,
            }
            return {"steps": state.get("steps", []) + [step], "attempt": attempt + 1}

        if verbose:
            print(f"[agent] Ollama ({elapsed/1000:.1f}s): {cypher[:120]}", flush=True)

        result = exec_cypher(cypher, verbose=verbose)
        if verbose:
            print(f"[agent] Cypher exec: rows={result.get('row_count', 0)}, error={result.get('error')}", flush=True)

        step = {
            "attempt": attempt,
            "cypher": cypher,
            "error": result.get("error"),
            "data": result.get("data", []),
            "row_count": result.get("row_count", 0),
            "latency_ms": elapsed,
        }

        # Log cypher generation to Langfuse
        log_generation(
            name="cypher_generation",
            input_data={"question": question, "attempt": attempt},
            output_data={
                "cypher": cypher,
                "raw": raw[:500] if raw else "",
                "error": step.get("error"),
                "row_count": step.get("row_count", 0)
            },
            model=OLLAMA_CONFIG["model"],
            latency_ms=elapsed,
            metadata={"attempt": attempt, "task": "cypher_generation"}
        )

        return {"steps": state.get("steps", []) + [step], "attempt": attempt + 1, "cypher": cypher}

    except Exception as e:
        if verbose:
            print(f"[agent] Exception: {str(e)}", flush=True)
        step = {
            "attempt": attempt,
            "cypher": None,
            "error": str(e),
            "data": [],
            "row_count": 0,
        }
        return {"steps": state.get("steps", []) + [step], "attempt": attempt + 1}


def evaluate_and_decide(state: AgentState) -> AgentState:
    """Evaluate result and decide next action.

    Node: evaluate_and_decide
    Type: Decision point
    """
    steps = state.get("steps", [])
    if not steps:
        return state

    verbose = state.get("verbose", False)
    last_step = steps[-1]
    success = last_step.get("error") is None and last_step.get("row_count", 0) > 0
    row_count = last_step.get("row_count", 0)

    if verbose:
        from aegis_agents.graph.router import should_continue
        next_node = should_continue(state)
        print(f"[agent] Decision: success={success}, rows={row_count} -> {next_node}", flush=True)

    return {"success": success}


def generate_answer(state: AgentState) -> AgentState:
    """Generate natural language answer from query results.

    Node: generate_answer
    Type: LLM (generation)
    """
    question = state["question"]
    steps = state.get("steps", [])
    verbose = state.get("verbose", False)

    best_step = None
    for step in reversed(steps):
        if step.get("row_count", 0) > 0:
            best_step = step
            break

    if not best_step:
        answer = "No results found for your query."
        return {"answer": answer, "success": False}

    data = best_step.get("data", [])
    if not data:
        answer = "No results found for your query."
        return {"answer": answer, "success": False}

    row_count = best_step.get("row_count", len(data))
    cypher = best_step.get("cypher", "N/A")

    if verbose:
        print(f"[agent] Generating answer from {row_count} rows...", flush=True)

    results_text = "\n".join(
        [", ".join(f"{k}={v}" for k, v in row.items() if v is not None) for row in data[:20]]
    )
    if len(data) > 20:
        results_text += f"\n... and {len(data) - 20} more rows"

    prompt = get_prompt("answer_generation", question=question, cypher=cypher, row_count=row_count, results_text=results_text)

    url = f"{OLLAMA_CONFIG['base_url']}/api/generate"
    payload = {
        "model": OLLAMA_CONFIG["model"],
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 1024}
    }

    try:
        start = time.time()
        resp = requests.post(url, json=payload, timeout=OLLAMA_CONFIG["timeout"])
        elapsed = (time.time() - start) * 1000

        if resp.status_code != 200:
            return {"answer": f"Error generating answer: Ollama HTTP {resp.status_code}"}

        data = resp.json()
        answer = data.get("response", "").strip()

        if verbose:
            print(f"[agent] Answer ({elapsed/1000:.1f}s): {answer[:150]}...", flush=True)

        # Log answer generation to Langfuse
        log_generation(
            name="answer_generation",
            input_data={"question": question, "results": results_text},
            output_data={"answer": answer},
            model=OLLAMA_CONFIG["model"],
            latency_ms=0,
            metadata={"task": "answer_generation"}
        )

        return {"answer": answer, "success": True}

    except Exception as e:
        return {"answer": f"Error generating answer: {str(e)}", "success": False}
