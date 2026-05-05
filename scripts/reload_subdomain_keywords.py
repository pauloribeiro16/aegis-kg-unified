#!/usr/bin/env python3
"""Reload SubDomain keywords and examples from CSV into Neo4j.

Usage:
    python scripts/reload_subdomain_keywords.py
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
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "aegis_kg", "data", "02_subdomains.csv")


def exec_cypher(statement, params=None):
    url = f"{NEO4J_HTTP}/db/neo4j/tx/commit"
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}
    resp = requests.post(url, auth=AUTH, json=payload, timeout=30)
    if resp.status_code != 200:
        return None
    result = resp.json()
    if result.get("errors"):
        print(f"  ERROR: {result['errors'][0]['message']}")
        return None
    return result.get("results", [])


def main():
    print("Loading SubDomain keywords from CSV...")

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    updated = 0
    for row in rows:
        sd_id = row["subDomainId"]
        keywords = row.get("keywords", "")
        examples = row.get("examples", "")

        if not keywords.strip():
            continue

        cypher = """
        MATCH (sd:SubDomain {subDomainId: $sdId})
        SET sd.keywords = $keywords, sd.examples = $examples
        RETURN sd.subDomainId
        """
        result = exec_cypher(cypher, {"sdId": sd_id, "keywords": keywords, "examples": examples})
        if result:
            updated += 1
        else:
            print(f"  WARNING: Failed to update {sd_id}")

    print(f"Updated {updated}/{len(rows)} subdomains with keywords")

    verify = exec_cypher("MATCH (sd:SubDomain) WHERE sd.keywords IS NOT NULL RETURN count(sd)")
    count = verify[0]["data"][0]["row"][0] if verify else 0
    print(f"Verified: {count} subdomains with keywords in Neo4j")

    return 0 if count >= 30 else 1


if __name__ == "__main__":
    sys.exit(main())
