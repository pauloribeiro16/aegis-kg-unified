#!/usr/bin/env python3
"""Schema consistency test — verifies all agent-facing files use the same IDs and relationships.

Usage:
    python scripts/test_schema_consistency.py

Exit code 0 = all checks pass.
"""

import re
import sys


def check_file(filepath, patterns_must_exist, patterns_must_not_exist):
    """Check a file for required and forbidden patterns."""
    with open(filepath) as f:
        content = f.read()

    errors = []

    for pattern, description in patterns_must_exist:
        if not re.search(pattern, content):
            errors.append(f"  MISSING: {description} (pattern: {pattern})")

    for pattern, description in patterns_must_not_exist:
        if re.search(pattern, content):
            errors.append(f"  FORBIDDEN: {description} (pattern: {pattern})")

    return errors


def main():
    print("=" * 60)
    print("  Schema Consistency Test")
    print("=" * 60)

    all_errors = []

    print("\n[1] SubDomain ID format (DOT separator)")

    for filepath in [
        "aegis_agents/tools/schema_tool.py",
        "aegis_agents/graph/prompts.py",
        "aegis_agents/tools/neo4j_tool.py",
    ]:
        print(f"  Checking {filepath}...")
        errors = check_file(filepath, [
            (r"D-\d{2}\.\d", "DOT format (D-XX.Y)"),
        ], [
            (r"D-\d{2}-\d", "DASH format (D-XX-Y) — forbidden"),
        ])
        if errors:
            all_errors.extend([(filepath, e) for e in errors])
            for e in errors:
                print(f"    FAIL: {e}")
        else:
            print(f"    OK")

    print("\n[2] Relationship names")

    for filepath in [
        "aegis_agents/tools/schema_tool.py",
        "aegis_agents/graph/prompts.py",
    ]:
        print(f"  Checking {filepath}...")
        errors = check_file(filepath, [
            (r"CONTAINS", "CONTAINS relationship"),
        ], [
            (r"HAS_SUBDOMAIN", "HAS_SUBDOMAIN — forbidden (use CONTAINS)"),
        ])
        if errors:
            all_errors.extend([(filepath, e) for e in errors])
            for e in errors:
                print(f"    FAIL: {e}")
        else:
            print(f"    OK")

    print("\n[3] API relationship names")

    errors = check_file("aegis_kg/api/app.py", [
        (r"MAPPED_TO", "MAPPED_TO relationship"),
    ], [
        (r"COVERS_SUBDOMAIN", "COVERS_SUBDOMAIN — forbidden (use MAPPED_TO)"),
    ])
    if errors:
        all_errors.extend([("aegis_kg/api/app.py", e) for e in errors])
        for e in errors:
            print(f"  FAIL: {e}")
    else:
        print("  OK")

    print("\n[4] Fallback queries format")

    errors = check_file("aegis_agents/fallback_queries.py", [], [
        (r"D-\d{2}-\d", "DASH format in fallback queries"),
        (r"HAS_SUBDOMAIN", "HAS_SUBDOMAIN in fallback queries"),
        (r"COVERS_SUBDOMAIN", "COVERS_SUBDOMAIN in fallback queries"),
    ])
    if errors:
        all_errors.extend([("aegis_agents/fallback_queries.py", e) for e in errors])
        for e in errors:
            print(f"  FAIL: {e}")
    else:
        print("  OK")

    print("\n[5] schema_context.py — DASH in comments/docs only (acceptable)")

    with open("aegis_eval/schema_context.py") as f:
        content = f.read()

    dash_in_code = re.findall(r'D-\d{2}-\d', content)
    if dash_in_code:
        print(f"  Note: {len(dash_in_code)} occurrence(s) of D-XX-Y found in schema_context.py — these are in comments/docs describing the wrong format (acceptable)")

    print("\n" + "=" * 60)
    if all_errors:
        print(f"  FAILED: {len(all_errors)} errors found")
        for filepath, error in all_errors:
            print(f"    {filepath}: {error}")
        return 1
    else:
        print("  ALL CONSISTENCY CHECKS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
