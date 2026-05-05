"""
Obligation Type Analysis
Computes per-Regulation and per-SubDomain obligation type distributions.

Regulations have obligation types: CONTINUOUS, ONE_TIME, PERIODIC, TRIGGERED

Per-Regulation properties:
  - obligationProfile: JSON string {obligationType: count, ...}
  - dominantObligationType: most frequent obligation type
  - continuousObligationRatio: CONTINUOUS / total clauses
  - periodicObligationRatio: PERIODIC / total clauses
  - triggeredObligationRatio: TRIGGERED / total clauses
  - oneTimeObligationRatio: ONE_TIME / total clauses
  - urgencyIndex: 0-1 composite urgency score
    Formula: (continuous*1.0 + triggered*0.7 + periodic*0.5 + oneTime*0.3) / totalClauses

Per-SubDomain properties:
  - dominantObligationType: most frequent obligation type of mapped clauses
  - continuousObligationRatio: CONTINUOUS / total mapped clauses
  - obligationUrgencyIndex: same formula but aggregated at SubDomain level

Run: python 19_compute_obligation_types.py
"""

import json
from collections import Counter

from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "d3fendtest")

OBLIGATION_WEIGHTS = {
    "CONTINUOUS": 1.0,
    "TRIGGERED": 0.7,
    "PERIODIC": 0.5,
    "ONE_TIME": 0.3,
}


def compute_urgency_index(counter: Counter, total: int) -> float:
    if total == 0:
        return 0.0
    weighted = sum(OBLIGATION_WEIGHTS.get(ot, 0) * ct for ot, ct in counter.items())
    return round(weighted / total, 4)


def main():
    driver = GraphDatabase.driver(URI, auth=AUTH)

    with driver.session() as sess:
        # --- Per-Regulation computation ---
        result = sess.run("""
            MATCH (c:Clause)
            RETURN c.regulationId AS reg, c.obligationType AS ot, count(c) AS ct
            ORDER BY reg, ct DESC
        """)

        reg_updates = []
        reg_data = {}
        for record in result:
            reg_id = record["reg"]
            ot = record["ot"]
            ct = record["ct"]
            if reg_id not in reg_data:
                reg_data[reg_id] = Counter()
            reg_data[reg_id][ot] = ct

        for reg_id, counter in reg_data.items():
            total = sum(counter.values())
            dist = dict(counter)

            profile = json.dumps(dist)
            dominant = counter.most_common(1)[0][0] if counter else None
            cont_ratio = round(dist.get("CONTINUOUS", 0) / total, 4) if total > 0 else 0.0
            peri_ratio = round(dist.get("PERIODIC", 0) / total, 4) if total > 0 else 0.0
            trig_ratio = round(dist.get("TRIGGERED", 0) / total, 4) if total > 0 else 0.0
            one_ratio = round(dist.get("ONE_TIME", 0) / total, 4) if total > 0 else 0.0
            urgency = compute_urgency_index(counter, total)

            sess.run("""
                MATCH (r:Regulation {regulationId: $regId})
                SET r.obligationProfile = $profile,
                    r.dominantObligationType = $dominant,
                    r.continuousObligationRatio = $contRatio,
                    r.periodicObligationRatio = $periRatio,
                    r.triggeredObligationRatio = $trigRatio,
                    r.oneTimeObligationRatio = $oneRatio,
                    r.urgencyIndex = $urgency
            """, {
                "regId": reg_id,
                "profile": profile,
                "dominant": dominant,
                "contRatio": cont_ratio,
                "periRatio": peri_ratio,
                "trigRatio": trig_ratio,
                "oneRatio": one_ratio,
                "urgency": urgency,
            })

            reg_updates.append({
                "reg": reg_id, "total": total, "dominant": dominant,
                "contRatio": cont_ratio, "urgency": urgency
            })
            print(f"  {reg_id}: total={total}, dominant={dominant}, "
                  f"continuous_ratio={cont_ratio:.2f}, urgencyIndex={urgency:.3f}")

        # --- Per-SubDomain computation ---
        result = sess.run("""
            MATCH (c:Clause)-[:MAPPED_TO]->(sd:SubDomain)
            RETURN sd.subDomainId AS sdId, c.obligationType AS ot, count(c) AS ct
            ORDER BY sdId, ct DESC
        """)

        sd_updates = 0
        sd_data = {}
        for record in result:
            sd_id = record["sdId"]
            ot = record["ot"]
            ct = record["ct"]
            if sd_id not in sd_data:
                sd_data[sd_id] = Counter()
            sd_data[sd_id][ot] = ct

        for sd_id, counter in sd_data.items():
            total = sum(counter.values())
            dist = dict(counter)

            dominant = counter.most_common(1)[0][0] if counter else None
            cont_ratio = round(dist.get("CONTINUOUS", 0) / total, 4) if total > 0 else 0.0
            urgency = compute_urgency_index(counter, total)

            sess.run("""
                MATCH (sd:SubDomain {subDomainId: $sdId})
                SET sd.dominantObligationType = $dominant,
                    sd.continuousObligationRatio = $contRatio,
                    sd.obligationUrgencyIndex = $urgency
            """, {
                "sdId": sd_id,
                "dominant": dominant,
                "contRatio": cont_ratio,
                "urgency": urgency,
            })
            sd_updates += 1

    driver.close()

    print(f"\n[Obligation Types] Obligation Type Analysis: {len(reg_updates)} regulations, {sd_updates} subdomains")


if __name__ == "__main__":
    main()