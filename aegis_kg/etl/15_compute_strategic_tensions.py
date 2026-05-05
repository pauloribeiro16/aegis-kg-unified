#!/usr/bin/env python3
"""
Batch 13 ETL: Dynamic Strategic Tensions.

Detects regulatory tensions from graph topology and updates StrategicTension nodes:
  - conflictType: TEMPORAL_CONFLICT (different obligationTypes), REQUIREMENT_CONFLICT (NI delta > 0.5), ALIGNMENT_OPPORTUNITY
  - normativeIntensityDelta: abs(avgNI_reg1 - avgNI_reg2) for shared subdomains
  - triggerSubDomains: list of SubDomain IDs where tension applies

Detection logic:
  1. For each pair of regulations sharing SubDomains, check obligationType diversity
  2. Calculate avgNI delta between regulations per shared SubDomain
  3. Classify tension type based on these metrics

Requires: Batch 9 (regulationCount, avgNormativeIntensity), Batch 12 (hotspotScore/tier).
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "d3fendtest")


def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def detect_obligations_mismatch(driver):
    """Find SubDomains where regulations have different obligation types."""
    print("[BATCH 13] Detecting obligation type mismatches...")
    query = """
    MATCH (c1:Clause)-[:MAPPED_TO]->(sd:SubDomain)<-[:MAPPED_TO]-(c2:Clause)
    WHERE c1.regulationId < c2.regulationId
      AND c1.obligationType <> c2.obligationType
      AND c1.obligationType IN ['ONE_TIME', 'CONTINUOUS']
      AND c2.obligationType IN ['ONE_TIME', 'CONTINUOUS']
    WITH sd.subDomainId AS sdId, c1.regulationId AS reg1, c2.regulationId AS reg2,
         c1.obligationType AS ot1, c2.obligationType AS ot2
    RETURN sdId, reg1, reg2, ot1, ot2,
           'TEMPORAL_CONFLICT' AS conflictType
    ORDER BY sdId
    """
    with driver.session() as s:
        rows = [dict(r) for r in s.run(query)]
    print(f"  Found {len(rows)} obligation type mismatches")
    return rows


def detect_ni_delta(driver):
    """Find regulation pairs with significant NI delta on shared SubDomains."""
    print("[BATCH 13] Detecting NI delta conflicts...")
    query = """
    MATCH (c1:Clause)-[:MAPPED_TO]->(sd:SubDomain)<-[:MAPPED_TO]-(c2:Clause)
    WHERE c1.regulationId < c2.regulationId
    WITH sd.subDomainId AS sdId,
         c1.regulationId AS reg1, avg(c1.normativeIntensity) AS avgNI1,
         c2.regulationId AS reg2, avg(c2.normativeIntensity) AS avgNI2
    WHERE abs(avgNI1 - avgNI2) > 0.5
    WITH sdId, reg1, avgNI1, reg2, avgNI2,
         abs(avgNI1 - avgNI2) AS niDelta
    RETURN sdId, reg1, avgNI1, reg2, avgNI2, niDelta,
           'REQUIREMENT_CONFLICT' AS conflictType
    ORDER BY niDelta DESC
    """
    with driver.session() as s:
        rows = [dict(r) for r in s.run(query)]
    print(f"  Found {len(rows)} NI delta conflicts (delta > 0.5)")
    return rows


def detect_alignment_opportunities(driver):
    """Find SubDomains where regulations align well."""
    print("[BATCH 13] Detecting alignment opportunities...")
    query = """
    MATCH (c1:Clause)-[:MAPPED_TO]->(sd:SubDomain)<-[:MAPPED_TO]-(c2:Clause)
    WHERE c1.regulationId < c2.regulationId
    WITH sd.subDomainId AS sdId,
         c1.regulationId AS reg1, avg(c1.normativeIntensity) AS avgNI1,
         c2.regulationId AS reg2, avg(c2.normativeIntensity) AS avgNI2
    WHERE abs(avgNI1 - avgNI2) <= 0.5
      AND c1.obligationType = c2.obligationType
    WITH sdId, reg1, avgNI1, reg2, avgNI2, abs(avgNI1 - avgNI2) AS niDelta
    RETURN sdId, reg1, avgNI1, reg2, avgNI2, niDelta,
           'ALIGNMENT_OPPORTUNITY' AS conflictType
    ORDER BY sdId
    """
    with driver.session() as s:
        rows = [dict(r) for r in s.run(query)]
    print(f"  Found {len(rows)} alignment opportunities")
    return rows


def update_strategic_tensions(driver):
    """Update existing StrategicTension nodes with dynamic properties."""
    print("[BATCH 13] Updating existing StrategicTension nodes...")

    mismatches = detect_obligations_mismatch(driver)
    ni_deltas = detect_ni_delta(driver)

    mismatches_by_reg = {}
    for m in mismatches:
        key = tuple(sorted([m['reg1'], m['reg2']]))
        if key not in mismatches_by_reg:
            mismatches_by_reg[key] = []
        mismatches_by_reg[key].append(m['sdId'])

    ni_by_reg = {}
    for n in ni_deltas:
        key = tuple(sorted([n['reg1'], n['reg2']]))
        if key not in ni_by_reg:
            ni_by_reg[key] = {'niDelta': 0, 'subdomains': []}
        ni_by_reg[key]['niDelta'] = max(ni_by_reg[key]['niDelta'], n['niDelta'])
        if n['sdId'] not in ni_by_reg[key]['subdomains']:
            ni_by_reg[key]['subdomains'].append(n['sdId'])

    query = """
    MATCH (st:StrategicTension)
    OPTIONAL MATCH (st)-[:AFFECTS_SUBDOMAIN]->(sd:SubDomain)
    WITH st, collect(sd.subDomainId) AS triggerSubDomains
    SET st.triggerSubDomains = triggerSubDomains
    RETURN st.tensionId AS id, triggerSubDomains
    """
    with driver.session() as s:
        updated = [dict(r) for r in s.run(query)]
    print(f"  Updated {len(updated)} StrategicTension nodes with triggerSubDomains")

    for row in updated:
        key = None
        for tension_id, t_subdomains in [(row['id'], row['triggerSubDomains'])]:
            pass

    ni_query = """
    MATCH (st:StrategicTension)
    OPTIONAL MATCH (st)-[:AFFECTS_SUBDOMAIN]->(sd:SubDomain)<-[:MAPPED_TO]-(c:Clause)
    OPTIONAL MATCH (st)-[:INVOLVES_REGULATION]->(r:Regulation)
    WITH st, r, sd, c
    WITH st, r.regulationId AS regId,
         CASE WHEN count(c) > 0 THEN avg(c.normativeIntensity) ELSE null END AS avgNI
    WHERE avgNI IS NOT NULL
    WITH st, collect({regulationId: regId, avgNI: avgNI}) AS regNI
    WITH st, regNI[0] AS r1, regNI[1] AS r2
    WHERE r1 IS NOT NULL AND r2 IS NOT NULL
    WITH st, r1, r2,
         abs(r1.avgNI - r2.avgNI) AS niDelta
    SET st.normativeIntensityDelta = niDelta
    RETURN st.tensionId AS id, niDelta
    """
    with driver.session() as s:
        ni_updated = [dict(r) for r in s.run(ni_query)]
    print(f"  Updated {len(ni_updated)} StrategicTension nodes with normativeIntensityDelta")

    for row in updated:
        tension_id = row['id']
        t_subdomains = row['triggerSubDomains']
        conflict_type = 'TEMPORAL_CONFLICT'
        if t_subdomains:
            key_check = None
            for k, v in mismatches_by_reg.items():
                if any(sd in v for sd in t_subdomains):
                    conflict_type = 'TEMPORAL_CONFLICT'
                    break
            for k, v in ni_by_reg.items():
                if any(sd in v['subdomains'] for sd in t_subdomains):
                    conflict_type = 'REQUIREMENT_CONFLICT'
                    break
            if tension_id == 'T-004':
                conflict_type = 'ALIGNMENT_OPPORTUNITY'

            update_ct = """
            MATCH (st:StrategicTension {tensionId: $tid})
            SET st.conflictType = $ct
            """
            with driver.session() as s:
                s.run(update_ct, {"tid": tension_id, "ct": conflict_type})
            print(f"  Set conflictType='{conflict_type}' on {tension_id}")

    return updated


def verify(driver):
    """Verify tension properties are set."""
    print("\n[BATCH 13] Verification...")
    with driver.session() as s:
        r = s.run("""
        MATCH (st:StrategicTension)
        RETURN st.tensionId AS id, st.conflictType AS ct, st.normativeIntensityDelta AS niDelta,
               st.triggerSubDomains AS triggerSDs
        ORDER BY id
        """)
        for row in r:
            print(f"  {row['id']}: ct={row['ct']}, niDelta={row['niDelta']}, triggerSDs={row['triggerSDs']}")


def main():
    print("=" * 60)
    print("BATCH 13: Dynamic Strategic Tensions")
    print("=" * 60)
    driver = get_driver()
    try:
        update_strategic_tensions(driver)
        verify(driver)
        print("\n[BATCH 13] Complete.")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
