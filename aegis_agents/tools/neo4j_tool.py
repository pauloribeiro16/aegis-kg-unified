"""Neo4j tool for LangChain agent."""

import re
import time
from typing import Any, Optional

import requests
from langchain_core.tools import tool

from aegis_agents.config import NEO4J_CONFIG


def exec_cypher(statement: str, params: dict = None) -> dict:
    """Execute Cypher against Neo4j and return results."""
    url = f"{NEO4J_CONFIG['http_url']}/db/{NEO4J_CONFIG['database']}/tx/commit"
    auth = (NEO4J_CONFIG["user"], NEO4J_CONFIG["password"])
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}

    try:
        resp = requests.post(url, auth=auth, json=payload, timeout=60)
        if resp.status_code != 200:
            return {
                "error": f"HTTP {resp.status_code}",
                "results": [],
                "data": [],
                "cypher": statement
            }
        result = resp.json()
        if result.get("errors"):
            return {
                "error": result["errors"][0]["message"],
                "results": [],
                "data": [],
                "cypher": statement
            }
        rows = []
        for res in result.get("results", []):
            if "data" in res:
                cols = res.get("columns", [])
                for row in res["data"]:
                    rows.append(dict(zip(cols, row["row"])))
        return {
            "error": None,
            "results": result.get("results", []),
            "data": rows,
            "row_count": len(rows),
            "cypher": statement
        }
    except Exception as e:
        return {
            "error": str(e),
            "results": [],
            "data": [],
            "cypher": statement
        }


def extract_cypher(raw_output: str) -> Optional[str]:
    """Extract the first valid Cypher statement from LLM output."""
    lines = raw_output.strip().split("\n")
    cypher_lines = []
    in_cypher = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("MATCH") or stripped.startswith("RETURN") or \
           stripped.startswith("CREATE") or stripped.startswith("MERGE") or \
           stripped.startswith("WITH") or stripped.startswith("UNWIND"):
            in_cypher = True
        if in_cypher:
            cypher_lines.append(stripped)
            if ";" in line:
                break

    cypher = " ".join(cypher_lines)
    cypher = re.sub(r"^MATCH", "MATCH", cypher)
    cypher = re.sub(r"^RETURN", "RETURN", cypher)

    if not cypher or len(cypher) < 10:
        return None

    if "MATCH" not in cypher and "RETURN" not in cypher:
        return None

    if ";" not in cypher:
        cypher += ";"

    return cypher


@tool
def cypher_query(question: str, schema_context: str) -> dict:
    """Execute a Cypher query against the AEGIS Neo4j knowledge graph.

    Takes a natural language question, generates a Cypher query using the provided
    schema context, executes it, and returns the results or an error message.

    Args:
        question: The natural language question to answer
        schema_context: The Neo4j schema description to use for query generation

    Returns:
        A dictionary with:
        - success: bool indicating if query succeeded
        - cypher: the generated Cypher query
        - data: list of result rows (if successful)
        - row_count: number of result rows
        - error: error message (if failed)
        - raw_response: the raw LLM response
    """
    from aegis_agents.config import OLLAMA_CONFIG

    url = f"{OLLAMA_CONFIG['base_url']}/api/generate"
    system_prompt = """You are a Neo4j Cypher expert. Given a question in natural language about the AEGIS regulatory knowledge graph, generate a valid Cypher query.

IMPORTANT RULES:
1. Only output the Cypher query — no explanations, no markdown, no commentary.
2. Use the schema provided. Node labels are: Regulation, Article, Clause, Domain, SubDomain, ComplementarityAnalysis, Framework, FrameworkCategory, FrameworkControl
3. Relationship types: HAS_ARTICLE, HAS_CLAUSE, DEFINES, HAS_SUBDOMAIN, MAPPED_TO, OVERLAPS_WITH, HAS_CATEGORY, HAS_CONTROL, MAPS_TO_SUBDOMAIN, MAPS_TO_DOMAIN
4. Property names match exactly as defined in the schema.
5. For the SubDomain ID format use 'D-01-1' (D-XX-Y with leading zeros dropped).
6. For clause IDs use format like 'GDPR-C01', 'CRA-C07', etc.
7. For regulation IDs use 'GDPR', 'CRA', 'NIS2', 'DORA', 'AIAct'.
8. If the question is ambiguous, pick the most logical interpretation.
"""

    user_prompt = f"""SCHEMA:
{schema_context}

QUESTION: {question}

Generate the Cypher query:"""

    payload = {
        "model": OLLAMA_CONFIG["model"],
        "prompt": user_prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 512,
            "stop": ["\n\n", "---", "##"]
        }
    }

    start = time.time()
    try:
        resp = requests.post(url, json=payload, timeout=OLLAMA_CONFIG["timeout"])
        elapsed = (time.time() - start) * 1000

        if resp.status_code != 200:
            return {
                "success": False,
                "cypher": None,
                "data": [],
                "row_count": 0,
                "error": f"Ollama HTTP {resp.status_code}",
                "raw_response": resp.text[:500],
                "latency_ms": elapsed
            }

        data = resp.json()
        raw = data.get("response", "")

        cypher = extract_cypher(raw)
        if not cypher:
            return {
                "success": False,
                "cypher": raw,
                "data": [],
                "row_count": 0,
                "error": "Failed to extract valid Cypher from LLM output",
                "raw_response": raw,
                "latency_ms": elapsed
            }

        result = exec_cypher(cypher)
        if result.get("error"):
            return {
                "success": False,
                "cypher": cypher,
                "data": [],
                "row_count": 0,
                "error": result["error"],
                "raw_response": raw,
                "latency_ms": elapsed
            }

        return {
            "success": True,
            "cypher": cypher,
            "data": result["data"],
            "row_count": result["row_count"],
            "error": None,
            "raw_response": raw,
            "latency_ms": elapsed
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "cypher": None,
            "data": [],
            "row_count": 0,
            "error": "Timeout calling Ollama",
            "raw_response": "",
            "latency_ms": (time.time() - start) * 1000
        }
    except Exception as e:
        return {
            "success": False,
            "cypher": None,
            "data": [],
            "row_count": 0,
            "error": str(e),
            "raw_response": "",
            "latency_ms": (time.time() - start) * 1000
        }


def get_neo4j_tool():
    """Get the configured Neo4j tool for LangChain agent."""
    return cypher_query
