#!/usr/bin/env python3
"""
Simple Phase 1 KG Setup - Python version
Creates Neo4j schema directly using Python instead of Docker setup
"""
import time
from neo4j import GraphDatabase

def main():
    # Configuration
    URI = "bolt://localhost:7687"
    USER = "neo4j"
    PASSWORD = ""  # No password for local development

    print("=" * 50)
    print("AEGIS Phase 1 KG - Neo4j Setup (Python)")
    print("=" * 50)
    print()

    try:
        print("Connecting to Neo4j...")
        driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

        # Create constraints
        with driver.session() as session:
            print("Creating constraints...")
            session.run("""
                CREATE CONSTRAINT regulation_id_unique IF NOT EXISTS FOR (r:Regulation) REQUIRE r.regulationId IS UNIQUE;
                CREATE CONSTRAINT article_id_unique IF NOT EXISTS FOR (a:Article) REQUIRE a.articleId IS UNIQUE;
                CREATE CONSTRAINT clause_id_unique IF NOT EXISTS FOR (c:Clause) REQUIRE c.clauseId IS UNIQUE;
                CREATE CONSTRAINT domain_id_unique IF NOT EXISTS FOR (d:Domain) REQUIRE d.domainId IS UNIQUE;
                CREATE CONSTRAINT subdomain_id_unique IF NOT EXISTS FOR (sd:SubDomain) REQUIRE sd.subDomainId IS UNIQUE;
            """)
            print("✓ Constraints created")

        with driver.session() as session:
            print("Creating indexes...")
            session.run("""
                CREATE INDEX regulation_name IF NOT EXISTS FOR (r:Regulation) ON (r.name);
                CREATE INDEX article_number IF NOT EXISTS FOR (a:Article) ON (a.number);
                CREATE INDEX clause_applicable IF NOT EXISTS FOR (c:Clause) ON (c.applicable);
                CREATE INDEX clause_normative_intensity IF NOT EXISTS FOR (c:Clause) ON (c.normativeIntensity);
                CREATE INDEX subdomain_name IF NOT EXISTS FOR (sd:SubDomain) ON (sd.name);
            """)
            print("✓ Indexes created")

        # Create sample data
        with driver.session() as session:
            print("Creating sample regulations...")
            session.run("""
                CREATE (r1:Regulation {
                    regulationId: 'GDPR',
                    name: 'GDPR',
                    fullName: 'General Data Protection Regulation 2016/679',
                    type: 'DATA_PROTECTION',
                    effectiveDate: date('2018-05-25'),
                    lastAmended: date('2023-12-07'),
                    officialLink: 'https://eur-lex.europa.eu/eli/reg/2016/679',
                    primaryFocus: 'Data protection and privacy'
                })

                CREATE (r2:Regulation {
                    regulationId: 'CRA',
                    name: 'CRA',
                    fullName: 'Cyber Resilience Act (EU) 2022/2554',
                    type: 'CYBER_SECURITY',
                    effectiveDate: date('2024-12-12'),
                    lastAmended: null,
                    officialLink: 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52022PC2554',
                    primaryFocus: 'Digital product security'
                })
            """)
            print("✓ Sample regulations created")

        with driver.session() as session:
            print("Creating sample domains...")
            session.run("""
                CREATE (d1:Domain {
                    domainId: 'D-01',
                    name: 'Data Protection & Encryption',
                    description: 'Data protection, encryption, pseudonymisation, anonymisation',
                    primaryRegulatoryDriver: 'GDPR'
                })

                CREATE (d2:Domain {
                    domainId: 'D-02',
                    name: 'Vulnerability Management',
                    description: 'Vulnerability assessment, patching, coordinated disclosure',
                    primaryRegulatoryDriver: 'CRA'
                })
            """)
            print("✓ Sample domains created")

        driver.close()
        print()
        print("=" * 50)
        print("✓ Neo4j Setup Complete!")
        print("=" * 50)
        print()
        print("Connection Information:")
        print("  Neo4j Browser: http://localhost:7474")
        print("  Bolt Protocol: bolt://localhost:7687")
        print("  Username: neo4j")
        print("  Password: <no password>")
        print()
        print("Next Step: Verify nodes were created")
        print("  Run: python3 01_simple_setup.py")

    except Exception as e:
        print(f"Error: {e}")
        print("Make sure Neo4j is running: docker ps | grep aegis-phase1-kg")
        print("Check logs: docker logs aegis-phase1-kg")
        return 1

if __name__ == "__main__":
    main()
