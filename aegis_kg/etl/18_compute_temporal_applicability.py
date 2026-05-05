"""
Batch 16 — Temporal Applicability Map
Populates missing regulatory milestone dates on Regulation nodes:
  - complianceDeadline: date by which regulated entities must comply
  - enforcementDate: date when penalties/sanctions begin
  - applicationDate: date the regulation started applying to organizations

Known dates (verified from EU directives/regulations):
  GDPR:     effective=2018-05-25, application=2018-05-25, complianceDeadline=2018-05-25, enforcement=2018-05-25
  NIS2:     effective=2023-01-16, application=2024-10-17, complianceDeadline=2024-10-17, enforcement=2024-10-17
  CRA:      effective=2024-12-12, application=2027-09-11, complianceDeadline=2027-09-11, enforcement=2027-09-11
  DORA:     effective=2025-01-17, application=2025-01-17, complianceDeadline=2025-01-17, enforcement=2025-01-17
  AIAct:    effective=2024-07-12, application=2026-08-02, complianceDeadline=2026-08-02, enforcement=2027-08-02

Also creates RegulatoryTimeline nodes for key milestone events per regulation.

Run: python 18_compute_temporal_applicability.py
"""

from datetime import date, datetime
from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "d3fendtest")

REGULATORY_DATES = {
    "GDPR": {
        "effectiveDate": date(2018, 5, 25),
        "applicationDate": date(2018, 5, 25),
        "complianceDeadline": date(2018, 5, 25),
        "enforcementDate": date(2018, 5, 25),
        "milestones": [
            ("ENTRY_INTO_FORCE", date(2016, 5, 4), "Regulation published in Official Journal"),
            ("APPLICATION", date(2018, 5, 25), "Regulation starts applying to organizations"),
            ("ENFORCEMENT", date(2018, 5, 25), "Data protection authorities begin enforcement"),
        ],
    },
    "NIS2": {
        "effectiveDate": date(2023, 1, 16),
        "applicationDate": date(2024, 10, 17),
        "complianceDeadline": date(2024, 10, 17),
        "enforcementDate": date(2024, 10, 17),
        "milestones": [
            ("ENTRY_INTO_FORCE", date(2022, 12, 14), "NIS2 Directive published in Official Journal"),
            ("TRANSPOSITION_DEADLINE", date(2024, 10, 17), "Member states must transpose into national law"),
            ("APPLICATION", date(2024, 10, 17), "Entities must comply with NIS2 requirements"),
            ("ENFORCEMENT", date(2024, 10, 17), "National authorities begin supervisory actions"),
        ],
    },
    "CRA": {
        "effectiveDate": date(2024, 12, 12),
        "applicationDate": date(2027, 9, 11),
        "complianceDeadline": date(2027, 9, 11),
        "enforcementDate": date(2027, 9, 11),
        "milestones": [
            ("ENTRY_INTO_FORCE", date(2024, 11, 20), "CRA published in Official Journal"),
            ("APPLICATION", date(2027, 9, 11), "Main obligations start applying"),
            ("ESSENTIAL_REQUIREMENTS", date(2026, 9, 11), "Essential cybersecurity requirements apply"),
            ("ENFORCEMENT", date(2027, 9, 11), "Market surveillance authorities begin enforcement"),
        ],
    },
    "DORA": {
        "effectiveDate": date(2025, 1, 17),
        "applicationDate": date(2025, 1, 17),
        "complianceDeadline": date(2025, 1, 17),
        "enforcementDate": date(2025, 1, 17),
        "milestones": [
            ("ENTRY_INTO_FORCE", date(2022, 12, 14), "DORA published in Official Journal"),
            ("APPLICATION", date(2025, 1, 17), "Regulation starts applying to financial entities"),
            ("TLPT_DEADLINE", date(2024, 7, 17), "Threat-led penetration testing requirements apply"),
            ("ENFORCEMENT", date(2025, 1, 17), "Competent authorities begin oversight"),
        ],
    },
    "AIAct": {
        "effectiveDate": date(2024, 7, 12),
        "applicationDate": date(2026, 8, 2),
        "complianceDeadline": date(2026, 8, 2),
        "enforcementDate": date(2027, 8, 2),
        "milestones": [
            ("ENTRY_INTO_FORCE", date(2024, 7, 12), "AI Act published in Official Journal"),
            ("PROHIBITED_AI", date(2024, 8, 2), "Prohibited AI practices provisions apply (6 months)"),
            ("APPLICATION", date(2026, 8, 2), "Main AI Act provisions start applying"),
            ("HIGH_RISK_DEADLINE", date(2026, 8, 2), "High-risk AI system requirements apply"),
            ("ENFORCEMENT", date(2027, 8, 2), "Penalties for non-compliance begin (12 months after application)"),
        ],
    },
}


def parse_iso(val):
    """Parse a date string or return None."""
    if val is None:
        return None
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except Exception:
        return None


def days_until(d: date) -> int:
    """Days from today until date d (negative if in the past)."""
    today = date.today()
    return (d - today).days


def urgency_tier(reg_id: str, comp_deadline: date) -> str:
    """Compute urgency tier based on compliance deadline."""
    days = days_until(comp_deadline)
    if days < 0:
        return "PAST_DUE"
    if days <= 90:
        return "CRITICAL"
    if days <= 365:
        return "URGENT"
    return "ON_TRACK"


def main():
    driver = GraphDatabase.driver(URI, auth=AUTH)

    with driver.session() as sess:
        today = date.today()

        for reg_id, data in REGULATORY_DATES.items():
            comp_deadline = data["complianceDeadline"]
            enforcement = data["enforcementDate"]
            application = data["applicationDate"]

            tier = urgency_tier(reg_id, comp_deadline)
            days_to_comply = days_until(comp_deadline)
            days_to_enforce = days_until(enforcement)

            sess.run("""
                MATCH (r:Regulation {regulationId: $regId})
                SET r.complianceDeadline = date($compDeadline),
                    r.enforcementDate = date($enforcementDate),
                    r.applicationDate = date($applicationDate),
                    r.urgencyTier = $urgencyTier,
                    r.daysToCompliance = $daysToCompliance,
                    r.daysToEnforcement = $daysToEnforcement
            """, {
                "regId": reg_id,
                "compDeadline": comp_deadline.isoformat(),
                "enforcementDate": enforcement.isoformat(),
                "applicationDate": application.isoformat(),
                "urgencyTier": tier,
                "daysToCompliance": days_to_comply,
                "daysToEnforcement": days_to_enforce,
            })

            # Create RegulatoryTimeline nodes
            for event_type, evt_date, description in data["milestones"]:
                timeline_id = f"TL-{reg_id}-{event_type}"
                sess.run("""
                    MATCH (r:Regulation {regulationId: $regId})
                    CREATE (t:RegulatoryTimeline {
                        timelineId: $timelineId,
                        eventType: $eventType,
                        eventDate: date($eventDate),
                        description: $description,
                        regulationId: $regId
                    })
                    CREATE (r)-[:HAS_TIMELINE_EVENT]->(t)
                """, {
                    "timelineId": timeline_id,
                    "regId": reg_id,
                    "eventType": event_type,
                    "eventDate": evt_date.isoformat(),
                    "description": description,
                })

            print(f"  {reg_id}: compliance={comp_deadline}, enforcement={enforcement}, "
                  f"tier={tier}, days_to_comply={days_to_comply}, days_to_enforce={days_to_enforce}")

    driver.close()
    print(f"\n[Batch 16] Temporal Applicability Map computed for 5 regulations")


if __name__ == "__main__":
    main()