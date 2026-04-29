"""Query refinement utilities for feedback loops."""

import time
from typing import Optional

import requests

from aegis_agents.config import OLLAMA_CONFIG


class QueryRefiner:
    """LLM-based query refinement for failed or empty Cypher queries."""

    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts

    def refine_on_error(self, question: str, cypher: str, error: str, schema_context: str) -> str:
        """Generate a refined Cypher query based on an error message.

        Args:
            question: The original natural language question
            cypher: The failed Cypher query
            error: The error message from Neo4j
            schema_context: The schema description

        Returns:
            A refined Cypher query string
        """
        system_prompt = """You are a Neo4j Cypher expert specializing in debugging and refining queries.

Given a failed Cypher query, an error message, and the original question, generate a FIXED Cypher query.

IMPORTANT:
1. Only output the corrected Cypher query — no explanations
2. Study the error message carefully
3. Check property names, relationship types, and node labels against the schema
4. If the error is about syntax, fix the syntax
5. If the error is about missing labels/properties, adjust the query
6. Keep the same semantic intent as the original query
"""

        user_prompt = f"""SCHEMA:
{schema_context}

ORIGINAL QUESTION: {question}

FAILED CYPHER:
{cypher}

ERROR MESSAGE:
{error}

Generate a FIXED Cypher query:"""

        return self._call_llm(user_prompt, system_prompt)

    def refine_on_empty(
        self, question: str, cypher: str, schema_context: str
    ) -> str:
        """Generate a refined Cypher query when results are empty.

        Args:
            question: The original natural language question
            cypher: The query that returned no results
            schema_context: The schema description

        Returns:
            A refined Cypher query string
        """
        system_prompt = """You are a Neo4j Cypher expert specializing in query debugging.

Given a Cypher query that returned NO RESULTS and the original question, generate an ALTERNATIVE Cypher query that might return results.

IMPORTANT:
1. Only output the Cypher query — no explanations
2. Consider: empty results might mean wrong node labels, wrong property names, wrong relationship directions
3. Try alternative patterns that capture the same intent
4. Check ID formats and property names carefully
5. Consider using OPTIONAL MATCH or checking different relationship directions
"""

        user_prompt = f"""SCHEMA:
{schema_context}

ORIGINAL QUESTION: {question}

QUERY WITH NO RESULTS:
{cypher}

The query executed without error but returned 0 rows. Generate an ALTERNATIVE Cypher query:"""

        return self._call_llm(user_prompt, system_prompt)

    def refine_on_mismatch(
        self, question: str, cypher: str, results: list, intent: str, schema_context: str
    ) -> str:
        """Generate a refined Cypher query when results don't match intent.

        Args:
            question: The original natural language question
            cypher: The query that was executed
            results: The results returned (for analysis)
            intent: Description of what was expected vs what was received
            schema_context: The schema description

        Returns:
            A refined Cypher query string
        """
        results_text = "\n".join(
            [", ".join(f"{k}={v}" for k, v in row.items()) for row in results[:5]]
        )
        if len(results) > 5:
            results_text += f"\n... and {len(results) - 5} more rows"

        system_prompt = """You are a Neo4j Cypher expert specializing in query debugging.

Given a Cypher query, its results, and a description of how the results mismatch the intended answer, generate a CORRECTED Cypher query.

IMPORTANT:
1. Only output the Cypher query — no explanations
2. Analyze what the results show vs what was asked
3. Adjust the query to match the original intent
4. Check MATCH patterns, WHERE clauses, and RETURN statements
"""

        user_prompt = f"""SCHEMA:
{schema_context}

ORIGINAL QUESTION: {question}

QUERY:
{cypher}

RESULTS RETURNED:
{results_text}

MISMATCH DESCRIPTION:
{intent}

Generate a CORRECTED Cypher query:"""

        return self._call_llm(user_prompt, system_prompt)

    def suggest_alternatives(self, question: str, schema_context: str) -> list[str]:
        """Suggest alternative query approaches for a question.

        Args:
            question: The natural language question
            schema_context: The schema description

        Returns:
            A list of alternative Cypher query approaches
        """
        system_prompt = """You are a Neo4j Cypher expert. For the given question, suggest 2-3 DIFFERENT Cypher query approaches that could answer it.

IMPORTANT:
1. Output ONLY the Cypher queries, one per line
2. Each query should be a complete, valid Cypher statement ending with ;
3. The queries should represent meaningfully different approaches (different MATCH patterns, different relationship traversals, etc.)
4. No explanations, no numbering, just the queries
"""

        user_prompt = f"""SCHEMA:
{schema_context}

QUESTION: {question}

Generate 2-3 alternative Cypher queries (one per line):"""

        response = self._call_llm(user_prompt, system_prompt)
        queries = [q.strip() for q in response.split(";") if q.strip()]
        return [q + ";" if not q.endswith(";") else q for q in queries]

    def _call_llm(self, user_prompt: str, system_prompt: str) -> str:
        """Make a single call to Ollama."""
        url = f"{OLLAMA_CONFIG['base_url']}/api/generate"
        payload = {
            "model": OLLAMA_CONFIG["model"],
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 512,
                "stop": ["\n\n", "---", "##"]
            }
        }

        start = time.time()
        try:
            resp = requests.post(url, json=payload, timeout=OLLAMA_CONFIG["timeout"])
            elapsed = (time.time() - start) * 1000

            if resp.status_code != 200:
                return f"// Error calling Ollama: HTTP {resp.status_code}"

            data = resp.json()
            return data.get("response", "")
        except Exception as e:
            return f"// Error: {str(e)}"
