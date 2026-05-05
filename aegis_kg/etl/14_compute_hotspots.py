#!/usr/bin/env python3
"""
Multi-Regulation Hotspots.

For each SubDomain:
  - hotspotScore: Integer — number of regulations covering this SubDomain (= regulationCount)
  - hotspotTier: String — CRITICAL (5 regs), HIGH (4 regs), MODERATE (3 regs), LOW (1-2 regs)

Requires: regulationCount must already be set on SubDomain.
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


def compute_hotspots(driver):
    """Compute hotspot score and tier for SubDomains."""
    print("[Hotspots] Computing hotspot metrics...")

    query = """
    MATCH (sd:SubDomain)
    OPTIONAL MATCH (sd)<-[:MAPPED_TO]-(:Clause)
    WITH sd,
         CASE WHEN sd.regulationCount IS NOT NULL THEN sd.regulationCount
              ELSE 0 END AS hotspotScore,
         CASE
             WHEN sd.regulationCount >= 5 THEN 'CRITICAL'
             WHEN sd.regulationCount >= 4 THEN 'HIGH'
             WHEN sd.regulationCount >= 3 THEN 'MODERATE'
             ELSE 'LOW' END AS hotspotTier
    WITH DISTINCT sd, hotspotScore, hotspotTier
    SET sd.hotspotScore = hotspotScore,
        sd.hotspotTier = hotspotTier
    RETURN sd.subDomainId AS id, hotspotScore, hotspotTier
    ORDER BY hotspotScore DESC
    """

    with driver.session() as s:
        rows = [dict(r) for r in s.run(query)]

    print(f"[Hotspots] Updated {len(rows)} SubDomain nodes.")
    print("  Tier distribution:")
    from collections import Counter
    tiers = Counter(r['hotspotTier'] for r in rows)
    for tier in ['CRITICAL', 'HIGH', 'MODERATE', 'LOW']:
        if tier in tiers:
            print(f"    {tier}: {tiers[tier]} SubDomains")

    return rows


def verify(driver):
    """Verify hotspot properties are set."""
    print("\n[Hotspots] Verification...")

    with driver.session() as s:
        nulls = [dict(r) for r in s.run(
            "MATCH (sd:SubDomain) WHERE sd.hotspotTier IS NULL RETURN sd.subDomainId AS id"
        )]
        if nulls:
            print(f"  WARNING: {len(nulls)} SubDomains with NULL hotspotTier")
            for n in nulls[:5]:
                print(f"    {n['id']}")
        else:
            print("  All SubDomains have hotspotTier set.")

        dist = s.run(
            "MATCH (sd:SubDomain) RETURN sd.hotspotTier AS tier, count(*) AS count ORDER BY tier"
        )
        print("  Distribution:")
        for row in dist:
            print(f"    {row['tier']}: {row['count']}")


def main():
    print("=" * 60)
    print("Hotspots: Multi-Regulation Hotspots")
    print("=" * 60)

    driver = get_driver()
    try:
        compute_hotspots(driver)
        verify(driver)
        print("\n[Hotspots] Complete.")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
