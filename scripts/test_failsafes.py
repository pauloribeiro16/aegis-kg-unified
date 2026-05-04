#!/usr/bin/env python3
"""Failsafe component tests — verifies circuit breaker, linter, fallbacks, etc.

Usage:
    python scripts/test_failsafes.py

Exit code 0 = all tests pass.
"""

import sys


def test_circuit_breaker():
    """Test circuit breaker state transitions."""
    from aegis_agents.circuit_breaker import CircuitBreaker, CircuitOpenError

    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=2, success_threshold=2)
    assert cb.state == "CLOSED", f"Initial: expected CLOSED, got {cb.state}"

    for _ in range(3):
        try:
            cb.call(lambda: (_ for _ in ()).throw(ConnectionError("test")))
        except ConnectionError:
            pass

    assert cb.state == "OPEN", f"After 3 failures: expected OPEN, got {cb.state}"
    assert cb.is_open, "is_open should be True"

    try:
        cb.call(lambda: "should fail")
        assert False, "Should have raised CircuitOpenError"
    except CircuitOpenError:
        pass

    print("  [PASS] Circuit breaker state transitions")


def test_query_linter():
    """Test query validation."""
    from aegis_agents.query_linter import validate_cypher

    valid_queries = [
        "MATCH (r:Regulation) RETURN r.regulationId",
        "MATCH (c:Clause) WHERE c.regulationId = 'GDPR' RETURN count(c) AS total",
        "MATCH (sd:SubDomain) WHERE NOT EXISTS((:Clause)-[:MAPPED_TO]->(sd)) RETURN sd.name",
    ]
    for q in valid_queries:
        ok, reason = validate_cypher(q)
        assert ok, f"Should be valid: {q} — {reason}"

    invalid_queries = [
        ("CREATE (n:Test) RETURN n", "write"),
        ("MERGE (n:Test) RETURN n", "write"),
        ("MATCH (n) DELETE n", "write"),
        ("MATCH (n) REMOVE n.prop", "write"),
        ("MATCH (n) SET n.x = 1 RETURN n", "write"),
        ("MATCH (r:Regulation)", "RETURN"),
        ("", "Empty"),
    ]
    for q, kw in invalid_queries:
        ok, reason = validate_cypher(q)
        assert not ok, f"Should be invalid: {q}"
        assert kw.lower() in reason.lower() or "return" in reason.lower(), f"Expected '{kw}' in: {reason}"

    print("  [PASS] Query linter")


def test_fallback_queries():
    """Test fallback template matching."""
    from aegis_agents.fallback_queries import find_fallback

    should_match = [
        ("How many clauses does GDPR have?", "MATCH"),
        ("List all regulations", "MATCH"),
        ("Which subdomains have no coverage?", "MATCH"),
        ("Show NIST controls for the PR function", "MATCH"),
        ("What are the strategic tensions?", "MATCH"),
        ("Tell me about gap analysis", "MATCH"),
        ("How many NIST controls are there?", "MATCH"),
    ]
    for question, kw in should_match:
        result = find_fallback(question)
        assert result is not None, f"Should match: {question}"
        assert kw in result, f"Should contain {kw}: {result}"

    should_not_match = [
        "What is the meaning of life?",
        "Tell me a joke",
    ]
    for question in should_not_match:
        result = find_fallback(question)
        assert result is None, f"Should not match: {question} — got: {result}"

    print("  [PASS] Fallback queries")


def test_result_validator():
    """Test result validation."""
    from aegis_agents.result_validator import validate_result

    _, warnings = validate_result({"error": None, "data": [{"x": 1}], "row_count": 1}, "test")
    assert len(warnings) == 0, f"Expected no warnings: {warnings}"

    _, warnings = validate_result({"error": None, "data": [{"x": i} for i in range(501)], "row_count": 501}, "test")
    assert len(warnings) > 0, "Expected warning for 501 rows"

    _, warnings = validate_result({"error": "some error", "data": [], "row_count": 0}, "test")
    assert len(warnings) == 0, "Errors should not generate warnings"

    print("  [PASS] Result validator")


def test_extended_state():
    """Test extended agent state has new fields."""
    from aegis_agents.graph.state import AgentState
    ann = AgentState.__annotations__
    required = ["circuit_breaker_state", "last_error_type", "fallback_used", "total_latency_ms", "degraded_mode"]
    for field in required:
        assert field in ann, f"Missing field: {field}"

    print("  [PASS] Extended agent state")


def main():
    print("=" * 60)
    print("  Failsafe Component Tests")
    print("=" * 60)

    tests = [
        ("Circuit Breaker", test_circuit_breaker),
        ("Query Linter", test_query_linter),
        ("Fallback Queries", test_fallback_queries),
        ("Result Validator", test_result_validator),
        ("Extended State", test_extended_state),
    ]

    failed = []
    for name, test_func in tests:
        print(f"\n[{name}]")
        try:
            test_func()
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed.append((name, str(e)))

    print("\n" + "=" * 60)
    if failed:
        print(f"  FAILED: {len(failed)}/{len(tests)} tests")
        for name, error in failed:
            print(f"    {name}: {error}")
        return 1
    else:
        print(f"  ALL {len(tests)} TESTS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
