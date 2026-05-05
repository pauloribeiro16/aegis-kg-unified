#!/usr/bin/env python3
"""
NI-Weighted Coverage.

For each SubDomain:
  - effectiveCoverage: float — sum(normativeIntensity * weight) per mapped clause
    Computed as sum(c.normativeIntensity) for all clauses mapped to this SubDomain
    (weight on COVERS_SUBDOMAIN relationship is always 1.0)
  - effectiveCoverageTier: string — HIGH (>= 8.0), MEDIUM (>= 4.0), LOW (< 4.0)
    Based on effectiveCoverage score

For each Regulation:
  - effectiveCoverageScore: float — sum of all clause NI values for this regulation's clauses
  - effectiveCoverageTier: string — HIGH, MEDIUM, LOW

Requires: clauseCount and avgNormativeIntensity must already be set on SubDomain.
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


def compute_effective_coverage(driver):
    """Compute NI-weighted effective coverage for SubDomains."""
    print("[Effective Coverage] Computing NI-weighted effective coverage...")

    query = """
    MATCH (sd:SubDomain)
    OPTIONAL MATCH (c:Clause)-[:MAPPED_TO]->(sd)
    WITH sd,
         CASE WHEN count(DISTINCT c) > 0
              THEN sum(c.normativeIntensity)
              ELSE 0.0 END AS effectiveCoverage,
         CASE WHEN count(DISTINCT c) > 0
              THEN avg(c.normativeIntensity)
              ELSE 0.0 END AS avgNI
    SET sd.effectiveCoverage = effectiveCoverage,
        sd.effectiveCoverageTier = CASE
            WHEN effectiveCoverage >= 8.0 THEN 'HIGH'
            WHEN effectiveCoverage >= 4.0 THEN 'MEDIUM'
            ELSE 'LOW' END
    RETURN sd.subDomainId AS id,
           effectiveCoverage,
           CASE
               WHEN effectiveCoverage >= 8.0 THEN 'HIGH'
               WHEN effectiveCoverage >= 4.0 THEN 'MEDIUM'
               ELSE 'LOW' END AS tier,
           avgNI
    ORDER BY effectiveCoverage DESC
    """

    with driver.session() as s:
        rows = [dict(r) for r in s.run(query)]

    print(f"[Effective Coverage] Updated {len(rows)} SubDomain nodes.")
    for r in rows[:10]:
        print(f"  {r['id']}: effectiveCoverage={r['effectiveCoverage']}, tier={r['tier']}, avgNI={r['avgNI']}")

    return rows


def compute_regulation_effective_coverage(driver):
    """Compute NI-weighted effective coverage per Regulation."""
    print("\n[Effective Coverage] Computing effective coverage per regulation...")

    query = """
    MATCH (r:Regulation)-[:HAS_CLAUSE]->(c:Clause)-[:MAPPED_TO]->(sd:SubDomain)
    WITH r.regulationId AS regId, r.name AS name,
         count(DISTINCT c) AS clauseCount,
         sum(c.normativeIntensity) AS totalNI,
         avg(c.normativeIntensity) AS avgNI,
         count(DISTINCT sd) AS coveredSDs
    RETURN regId, name, clauseCount, totalNI, avgNI, coveredSDs
    ORDER BY totalNI DESC
    """

    with driver.session() as s:
        rows = [dict(r) for r in s.run(query)]

    update_query = """
    MATCH (r:Regulation {regulationId: $regId})
    SET r.effectiveCoverageScore = $totalNI,
        r.effectiveCoverageTier = $tier
    """

    tier_query = """
    MATCH (r:Regulation {regulationId: $regId})
    SET r.effectiveCoverageTier = $tier
    """

    with driver.session() as s:
        for r in rows:
            tier = 'HIGH' if r['totalNI'] >= 50.0 else 'MEDIUM' if r['totalNI'] >= 25.0 else 'LOW'
            s.run(update_query, {
                "regId": r['regId'],
                "totalNI": r['totalNI'],
                "tier": tier
            })
            print(f"  {r['regId']}: clauses={r['clauseCount']}, totalNI={r['totalNI']}, "
                  f"avgNI={round(r['avgNI'],2)}, coveredSDs={r['coveredSDs']}, tier={tier}")

    return rows


def verify(driver):
    """Verify effective coverage properties are set."""
    print("\n[Effective Coverage] Verification...")

    with driver.session() as s:
        r = s.run("""
        MATCH (sd:SubDomain)
        WHERE sd.effectiveCoverageTier IS NULL
        RETURN sd.subDomainId AS id
        """)
        null_rows = [dict(row)["id"] for row in r]

        if null_rows:
            print(f"  WARNING: {len(null_rows)} SubDomains with NULL effectiveCoverageTier")
        else:
            print(f"  All SubDomains have effectiveCoverageTier set.")

        tier_dist = s.run("""
        MATCH (sd:SubDomain)
        RETURN sd.effectiveCoverageTier AS tier, count(*) AS count ORDER BY tier
        """)
        for row in tier_dist:
            print(f"  Tier {row['tier']}: {row['count']} SubDomains")

        reg_check = s.run("""
        MATCH (r:Regulation)
        WHERE r.effectiveCoverageTier IS NOT NULL
        RETURN r.regulationId AS reg, r.effectiveCoverageScore AS score, r.effectiveCoverageTier AS tier
        ORDER BY score DESC
        """)
        print("\n  Regulation effective coverage:")
        for row in reg_check:
            print(f"    {row['reg']}: score={row['score']}, tier={row['tier']}")


def main():
    print("=" * 60)
    print("Effective Coverage: NI-Weighted Coverage")
    print("=" * 60)

    driver = get_driver()
    try:
        compute_effective_coverage(driver)
        compute_regulation_effective_coverage(driver)
        verify(driver)
        print("\n[Effective Coverage] Complete.")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
