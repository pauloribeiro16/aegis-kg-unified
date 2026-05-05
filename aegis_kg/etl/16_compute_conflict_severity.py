#!/usr/bin/env python3
"""
Conflict Severity Score.

Computes conflictSeverityScore for each ComplementarityAnalysis node:
  conflictSeverityScore = dynamicJaccard * 0.4 + niDelta_normalized * 0.3 + timeline_normalized * 0.3

Where:
  - niDelta_normalized: niDelta / max_niDelta across all pairs
  - timeline_normalized: based on notification deadline differences (24h vs 72h = 0.5, etc.)

Requires: dynamicJaccard on ComplementarityAnalysis, normativeIntensityDelta on StrategicTensions.
"""

import os
import json
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


TIMELINE_MAP = {
    'GDPR': {'notification': 72, 'early_warning': None},
    'NIS2': {'notification': 24, 'early_warning': 24},
    'CRA': {'notification': 24, 'early_warning': None},
    'DORA': {'notification': 24, 'early_warning': 24},
    'AIAct': {'notification': None, 'early_warning': None},
}


def compute_severity(driver):
    """Compute conflictSeverityScore for each ComplementarityAnalysis pair."""
    print("[Conflict Severity] Computing conflict severity scores...")

    ni_query = """
    MATCH (ca:ComplementarityAnalysis)-[:OVERLAPS_WITH]->(r:Regulation)
    WITH ca, r.regulationId AS regId, r.effectiveCoverageScore AS cov
    ORDER BY ca.analysisId, regId
    WITH ca, collect({regId: regId, cov: cov}) AS regPairs
    WHERE size(regPairs) = 2
    WITH ca, regPairs[0] AS p1, regPairs[1] AS p2
    RETURN ca.analysisId AS id,
           p1.regId AS reg1, p2.regId AS reg2,
           ca.dynamicJaccard AS jaccard,
           p1.cov AS cov1, p2.cov AS cov2,
           ca.dynamicSharedSubDomainCount AS sharedCount,
           abs(p1.cov - p2.cov) AS niDelta
    ORDER BY id
    """
    with driver.session() as s:
        pairs = [dict(r) for r in s.run(ni_query)]

    max_ni_delta = max(p['niDelta'] for p in pairs) if pairs else 1.0

    update_q = """
    MATCH (ca:ComplementarityAnalysis {analysisId: $id})
    SET ca.conflictSeverityScore = $score,
        ca.severityComponents = $components
    """

    for p in pairs:
        ni_delta_norm = p['niDelta'] / max_ni_delta if max_ni_delta > 0 else 0

        r1 = p['reg1']
        r2 = p['reg2']
        t1 = TIMELINE_MAP.get(r1, {})
        t2 = TIMELINE_MAP.get(r2, {})
        n1 = t1.get('notification', 999) or 0
        n2 = t2.get('notification', 999) or 0
        if n1 == 0 or n2 == 0:
            timeline_delta_norm = 0.0
        else:
            timeline_delta = abs(n1 - n2) / 72.0
            timeline_delta_norm = min(timeline_delta, 1.0)

        jaccard_weight = p['jaccard'] if p['jaccard'] is not None else 0.0
        severity_score = (jaccard_weight * 0.4) + (ni_delta_norm * 0.3) + (timeline_delta_norm * 0.3)

        components = {
            'jaccardComponent': round(jaccard_weight * 0.4, 3),
            'niDeltaComponent': round(ni_delta_norm * 0.3, 3),
            'timelineComponent': round(timeline_delta_norm * 0.3, 3),
            'rawNiDelta': p['niDelta'],
            'timelineDeltaHours': abs(n1 - n2) if n1 > 0 and n2 > 0 else 0
        }

        with driver.session() as s:
            s.run(update_q, {
                "id": p['id'],
                "score": round(severity_score, 3),
                "components": json.dumps(components)
            })
        print(f"  {p['id']} ({p['reg1']}-{p['reg2']}): score={round(severity_score,3)} "
              f"(j={round(jaccard_weight,2)}*{0.4}={round(jaccard_weight*0.4,3)}, "
              f"ni={round(ni_delta_norm,2)}*{0.3}={round(ni_delta_norm*0.3,3)}, "
              f"tl={round(timeline_delta_norm,2)}*{0.3}={round(timeline_delta_norm*0.3,3)})")

    return pairs


def verify(driver):
    """Verify severity scores are set."""
    print("\n[Conflict Severity] Verification...")
    with driver.session() as s:
        r = s.run("""
        MATCH (ca:ComplementarityAnalysis)
        RETURN ca.analysisId AS id, ca.regulation1Id AS r1, ca.regulation2Id AS r2,
               ca.conflictSeverityScore AS score, ca.severityComponents AS components
        ORDER BY score DESC
        """)
        for row in r:
            print(f"  {row['id']} ({row['r1']}-{row['r2']}): score={row['score']}")


def main():
    print("=" * 60)
    print("Conflict Severity: Conflict Severity Score")
    print("=" * 60)
    driver = get_driver()
    try:
        compute_severity(driver)
        verify(driver)
        print("\n[Conflict Severity] Complete.")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
