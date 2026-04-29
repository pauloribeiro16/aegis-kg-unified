#!/usr/bin/env python3
"""
Load Regulatory Timelines as properties on Regulation nodes.
Each Regulation gets a notificationTimelines property (list of maps).
"""
import os
import requests
import csv
import json
from pathlib import Path

IMPORT_JSON = True  # Store timelines as JSON string (Neo4j Community doesn't support nested maps)

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


def main():
    print("=" * 60)
    print("  Loading Regulatory Timelines")
    print("=" * 60)

    rows = load_csv("08_regulatory_timelines.csv")
    print(f"\n  Loaded {len(rows)} timeline entries")

    print("\n  Testing Neo4j connection...")
    success, err = exec_cypher("MATCH (n) RETURN count(n)")
    if not success:
        print(f"  ✗ Neo4j connection failed: {err}")
        return
    print("  ✓ Neo4j connection OK")

    timelines_by_reg = {}
    for row in rows:
        reg = row['regulationId'].strip()
        entry = {
            'type': row['timelineType'].strip(),
            'deadline': row['deadline'].strip() if row['deadline'].strip() else None,
            'unit': row['unit'].strip() if row['unit'].strip() else None,
            'triggerCondition': row['triggerCondition'].strip(),
            'source': row['source'].strip()
        }
        if reg not in timelines_by_reg:
            timelines_by_reg[reg] = []
        timelines_by_reg[reg].append(entry)

    for reg_id, timelines in timelines_by_reg.items():
        timelines_json = json.dumps(timelines)
        cypher = """
        MATCH (r:Regulation {regulationId: $regId})
        SET r.notificationTimelines = $timelinesJson
        RETURN r.regulationId AS id, $timelineCount AS count
        """
        params = {"regId": reg_id, "timelinesJson": timelines_json, "timelineCount": len(timelines)}
        success, err = exec_cypher(cypher, params)
        if success:
            print(f"  ✓ {reg_id}: {len(timelines)} timeline(s)")
        else:
            print(f"  ✗ {reg_id}: {err[:60]}")

    print("\n" + "=" * 60)
    print("  Verification")
    print("=" * 60)

    verify_q = """
    MATCH (r:Regulation)
    WHERE r.notificationTimelines IS NOT NULL
    RETURN r.regulationId AS id,
           r.notificationTimelines AS json
    ORDER BY id
    """
    success, _ = exec_cypher(verify_q)
    if success:
        payload = {"statements": [{"statement": verify_q}]}
        response = requests.post(f"{NEO4J_HTTP}/db/neo4j/tx/commit", auth=AUTH, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if result.get('results') and result['results'][0].get('data'):
                for row in result['results'][0]['data']:
                    r = row['row']
                    timelines = json.loads(r[1]) if r[1] else []
                    print(f"    {r[0]}: {len(timelines)} timeline(s)")
                    for t in timelines:
                        print(f"      - {t['type']} ({t['deadline']} {t['unit'] if t['unit'] else 'N/A'})")

    print("\n" + "=" * 60)
    print("  ✓ Regulatory timelines loaded")
    print("=" * 60)


if __name__ == "__main__":
    main()
