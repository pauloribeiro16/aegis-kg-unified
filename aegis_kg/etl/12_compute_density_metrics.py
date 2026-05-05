#!/usr/bin/env python3
"""
Compute SubDomain density metrics and dynamic Jaccard.

Computes for each SubDomain:
  - clauseCount: count of clauses mapped to this SubDomain
  - regulationCount: count of distinct regulations covering this SubDomain
  - coveringRegulations: list of distinct regulationIds covering this SubDomain
  - densityScore: clauseCount / 5.0 (normalized by max 5 regulations)
  - avgNormativeIntensity: average NI of covering clauses
  - weightedDensity: sum(NI) / 15.0 (NI-weighted, max theoretical 1.0)

Recomputes Jaccard for all ComplementarityAnalysis pairs from actual graph data:
  - dynamicJaccard: shared_subdomains / union
  - dynamicSharedSubDomainCount: actual shared SubDomain count
  - jaccardSource: 'DYNAMIC'
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_URI = "bolt://localhost:7687"  # Always use Bolt protocol on 7687
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "d3fendtest")


def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def compute_subdomain_metrics(driver):
    """Compute and set density metrics on all SubDomain nodes."""
    print("[Density Metrics] Computing SubDomain density metrics...")

    query = """
    MATCH (sd:SubDomain)
    OPTIONAL MATCH (c:Clause)-[:MAPPED_TO]->(sd)
    WITH sd,
         count(DISTINCT c) AS clauseCount,
         count(DISTINCT c.regulationId) AS regulationCount,
         collect(DISTINCT c.regulationId) AS coveringRegulations,
         CASE WHEN count(DISTINCT c) > 0
              THEN round(avg(c.normativeIntensity) * 100) / 100
              ELSE 0.0 END AS avgNI,
         CASE WHEN count(DISTINCT c) > 0
              THEN round(toFloat(sum(c.normativeIntensity)) / 15.0 * 100) / 100
              ELSE 0.0 END AS weightedDensity
    SET sd.clauseCount = clauseCount,
        sd.regulationCount = regulationCount,
        sd.coveringRegulations = coveringRegulations,
        sd.densityScore = round(toFloat(clauseCount) / 5.0 * 100) / 100,
        sd.avgNormativeIntensity = avgNI,
        sd.weightedDensity = weightedDensity
    RETURN sd.subDomainId AS id,
           clauseCount,
           regulationCount,
           coveringRegulations,
           round(toFloat(clauseCount) / 5.0 * 100) / 100 AS densityScore,
           avgNI,
           weightedDensity
    ORDER BY clauseCount DESC
    """

    with driver.session() as s:
        result = s.run(query)
        rows = [dict(r) for r in result]

    print(f"[Density Metrics] Updated {len(rows)} SubDomain nodes.")
    for r in rows:
        print(f"  {r['id']}: clauses={r['clauseCount']}, regs={r['regulationCount']}, "
              f"density={r['densityScore']}, avgNI={r['avgNI']}, "
              f"covering={r['coveringRegulations']}")

    return rows


def compute_dynamic_jaccard(driver):
    """Recompute Jaccard from actual graph data for all regulation pairs."""
    print("\n[Density Metrics] Computing dynamic Jaccard indices...")

    regs_query = "MATCH (r:Regulation) RETURN r.regulationId AS id ORDER BY id"
    with driver.session() as s:
        regs = [dict(r)["id"] for r in s.run(regs_query)]

    pairs = []
    for i, r1 in enumerate(regs):
        for r2 in regs[i + 1:]:
            with driver.session() as s:
                row = s.run(
                    f"""
                    MATCH (:Regulation {{regulationId: '{r1}'}})-[:HAS_CLAUSE]->(:Clause)-[:MAPPED_TO]->(sd:SubDomain)
                    WITH collect(DISTINCT sd.subDomainId) AS set1
                    MATCH (:Regulation {{regulationId: '{r2}'}})-[:HAS_CLAUSE]->(:Clause)-[:MAPPED_TO]->(sd2:SubDomain)
                    WITH set1, collect(DISTINCT sd2.subDomainId) AS set2
                    RETURN size(set1) AS total1,
                           size(set2) AS total2,
                           size([x IN set1 WHERE x IN set2]) AS sharedCount
                    """
                ).single()
            if row:
                t1, t2, shared = row["total1"], row["total2"], row["sharedCount"]
                union = t1 + t2 - shared
                jaccard = round(shared / union, 3) if union > 0 else 0.0
                pairs.append((r1, r2, t1, t2, shared, union, jaccard))
                print(f"  {r1}-{r2}: shared={shared}, union={union}, jaccard={jaccard}")

    update_query = """
    MATCH (ca:ComplementarityAnalysis)
    WHERE (ca.regulation1Id = $r1 AND ca.regulation2Id = $r2)
       OR (ca.regulation1Id = $r2 AND ca.regulation2Id = $r1)
    SET ca.dynamicJaccard = $jaccard,
        ca.dynamicSharedSubDomainCount = $shared,
        ca.jaccardSource = 'DYNAMIC'
    RETURN ca.analysisId AS id, ca.dynamicJaccard AS dj, ca.dynamicSharedSubDomainCount AS dsh
    """

    with driver.session() as s:
        for r1, r2, t1, t2, shared, union, jaccard in pairs:
            res = s.run(
                update_query,
                {"r1": r1, "r2": r2, "jaccard": jaccard, "shared": shared},
            )
            updated = [dict(r) for r in res]
            if updated:
                print(
                    f"  Updated {updated[0]['id']}: dynamicJaccard={updated[0]['dj']}, "
                    f"dynamicShared={updated[0]['dsh']}"
                )

    return pairs


def create_indexes(driver):
    """Create indexes for new SubDomain density properties."""
    print("\n[Density Metrics] Creating indexes for density properties...")

    indexes = [
        "CREATE INDEX subdomain_density_score IF NOT EXISTS FOR (sd:SubDomain) ON (sd.densityScore)",
        "CREATE INDEX subdomain_clause_count IF NOT EXISTS FOR (sd:SubDomain) ON (sd.clauseCount)",
        "CREATE INDEX subdomain_regulation_count IF NOT EXISTS FOR (sd:SubDomain) ON (sd.regulationCount)",
        "CREATE INDEX subdomain_avg_ni IF NOT EXISTS FOR (sd:SubDomain) ON (sd.avgNormativeIntensity)",
    ]

    with driver.session() as s:
        for idx in indexes:
            try:
                s.run(idx)
                print(f"  {idx.split('IF NOT EXISTS')[0].strip()}: OK")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"  {idx}: already exists (skipped)")
                else:
                    print(f"  {idx}: {e}")


def verify(driver):
    """Verify all SubDomain properties are set."""
    print("\n[Density Metrics] Verification query...")

    with driver.session() as s:
        query = """
        MATCH (sd:SubDomain)
        RETURN sd.subDomainId AS id,
               sd.clauseCount AS cc,
               sd.regulationCount AS rc,
               sd.densityScore AS ds,
               sd.avgNormativeIntensity AS avgNI,
               sd.weightedDensity AS wd,
               size(sd.coveringRegulations) AS crs
        ORDER BY sd.clauseCount DESC
        LIMIT 10
        """
        rows = [dict(r) for r in s.run(query)]

    print("  Top 10 SubDomains by clauseCount:")
    for r in rows:
        print(
            f"    {r['id']}: clauses={r['cc']}, regs={r['rc']}, "
            f"density={r['ds']}, avgNI={r['avgNI']}, weightedDensity={r['wd']}"
        )

    with driver.session() as s:
        null_check = s.run(
            "MATCH (sd:SubDomain) WHERE sd.clauseCount IS NULL RETURN sd.subDomainId AS id"
        )
        null_rows = [dict(r)["id"] for r in null_check]
        if null_rows:
            print(f"  WARNING: {len(null_rows)} SubDomains still have NULL clauseCount")
        else:
            print(f"  All SubDomains have clauseCount set.")

        jaccard_check = s.run(
            "MATCH (ca:ComplementarityAnalysis) WHERE ca.jaccardSource = 'DYNAMIC' "
            "RETURN ca.analysisId AS id, ca.dynamicJaccard AS dj"
        )
        jaccard_rows = [dict(r) for r in jaccard_check]
        print(f"  ComplementarityAnalysis updated: {len(jaccard_rows)} pairs with dynamic Jaccard")


def main():
    print("=" * 60)
    print("Density Metrics: Dynamic Jaccard + SubDomain density")
    print("=" * 60)

    driver = get_driver()
    try:
        create_indexes(driver)
        compute_subdomain_metrics(driver)
        compute_dynamic_jaccard(driver)
        verify(driver)
        print("\n[Density Metrics] Complete.")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
