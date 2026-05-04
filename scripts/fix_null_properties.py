#!/usr/bin/env python3
"""Fix NULL properties in the AEGIS Knowledge Graph.

Populates missing Regulation, Article, Clause properties.
Deletes phantom SubDomainMetrics nodes.

Usage:
    python scripts/fix_null_properties.py
"""

import csv
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

NEO4J_HTTP = os.getenv("NEO4J_URI", "http://localhost:7474")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
AUTH = (NEO4J_USER, NEO4J_PASSWORD)
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "aegis_kg", "data")


def exec_cypher(statement, params=None):
    url = f"{NEO4J_HTTP}/db/neo4j/tx/commit"
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}
    resp = requests.post(url, auth=AUTH, json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"  ERROR: HTTP {resp.status_code}: {resp.text[:200]}")
        return None
    result = resp.json()
    if result.get("errors"):
        print(f"  ERROR: {result['errors'][0]['message']}")
        return None
    return result.get("results", [])


def query_one(statement):
    r = exec_cypher(statement)
    if r and r[0].get("data"):
        return r[0]["data"][0]["row"]
    return None


def main():
    print("=" * 60)
    print("  AEGIS KG — Fix NULL Properties")
    print("=" * 60)

    try:
        r = requests.get(NEO4J_HTTP, auth=AUTH, timeout=5)
        assert r.status_code == 200, f"Neo4j returned {r.status_code}"
        print("  OK: Neo4j connected")
    except Exception as e:
        print(f"  FATAL: Cannot connect to Neo4j: {e}")
        sys.exit(1)

    print("\n--- STEP 1: Populate Regulation properties ---")
    csv_path = os.path.join(DATA_DIR, "00_regulations.csv")
    if not os.path.exists(csv_path):
        print(f"  FATAL: CSV not found: {csv_path}")
        sys.exit(1)

    with open(csv_path, newline="", encoding="utf-8") as f:
        regulations = list(csv.DictReader(f))

    print(f"  Loaded {len(regulations)} regulations from CSV")

    for reg in regulations:
        reg_id = reg["regulationId"]
        cypher = """
        MATCH (r:Regulation {regulationId: $regId})
        SET r.name = $name,
            r.fullName = $fullName,
            r.effectiveDate = $effectiveDate,
            r.lastAmended = $lastAmended
        RETURN r.regulationId
        """
        result = exec_cypher(cypher, {
            "regId": reg_id,
            "name": reg.get("name", ""),
            "fullName": reg.get("fullName", ""),
            "effectiveDate": reg.get("effectiveDate", ""),
            "lastAmended": reg.get("lastAmended", ""),
        })
        if result:
            print(f"  Updated {reg_id}: name='{reg.get('name', '')}'")
        else:
            print(f"  WARNING: Failed to update {reg_id}")

    null_names = query_one("MATCH (r:Regulation) WHERE r.name IS NULL RETURN count(r)")
    print(f"  Regulations with NULL name: {null_names[0] if null_names else 'QUERY FAILED'}")

    print("\n--- STEP 2: Populate Article.regulationId ---")
    cypher = """
    MATCH (a:Article)
    WHERE a.regulationId IS NULL AND a.articleId IS NOT NULL
    WITH a, split(a.articleId, '-') AS parts
    SET a.regulationId = parts[0]
    RETURN count(a) AS updated
    """
    result = query_one(cypher)
    print(f"  Updated {result[0] if result else '?'} articles with regulationId")

    null_reg = query_one("MATCH (a:Article) WHERE a.regulationId IS NULL RETURN count(a)")
    print(f"  Articles still with NULL regulationId: {null_reg[0] if null_reg else '?'}")

    print("\n--- STEP 3: Set Clause.applicable = true ---")
    cypher = """
    MATCH (c:Clause)
    WHERE c.applicable IS NULL
    SET c.applicable = true
    RETURN count(c) AS updated
    """
    result = query_one(cypher)
    print(f"  Updated {result[0] if result else '?'} clauses with applicable=true")

    null_app = query_one("MATCH (c:Clause) WHERE c.applicable IS NULL RETURN count(c)")
    print(f"  Clauses still with NULL applicable: {null_app[0] if null_app else '?'}")

    print("\n--- STEP 4: Delete phantom SubDomainMetrics ---")
    count_before = query_one("MATCH (m:SubDomainMetrics) RETURN count(m)")
    print(f"  SubDomainMetrics before: {count_before[0] if count_before else '?'}")

    cypher = """
    MATCH (m:SubDomainMetrics)
    DETACH DELETE m
    RETURN count(*) AS deleted
    """
    result = query_one(cypher)
    print(f"  Deleted {result[0] if result else '?'} SubDomainMetrics nodes")

    count_after = query_one("MATCH (m:SubDomainMetrics) RETURN count(m)")
    print(f"  SubDomainMetrics after: {count_after[0] if count_after else '?'}")

    print("\n" + "=" * 60)
    print("  VERIFICATION")
    print("=" * 60)

    checks = [
        ("Regulation.name NULL", "MATCH (r:Regulation) WHERE r.name IS NULL RETURN count(r)", 0),
        ("Regulation count", "MATCH (r:Regulation) RETURN count(r)", 5),
        ("Article.regulationId NULL", "MATCH (a:Article) WHERE a.regulationId IS NULL RETURN count(a)", 0),
        ("Article count", "MATCH (a:Article) RETURN count(a)", 47),
        ("Clause.applicable NULL", "MATCH (c:Clause) WHERE c.applicable IS NULL RETURN count(c)", 0),
        ("Clause count", "MATCH (c:Clause) RETURN count(c)", 150),
        ("SubDomainMetrics count", "MATCH (m:SubDomainMetrics) RETURN count(m)", 0),
        ("SubDomain count", "MATCH (sd:SubDomain) RETURN count(sd)", 38),
        ("Domain count", "MATCH (d:Domain) RETURN count(d)", 10),
    ]

    all_pass = True
    for name, query, expected in checks:
        result = query_one(query)
        actual = result[0] if result else "QUERY FAILED"
        status = "PASS" if actual == expected else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  [{status}] {name}: {actual} (expected {expected})")

    print()
    if all_pass:
        print("  ALL CHECKS PASSED")
    else:
        print("  SOME CHECKS FAILED — verify manually")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())