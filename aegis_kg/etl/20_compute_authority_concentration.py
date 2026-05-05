"""
Batch 18 — Authority Concentration Map
Creates RegulatoryAuthority nodes representing the regulatory authorities
(ENISA, DPAs, NCAs, EU AI Office, ESAs) and computes their influence
based on sole-authority SubDomain concentration.

Authority mapping:
  CRA       -> ENISA (European Union Agency for Cybersecurity)
  GDPR      -> DPAs (Data Protection Authorities)
  NIS2      -> NCAs/ENISA (National Competent Authorities)
  AIAct     -> EU AI Office
  DORA      -> ESAs (EBA/ESMA/EIOPA)

Creates:
  - RegulatoryAuthority nodes with influence metrics
  - UNDER_AUTHORITY relationship from SubDomain to RegulatoryAuthority

Run: python 20_compute_authority_concentration.py
"""

from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "d3fendtest")

AUTHORITY_MAP = {
    "CRA": {
        "authorityId": "ENISA",
        "authorityName": "European Union Agency for Cybersecurity",
        "authorityType": "EU_AGENCY",
    },
    "GDPR": {
        "authorityId": "DPAs",
        "authorityName": "Data Protection Authorities",
        "authorityType": "NATIONAL_DPA",
    },
    "NIS2": {
        "authorityId": "NCAs_ENISA",
        "authorityName": "National Competent Authorities / ENISA",
        "authorityType": "NATIONAL_COORDINATION",
    },
    "AI Act": {
        "authorityId": "EU_AI_OFFICE",
        "authorityName": "EU AI Office (European Commission)",
        "authorityType": "EU_OFFICE",
    },
    "DORA": {
        "authorityId": "ESAs",
        "authorityName": "European Supervisory Authorities (EBA/ESMA/EIOPA)",
        "authorityType": "ESA_BODY",
    },
}


def main():
    driver = GraphDatabase.driver(URI, auth=AUTH)

    with driver.session() as sess:
        for reg_id, auth_info in AUTHORITY_MAP.items():
            # Get sole-authority SubDomains for this regulation
            result = sess.run("""
                MATCH (sd:SubDomain)
                WHERE sd.soleAuthority = $regId
                RETURN sd.subDomainId AS sd,
                       coalesce(sd.effectiveCoverage, 0) AS ec,
                       coalesce(sd.obligationUrgencyIndex, 0) AS oui,
                       coalesce(sd.continuousObligationRatio, 0) AS contR,
                       coalesce(sd.hotspotScore, 0) AS hs,
                       coalesce(sd.gapDensityScore, 0) AS gds
            """, {"regId": reg_id})

            items = list(result)
            if not items:
                print(f"  {reg_id}: no sole-authority SubDomains")
                continue

            sole_count = len(items)
            total_ec = sum(x["ec"] for x in items)
            avg_oui = sum(x["oui"] for x in items) / sole_count
            avg_cont = sum(x["contR"] for x in items) / sole_count
            total_hs = sum(x["hs"] for x in items)
            avg_gds = sum(x["gds"] for x in items) / sole_count

            influence_score = round(
                sole_count * 5.0 +
                total_ec * 0.3 +
                avg_oui * sole_count * 2.0 +
                total_hs * 1.0,
                2
            )

            auth_id = auth_info["authorityId"]

            # Create RegulatoryAuthority node
            sess.run("""
                MERGE (auth:RegulatoryAuthority {authorityId: $authId})
                SET auth.authorityName = $authName,
                    auth.authorityType = $authType,
                    auth.soleAuthorityCount = $soleCount,
                    auth.totalEffectiveCoverage = $totalEc,
                    auth.avgObligationUrgency = $avgOui,
                    auth.avgContinuousRatio = $avgCont,
                    auth.totalHotspotScore = $totalHs,
                    auth.avgGapDensityScore = $avgGds,
                    auth.authorityInfluenceScore = $influenceScore,
                    auth.primaryRegulationId = $regId
            """, {
                "authId": auth_id,
                "authName": auth_info["authorityName"],
                "authType": auth_info["authorityType"],
                "soleCount": sole_count,
                "totalEc": round(total_ec, 2),
                "avgOui": round(avg_oui, 4),
                "avgCont": round(avg_cont, 4),
                "totalHs": total_hs,
                "avgGds": round(avg_gds, 4),
                "influenceScore": influence_score,
                "regId": reg_id,
            })

            # Link SubDomains to authority
            for item in items:
                sess.run("""
                    MATCH (sd:SubDomain {subDomainId: $sdId})
                    MERGE (auth:RegulatoryAuthority {authorityId: $authId})
                    MERGE (sd)-[:UNDER_REGULATORY_AUTHORITY]->(auth)
                    SET sd.authorityId = $authId
                """, {"sdId": item["sd"], "authId": auth_id})

            print(f"  {reg_id} -> {auth_id}: {sole_count} sole-authority SubDomains, "
                  f"influenceScore={influence_score}")

    driver.close()
    print("\n[Batch 18] Authority Concentration Map computed")


if __name__ == "__main__":
    main()