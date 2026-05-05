"""
Batch 15 — Gap Density ETL
Computes per-SubDomain gap density metrics based on clause distribution
across the 5 regulations (GDPR, CRA, NIS2, DORA, AI Act).

gapDensityScore = 1 - min(cv, 1.0)
  where cv = stddev(clause_counts) / mean(clause_counts)
  across the 5 regulations.

gapDensityTier: DENSE >= 0.5, MODERATE >= 0.2, SPARSE < 0.2

Properties written to SubDomain:
  - gapDensityScore: float [0..1], balance of clause distribution
  - gapDensityTier: SPARSE|MODERATE|DENSE
  - clauseDistribution: JSON string {regId: count, ...}
  - missingRegulations: list of regulation IDs not covering this SubDomain

Run: python 17_compute_gap_density.py
"""

import json
import statistics
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "d3fendtest")
ALL_REGS = ["GDPR", "CRA", "NIS2", "DORA", "AIAct"]


def compute_gap_density(clause_counts: list[float]) -> float:
    """Return 1 - min(cv, 1.0) where cv is coefficient of variation."""
    mean_val = statistics.mean(clause_counts)
    if mean_val == 0:
        return 0.0
    cv = statistics.stdev(clause_counts) / mean_val
    return 1.0 - min(cv, 1.0)


def get_tier(score: float) -> str:
    if score >= 0.5:
        return "DENSE"
    if score >= 0.2:
        return "MODERATE"
    return "SPARSE"


def main():
    driver = GraphDatabase.driver(URI, auth=AUTH)

    with driver.session() as sess:
        # Collect clause counts per regulation per SubDomain
        result = sess.run("""
            MATCH (c:Clause)-[:MAPPED_TO]->(sd:SubDomain)
            WITH sd.subDomainId AS sdId,
                 c.regulationId AS reg,
                 count(c) AS cc
            ORDER BY sdId, cc DESC
            WITH sdId, collect({reg: reg, cc: cc}) AS dist
            RETURN sdId, dist
            ORDER BY sdId
        """)

        updates = []
        for record in result:
            sd_id = record["sdId"]
            dist = {item["reg"]: item["cc"] for item in record["dist"]}

            clause_counts = [float(dist.get(reg, 0)) for reg in ALL_REGS]
            gap_score = compute_gap_density(clause_counts)
            tier = get_tier(gap_score)
            missing = [reg for reg in ALL_REGS if reg not in dist]
            distribution_str = json.dumps(dist)

            updates.append({
                "sdId": sd_id,
                "gapDensityScore": round(gap_score, 4),
                "gapDensityTier": tier,
                "clauseDistribution": distribution_str,
                "missingRegulations": missing
            })

        # Write all properties back to Neo4j
        for u in updates:
            sess.run("""
                MATCH (sd:SubDomain {subDomainId: $sdId})
                SET sd.gapDensityScore = $gapDensityScore,
                    sd.gapDensityTier = $gapDensityTier,
                    sd.clauseDistribution = $clauseDistribution,
                    sd.missingRegulations = $missingRegulations
            """, u)

    driver.close()

    # Summary
    tier_dist = {"DENSE": 0, "MODERATE": 0, "SPARSE": 0}
    for u in updates:
        tier_dist[u["gapDensityTier"]] += 1

    print(f"[Batch 15] Gap Density computed for {len(updates)} SubDomains")
    print(f"  DENSE: {tier_dist['DENSE']}, MODERATE: {tier_dist['MODERATE']}, SPARSE: {tier_dist['SPARSE']}")
    print(f"  Top DENSE: ", end="")
    dense = [u for u in updates if u["gapDensityTier"] == "DENSE"]
    for d in sorted(dense, key=lambda x: -x["gapDensityScore"])[:3]:
        print(f"{d['sdId']}={d['gapDensityScore']}", end=" ")
    print()
    print(f"  Top SPARSE: ", end="")
    sparse = [u for u in updates if u["gapDensityTier"] == "SPARSE"]
    for s in sorted(sparse, key=lambda x: x["gapDensityScore"])[:3]:
        print(f"{s['sdId']}={s['gapDensityScore']}", end=" ")
    print()


if __name__ == "__main__":
    main()