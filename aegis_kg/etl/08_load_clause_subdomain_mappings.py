#!/usr/bin/env python3
"""
Load Clause → SubDomain mappings from CSV.
Maps all 150 clauses to their respective SubDomains using MERGE.
"""
import os
import requests
import csv
from pathlib import Path

NEO4J_HTTP = "http://localhost:7474"
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", ""))
DATA_DIR = Path(__file__).parent.parent / "data"


def load_csv(file_name):
    file_path = DATA_DIR / file_name
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def exec_cypher(statement, params=None):
    payload = {"statements": [{"statement": statement, "parameters": params or {}}]}
    try:
        response = requests.post(
            f"{NEO4J_HTTP}/db/neo4j/tx/commit",
            auth=AUTH,
            json=payload,
            timeout=30
        )
        if response.status_code != 200:
            return False, f"HTTP {response.status_code}: {response.text[:200]}"
        result = response.json()
        if result.get('errors'):
            return False, result['errors'][0].get('message', 'Unknown error')
        return True, None
    except Exception as e:
        return False, str(e)


def verify_relationship(clause_id, subdomain_id):
    cypher = """
    MATCH (c:Clause {clauseId: $cid})
    MATCH (sd:SubDomain {subDomainId: $sid})
    MATCH (c)-[r:COVERS_SUBDOMAIN]->(sd)
    RETURN r.weight AS weight, r.source AS source
    """
    payload = {"statements": [{"statement": cypher, "parameters": {"cid": clause_id, "sid": subdomain_id}}]}
    try:
        response = requests.post(f"{NEO4J_HTTP}/db/neo4j/tx/commit", auth=AUTH, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result.get('results') and result['results'][0].get('data'):
                return True
    except:
        pass
    return False


def main():
    print("=" * 60)
    print("  Loading Clause → SubDomain Mappings")
    print("=" * 60)

    mappings = load_csv("07_clause_subdomain_mapping.csv")
    print(f"\n  Loaded {len(mappings)} mappings from CSV")

    print("\n  Testing Neo4j connection...")
    success, err = exec_cypher("MATCH (n) RETURN count(n)")
    if not success:
        print(f"  ✗ Neo4j connection failed: {err}")
        return
    print("  ✓ Neo4j connection OK")

    created = 0
    errors = 0
    skipped = 0

    for row in mappings:
        clause_id = row['clauseId']
        subdomain_id = row['subDomainId']
        weight = float(row['weight'])
        source = row['source']

        cypher = """
        MATCH (c:Clause {clauseId: $cid})
        MATCH (sd:SubDomain {subDomainId: $sid})
        MERGE (c)-[r:COVERS_SUBDOMAIN]->(sd)
        SET r.weight = $weight,
            r.source = $source
        RETURN c.clauseId AS cid, sd.subDomainId AS sid
        """
        params = {"cid": clause_id, "sid": subdomain_id, "weight": weight, "source": source}
        success, err = exec_cypher(cypher, params)

        if success:
            created += 1
            print(f"  ✓ {clause_id} → {subdomain_id}")
        else:
            errors += 1
            print(f"  ✗ {clause_id} → {subdomain_id} ({err[:60] if err else 'unknown'})")

    print(f"\n  Results:")
    print(f"    Created: {created}/{len(mappings)}")
    print(f"    Errors:  {errors}")

    print("\n" + "=" * 60)
    print("  Verification")
    print("=" * 60)

    verify_cypher = """
    MATCH (c:Clause)-[r:COVERS_SUBDOMAIN]->(sd:SubDomain)
    WITH c.regulationId AS reg,
         count(DISTINCT c) AS clauses,
         count(DISTINCT sd) AS subdomains,
         count(r) AS rels
    RETURN reg, clauses, subdomains, rels
    ORDER BY reg
    """
    success, err = exec_cypher(verify_cypher)
    if success:
        payload = {"statements": [{"statement": verify_cypher}]}
        response = requests.post(f"{NEO4J_HTTP}/db/neo4j/tx/commit", auth=AUTH, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result.get('results') and result['results'][0].get('data'):
                total_rels = 0
                for row in result['results'][0]['data']:
                    r = row['row']
                    print(f"    {r[0]}: {r[1]} clauses → {r[2]} sub-domains ({r[3]} rels)")
                    total_rels += r[3]
                print(f"\n    TOTAL: {total_rels} COVERS_SUBDOMAIN relationships")

    total_cypher = """
    MATCH (c:Clause)-[r:COVERS_SUBDOMAIN]->(sd:SubDomain)
    RETURN count(r) AS total_rels,
           count(DISTINCT c) AS clauses_with_map,
           count(DISTINCT sd) AS subdomains_covered
    """
    payload = {"statements": [{"statement": total_cypher}]}
    response = requests.post(f"{NEO4J_HTTP}/db/neo4j/tx/commit", auth=AUTH, json=payload, timeout=30)
    if response.status_code == 200:
        result = response.json()
        if result.get('results') and result['results'][0].get('data'):
            row = result['results'][0]['data'][0]['row']
            print(f"\n    Total COVERS_SUBDOMAIN: {row[0]}")
            print(f"    Clauses with mapping:   {row[1]}/150")
            print(f"    SubDomains covered:      {row[2]}/38")

    print("\n" + "=" * 60)
    if errors == 0:
        print("  ✓ All Clause → SubDomain mappings created successfully")
    else:
        print(f"  ⚠ {errors} mapping(s) failed - check clause IDs in Neo4j")
    print("=" * 60)


if __name__ == "__main__":
    main()
