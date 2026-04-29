#!/usr/bin/env python3
"""
Load Sole Authority relationships: SubDomain → Regulation.
Source: ground_truth/regulatory_rules.yaml sole_authority section.
Also update SubDomain.isSoleAuthority property.
"""
import os
import requests
from pathlib import Path

NEO4J_HTTP = "http://localhost:7474"
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", ""))

SOLE_AUTHORITY_MAP = {
    'D-02.3': 'CRA',
    'D-03.4': 'CRA',
    'D-05.4': 'GDPR',
    'D-06.2': 'CRA',
    'D-07.2': 'DORA',
    'D-07.3': 'NIS2',
    'D-07.4': 'DORA',
    'D-08.3': 'NIS2',
}


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


def main():
    print("=" * 60)
    print("  Loading Sole Authority Relationships")
    print("=" * 60)

    print("\n  Testing Neo4j connection...")
    success, err = exec_cypher("MATCH (n) RETURN count(n)")
    if not success:
        print(f"  ✗ Neo4j connection failed: {err}")
        return
    print("  ✓ Neo4j connection OK")

    print(f"\n  Mapping {len(SOLE_AUTHORITY_MAP)} sole authority relationships:")
    for sd_id, reg_id in SOLE_AUTHORITY_MAP.items():
        cypher = """
        MATCH (sd:SubDomain {subDomainId: $sdId})
        MATCH (r:Regulation {regulationId: $regId})
        MERGE (sd)-[rel:SOLE_AUTHORITY]->(r)
        SET rel.source = 'GROUND_TRUTH',
            rel.loadedAt = date()
        RETURN sd.subDomainId AS sd, r.regulationId AS reg
        """
        params = {"sdId": sd_id, "regId": reg_id}
        success, err = exec_cypher(cypher, params)
        if success:
            print(f"  ✓ {sd_id} → {reg_id}")
        else:
            print(f"  ✗ {sd_id} → {reg_id}: {err[:60]}")

    print("\n  Setting SubDomain.isSoleAuthority property...")
    for sd_id in SOLE_AUTHORITY_MAP.keys():
        cypher = """
        MATCH (sd:SubDomain {subDomainId: $sdId})
        SET sd.isSoleAuthority = true
        """
        params = {"sdId": sd_id}
        success, err = exec_cypher(cypher, params)
        if success:
            print(f"  ✓ {sd_id}.isSoleAuthority = true")

    print("\n" + "=" * 60)
    print("  Verification")
    print("=" * 60)

    verify_q = """
    MATCH (sd:SubDomain)-[rel:SOLE_AUTHORITY]->(r:Regulation)
    RETURN sd.subDomainId AS subdomain, r.regulationId AS regulator,
           rel.source AS source
    ORDER BY sd.subDomainId
    """
    success, _ = exec_cypher(verify_q)
    if success:
        payload = {"statements": [{"statement": verify_q}]}
        response = requests.post(f"{NEO4J_HTTP}/db/neo4j/tx/commit", auth=AUTH, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result.get('results') and result['results'][0].get('data'):
                count = len(result['results'][0]['data'])
                print(f"\n    Total SOLE_AUTHORITY relationships: {count}")
                for row in result['results'][0]['data']:
                    r = row['row']
                    print(f"    {r[0]} → {r[1]} ({r[2]})")

    uncovered_q = """
    MATCH (sd:SubDomain)
    WHERE sd.isSoleAuthority = true
      AND NOT EXISTS((sd)-[:SOLE_AUTHORITY]->())
    RETURN sd.subDomainId AS orphanSoleAuthority
    """
    success, _ = exec_cypher(uncovered_q)
    if success:
        payload = {"statements": [{"statement": uncovered_q}]}
        response = requests.post(f"{NEO4J_HTTP}/db/neo4j/tx/commit", auth=AUTH, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result.get('results') and result['results'][0]['data']:
                orphans = [r['row'][0] for r in result['results'][0]['data']]
                if orphans:
                    print(f"\n    ⚠ Orphan sole authority subdomains (no target): {orphans}")

    print("\n" + "=" * 60)
    print("  ✓ Sole authority loaded")
    print("=" * 60)


if __name__ == "__main__":
    main()
