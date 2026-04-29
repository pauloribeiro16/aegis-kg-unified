#!/usr/bin/env python3
"""
text2cypher.py — Generate Cypher queries from natural language questions using Ollama.

Usage:
    from text2cypher import generate_cypher

    result = generate_cypher("How many clauses does GDPR have?")
    # {'cypher': 'MATCH ...', 'raw': '...', 'latency_ms': 1234, 'tokens': {...}}
"""

import re
import time
import requests
from typing import Optional

from aegis_eval.config import OLLAMA
from aegis_eval.schema_context import get_schema_context


SYSTEM_PROMPT = """You are a Neo4j Cypher expert. Given a question in natural language about the AEGIS regulatory knowledge graph, generate a valid Cypher query.

IMPORTANT RULES:
1. Only output the Cypher query — no explanations, no markdown, no commentary.
2. Use the schema provided. Node labels are: Regulation, Article, Clause, Domain, SubDomain, ComplementarityAnalysis
3. Relationship types: HAS_ARTICLE, HAS_CLAUSE, DEFINES, HAS_SUBDOMAIN, MAPPED_TO, OVERLAPS_WITH
4. Property names match exactly as defined in the schema.
5. For the SubDomain ID format use 'D-01-1' (D-XX-Y with leading zeros dropped).
6. For clause IDs use format like 'GDPR-C01', 'CRA-C07', etc.
7. For regulation IDs use 'GDPR', 'CRA', 'NIS2', 'DORA', 'AIAct'.
8. If the question is ambiguous, pick the most logical interpretation.
"""

USER_PROMPT_TEMPLATE = """SCHEMA:
{schema}

QUESTION: {question}

Generate the Cypher query:"""


def call_ollama(prompt: str, system: str = "") -> dict:
    """Call Ollama API and return response with metadata."""
    url = f"{OLLAMA['base_url']}/api/generate"
    payload = {
        "model": OLLAMA["model"],
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 512,
            "stop": ["\n\n", "---", "##"]
        }
    }
    start = time.time()
    try:
        resp = requests.post(url, json=payload, timeout=OLLAMA["timeout"])
        elapsed = (time.time() - start) * 1000
        if resp.status_code != 200:
            return {
                "error": f"Ollama HTTP {resp.status_code}",
                "raw": resp.text[:500],
                "latency_ms": elapsed,
                "tokens": {}
            }
        data = resp.json()
        return {
            "raw": data.get("response", ""),
            "latency_ms": elapsed,
            "tokens": {
                "prompt_eval_count": data.get("prompt_eval_count", 0),
                "eval_count": data.get("eval_count", 0)
            }
        }
    except requests.exceptions.Timeout:
        return {"error": "Timeout", "raw": "", "latency_ms": elapsed, "tokens": {}}
    except Exception as e:
        return {"error": str(e), "raw": "", "latency_ms": time.time() - start, "tokens": {}}


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


def generate_cypher(question: str, schema_ctx: Optional[str] = None) -> dict:
    """
    Generate a Cypher query from a natural language question.

    Returns:
        {
            'cypher': str,          # Extracted Cypher query
            'raw': str,             # Raw LLM output
            'latency_ms': float,
            'tokens': dict,
            'error': str or None
        }
    """
    if schema_ctx is None:
        schema_ctx = get_schema_context()

    user_prompt = USER_PROMPT_TEMPLATE.format(schema=schema_ctx, question=question)

    result = call_ollama(user_prompt, system=SYSTEM_PROMPT)

    if "error" in result:
        return {**result, "cypher": None}

    raw = result["raw"]
    cypher = extract_cypher(raw)

    return {
        "cypher": cypher,
        "raw": raw,
        "latency_ms": result["latency_ms"],
        "tokens": result.get("tokens", {}),
        "error": None if cypher else "Failed to extract Cypher from output"
    }


def generate_answer(question: str, results: list[dict], schema_ctx: Optional[str] = None) -> dict:
    """
    Generate a natural language answer from question + Neo4j results.
    """
    if not results:
        results_text = "No results found."
    else:
        lines = []
        for row in results[:10]:
            lines.append(", ".join(f"{k}={v}" for k, v in row.items()))
        results_text = "\n".join(lines)
        if len(results) > 10:
            results_text += f"\n... and {len(results) - 10} more rows"

    user_prompt = f"""You are a regulatory compliance expert answering questions about EU regulations.

SCHEMA CONTEXT:
{schema_ctx or get_schema_context()}

QUESTION: {question}

DATABASE RESULTS:
{results_text}

Provide a clear, concise answer based on the results. If results are empty or insufficient, say so."""

    SYSTEM_ANSWER = """You are a regulatory compliance expert. Answer based on the provided database results. Be precise and cite specific regulation names, clause IDs, and counts when available."""

    result = call_ollama(user_prompt, system=SYSTEM_ANSWER)

    return {
        "answer": result["raw"],
        "latency_ms": result["latency_ms"],
        "tokens": result.get("tokens", {}),
        "error": result.get("error")
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = "How many clauses does GDPR have?"

    print(f"Question: {question}")
    result = generate_cypher(question)
    print(f"Cypher: {result['cypher']}")
    print(f"Latency: {result['latency_ms']:.0f}ms")
    print(f"Tokens: {result['tokens']}")
    if result.get("error"):
        print(f"Error: {result['error']}")