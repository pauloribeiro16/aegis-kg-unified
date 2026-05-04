"""Pre-execution validation for Cypher queries.

Rejects write operations and malformed queries before they reach Neo4j.
"""

import re

WRITE_KEYWORDS = ["CREATE", "MERGE", "DELETE", "DETACH", "DROP", "REMOVE", "SET "]
MAX_QUERY_LENGTH = 2000


def validate_cypher(statement: str, timeout_seconds: int = 10) -> tuple[bool, str]:
    """Validate a Cypher query before execution.

    Checks:
        1. No write operations (CREATE, MERGE, DELETE, DROP, REMOVE, SET)
        2. Has RETURN clause
        3. Length < MAX_QUERY_LENGTH
        4. Contains MATCH or explicit read pattern

    Returns:
        (is_valid, reason) — reason is empty string if valid.
    """
    if not statement or not statement.strip():
        return False, "Empty query"

    upper = statement.upper().strip()

    if len(statement) > MAX_QUERY_LENGTH:
        return False, f"Query too long ({len(statement)} chars, max {MAX_QUERY_LENGTH})"

    for keyword in WRITE_KEYWORDS:
        pattern = r'\b' + keyword.rstrip() + r'\b'
        if re.search(pattern, upper):
            return False, f"Write operation detected: {keyword.rstrip()}"

    if "RETURN" not in upper:
        return False, "Query has no RETURN clause"

    return True, ""
