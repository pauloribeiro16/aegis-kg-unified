"""Post-execution validation for Cypher query results.

Detects suspicious results: excessive rows, NULL-heavy columns, etc.
"""

MAX_ROWS = 500
WARN_ROWS = 200
MAX_NULL_RATIO = 0.8


def validate_result(result: dict, question: str) -> tuple[dict, list[str]]:
    """Validate query results and return warnings.

    Args:
        result: Dict with 'data', 'row_count', 'error' keys.
        question: Original question for context.

    Returns:
        (result, warnings) — result is unchanged, warnings is a list of strings.
    """
    warnings = []

    if result.get("error") is not None:
        return result, warnings

    data = result.get("data", [])
    row_count = result.get("row_count", 0)

    if row_count > MAX_ROWS:
        warnings.append(f"Excessive rows: {row_count} (max {MAX_ROWS}). Query may be too broad.")

    elif row_count > WARN_ROWS:
        warnings.append(f"High row count: {row_count}. Consider narrowing the query.")

    if data:
        keys = list(data[0].keys())
        for key in keys:
            null_count = sum(1 for row in data if row.get(key) is None)
            if null_count > 0 and len(data) > 0:
                ratio = null_count / len(data)
                if ratio >= MAX_NULL_RATIO:
                    warnings.append(f"Column '{key}' is {ratio:.0%} NULL ({null_count}/{len(data)} rows)")

    return result, warnings
