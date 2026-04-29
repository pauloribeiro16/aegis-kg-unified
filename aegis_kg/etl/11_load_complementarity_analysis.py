#!/usr/bin/env python3
"""
Load full Complementarity Analysis for all 10 regulation pairs.
Computes Jaccard from KG data + qualitative classifications from case documents.
Creates ComplementarityAnalysis nodes with OVERLAPS_WITH relationships.
"""
import os
import requests
import json
from pathlib import Path

NEO4J_HTTP = "http://localhost:7474"
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", ""))


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


COMPLEMENTARITY_DATA = [
    {
        'analysisId': 'GDPR-CRA-001',
        'reg1': 'GDPR', 'reg2': 'CRA',
        'sharedCount': 12, 'total1': 19, 'total2': 22,
        'conflictClassification': 'STRUCTURAL_TENSION',
        'overlapDescription': 'Both mandate encryption, access control, and incident notification but with different scopes: GDPR focuses on personal data rights while CRA focuses on product security properties',
        'conflictDescription': 'GDPR 72h vs CRA 24h breach notification (EVT-001); GDPR appropriate measures (NI=2) vs CRA secure by default (NI=3)',
        'recommendedApproach': 'Implement CRA higher bar for overlapping requirements; use CRA 24h timeline as worst-case for incident reporting'
    },
    {
        'analysisId': 'GDPR-NIS2-001',
        'reg1': 'GDPR', 'reg2': 'NIS2',
        'sharedCount': 14, 'total1': 19, 'total2': 24,
        'conflictClassification': 'CONTEXTUAL_TENSION',
        'overlapDescription': 'NIS2 extends GDPR security requirements to essential/important entities with mandatory incident reporting and management accountability',
        'conflictDescription': 'NIS2 24h early warning vs GDPR 72h notification for same incident involving personal data breach (TC-001, TC-002)',
        'recommendedApproach': 'NIS2 24h satisfies GDPR 72h requirement; implement unified incident response with NIS2 timeline as primary driver'
    },
    {
        'analysisId': 'GDPR-DORA-001',
        'reg1': 'GDPR', 'reg2': 'DORA',
        'sharedCount': 15, 'total1': 19, 'total2': 28,
        'conflictClassification': 'STRUCTURAL_TENSION',
        'overlapDescription': 'DORA extends GDPR requirements for financial entities with specific ICT risk management, incident reporting tiers, and TLPT mandates',
        'conflictDescription': 'DORA RTS 4h initial vs GDPR 72h; DORA mandates specific ICT security controls that complement GDPR technical measures',
        'recommendedApproach': 'DORA compliance satisfies GDPR ICT security requirements; use DORA 4h as worst-case for personal data breaches'
    },
    {
        'analysisId': 'GDPR-AIA-001',
        'reg1': 'GDPR', 'reg2': 'AI_ACT',
        'sharedCount': 9, 'total1': 19, 'total2': 13,
        'conflictClassification': 'CONTEXTUAL_TENSION',
        'overlapDescription': 'AI Act high-risk requirements complement GDPR data protection obligations for AI systems processing personal data',
        'conflictDescription': 'AI Act logging (6-month min) vs GDPR storage limitation; DPIA trigger vs FRIA trigger timing mismatch (TM-001)',
        'recommendedApproach': 'Implement AI Act logging as maximum retention; align DPIA and FRIA assessments to satisfy both triggers simultaneously'
    },
    {
        'analysisId': 'CRA-NIS2-001',
        'reg1': 'CRA', 'reg2': 'NIS2',
        'sharedCount': 16, 'total1': 22, 'total2': 24,
        'conflictClassification': 'SYNERGISTIC',
        'overlapDescription': 'CRA product security requirements complement NIS2 organisational security measures; CRA applies to products, NIS2 to entity operations',
        'conflictDescription': 'No direct conflicts; CRA vulnerability disclosure (Art. 14) aligns with NIS2 coordinated disclosure practices',
        'recommendedApproach': 'Single vulnerability disclosure process satisfies both CRA Art. 14 and NIS2 Art. 21 vulnerability handling'
    },
    {
        'analysisId': 'CRA-DORA-001',
        'reg1': 'CRA', 'reg2': 'DORA',
        'sharedCount': 18, 'total1': 22, 'total2': 28,
        'conflictClassification': 'SYNERGISTIC',
        'overlapDescription': 'DORA ICT third-party risk management extends CRA supply chain requirements to financial sector; CRA applies to digital products, DORA to financial entity operations',
        'conflictDescription': 'DORA TLPT (36-month cycle) complements CRA conformity assessment; DORA supply chain controls extend CRA SBOM requirements',
        'recommendedApproach': 'DORA TLPT programme satisfies CRA testing requirements for financial sector digital products'
    },
    {
        'analysisId': 'CRA-AIA-001',
        'reg1': 'CRA', 'reg2': 'AI_ACT',
        'sharedCount': 9, 'total1': 22, 'total2': 13,
        'conflictClassification': 'STRUCTURAL_TENSION',
        'overlapDescription': 'AI Act high-risk AI system requirements complement CRA security objectives for AI-enabled products',
        'conflictDescription': 'AI Act accuracy/robustness requirements add to CRA security objectives; CRA conformity assessment may partially satisfy AI Act conformity',
        'recommendedApproach': 'AI Act conformity assessment should include CRA conformity evaluation to avoid duplicate assessments'
    },
    {
        'analysisId': 'NIS2-DORA-001',
        'reg1': 'NIS2', 'reg2': 'DORA',
        'sharedCount': 24, 'total1': 24, 'total2': 28,
        'conflictClassification': 'STRUCTURAL_TENSION',
        'overlapDescription': 'DORA lex specialis overrides NIS2 for financial sector ICT risk; DORA provides more specific requirements that NIS2 IRQ for financial entities',
        'conflictDescription': 'DORA specific ICT risk framework (Art. 5) and 4h/72h/30d reporting tiers vs NIS2 24h/72h/1mo; NIS2 IR 2024/2690 does not apply to financial entities (D-012)',
        'recommendedApproach': 'DORA compliance framework satisfies NIS2 ICT risk requirements for financial entities; NIS2 IR 2024/2690 excluded per DORA lex specialis'
    },
    {
        'analysisId': 'NIS2-AIA-001',
        'reg1': 'NIS2', 'reg2': 'AI_ACT',
        'sharedCount': 9, 'total1': 24, 'total2': 13,
        'conflictClassification': 'CONTEXTUAL_TENSION',
        'overlapDescription': 'NIS2 entity security obligations complement AI Act high-risk AI system security requirements for AI systems used in essential/important entities',
        'conflictDescription': 'NIS2 24h incident notification may overlap with AI Act 15d/2d AI incident reporting; NIS2 security training complements AI Act human oversight',
        'recommendedApproach': 'Implement unified incident classification covering both NIS2 significant incidents and AI Act serious incidents; NIS2 training satisfies AI Act human oversight competence'
    },
    {
        'analysisId': 'DORA-AIA-001',
        'reg1': 'DORA', 'reg2': 'AI_ACT',
        'sharedCount': 10, 'total1': 28, 'total2': 13,
        'conflictClassification': 'STRUCTURAL_TENSION',
        'overlapDescription': 'DORA ICT risk management complements AI Act high-risk AI system requirements for financial sector AI; both require testing, monitoring, and incident reporting',
        'conflictDescription': 'DORA TLPT and AI Act adversarial testing both require penetration testing; DORA 4h/72h/30d vs AI Act 15d/2d/10d incident reporting (AI Act TC-003)',
        'recommendedApproach': 'DORA incident reporting (4h initial) satisfies AI Act 15d requirement as worst-case; integrate AI incident into DORA ICT incident framework'
    },
]


def main():
    print("=" * 60)
    print("  Loading Complementarity Analysis (All 10 Pairs)")
    print("=" * 60)

    print("\n  Testing Neo4j connection...")
    success, err = exec_cypher("MATCH (n) RETURN count(n)")
    if not success:
        print(f"  ✗ Neo4j connection failed: {err}")
        return
    print("  ✓ Neo4j connection OK")

    print(f"\n  Clearing existing ComplementarityAnalysis nodes...")
    exec_cypher("MATCH (ca:ComplementarityAnalysis) DETACH DELETE ca")
    print("  ✓ Cleared old nodes")

    for data in COMPLEMENTARITY_DATA:
        analysis_id = data['analysisId']
        reg1, reg2 = data['reg1'], data['reg2']
        shared = data['sharedCount']
        total1, total2 = data['total1'], data['total2']
        union = total1 + total2 - shared
        jaccard = round(shared / union, 3) if union > 0 else 0
        complementarity = round(1 - jaccard, 3)

        cypher = """
        MATCH (r1:Regulation {regulationId: $reg1})
        MATCH (r2:Regulation {regulationId: $reg2})
        CREATE (ca:ComplementarityAnalysis {
            analysisId: $analysisId,
            regulation1Id: $reg1,
            regulation2Id: $reg2,
            sharedSubDomainCount: $shared,
            totalUniqueSubDomains: $union,
            jaccardIndex: $jaccard,
            complementarityIndex: $complementarity,
            conflictClassification: $conflictClass,
            overlapDescription: $overlapDesc,
            conflictDescription: $conflictDesc,
            recommendedApproach: $approach
        })
        MERGE (ca)-[:OVERLAPS_WITH]->(r1)
        MERGE (ca)-[:OVERLAPS_WITH]->(r2)
        RETURN ca.analysisId AS id, ca.jaccardIndex AS j, ca.conflictClassification AS cc
        """
        params = {
            'analysisId': analysis_id,
            'reg1': reg1,
            'reg2': reg2,
            'shared': shared,
            'union': union,
            'jaccard': jaccard,
            'complementarity': complementarity,
            'conflictClass': data['conflictClassification'],
            'overlapDesc': data['overlapDescription'],
            'conflictDesc': data['conflictDescription'],
            'approach': data['recommendedApproach']
        }
        success, err = exec_cypher(cypher, params)
        if success:
            print(f"  ✓ {analysis_id}: Jaccard={jaccard}, {data['conflictClassification']}")
        else:
            print(f"  ✗ {analysis_id}: {err[:60]}")

    print("\n" + "=" * 60)
    print("  Verification")
    print("=" * 60)

    verify_q = """
    MATCH (ca:ComplementarityAnalysis)-[:OVERLAPS_WITH]->(r:Regulation)
    WITH ca, collect(r.regulationId) AS regs, ca.conflictClassification AS cc
    RETURN ca.analysisId AS id,
           regs[0] AS reg1,
           regs[1] AS reg2,
           ca.sharedSubDomainCount AS shared,
           ca.jaccardIndex AS jaccard,
           cc AS conflictType
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
                    print(f"    {r[0]}: {r[1]} x {r[2]} | shared={r[3]}, Jaccard={r[4]}, {r[5]}")

    print("\n" + "=" * 60)
    print("  ✓ Complementarity analysis loaded (10 pairs)")
    print("=" * 60)


if __name__ == "__main__":
    main()
