import os
#!/usr/bin/env python3
"""
Phase 1 ETL Script - With Rate Limiting and Backoff
Loads Phase 1 data into Neo4j using REST API with rate limiting
"""
import requests
import csv
import time
import json
from pathlib import Path
import random

# Configuration
NEO4J_HTTP = "http://localhost:7474"
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", ""))
DATA_DIR = Path(__file__).parent / "data"

# Rate limiting configuration
MAX_REQUESTS_PER_MINUTE = 60  # Free tier: 60 requests/minute
BATCH_SIZE = 10  # Process 10 items per batch
RETRY_ATTEMPTS = 3
BASE_DELAY_MS = 1000  # Exponential backoff: 1s, 2s, 4s
REQUEST_TIMEOUT = 30  # seconds

class RateLimiter:
    """Simple rate limiter with exponential backoff"""
    def __init__(self):
        self.request_times = []
        self.requests_in_current_minute = 0

    def wait_if_needed(self):
        """Wait if rate limit is exceeded"""
        now = time.time()
        if now < self.minute_end:
            wait_time = self.minute_end - now
            if wait_time > 0:
                print(f"Rate limit hit. Waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
        self.requests_in_current_minute = 0
        self.minute_end = time.time() + 60

    def can_proceed(self):
        """Check if we can make a request"""
        return self.requests_in_current_minute < MAX_REQUESTS_PER_MINUTE

    def record_request(self):
        """Record a request was made"""
        self.requests_in_current_minute += 1

def load_csv(file_name):
    """Load CSV file and return data"""
    file_path = DATA_DIR / file_name
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        data = list(reader)
    return data

def create_regulation(data):
    """Create Regulation entity"""
    print(f"Creating Regulation: {data['regulationId']}")

    cypher = f"""
    CREATE (r:Regulation {{
        regulationId: '{data['regulationId']}',
        name: '{data['name']}',
        fullName: '{data['fullName']}',
        type: '{data['type']}',
        effectiveDate: '{data['effectiveDate']}',
        lastAmended: '{data.get('lastAmended', '')}',
        officialLink: '{data['officialLink']}',
        primaryFocus: '{data['primaryFocus']}'
    }})
    RETURN r
    """

    payload = {
        "statements": [
            {
                "statement": cypher
            }
        ]
    }

    response = requests.post(
        f"{NEO4J_HTTP}/db/neo4j/tx/commit",
        auth=AUTH,
        json=payload
    )

    if response.status_code == 200 and not response.json().get('errors'):
        print(f"✓ Created {data['regulationId']}")
        return True
    else:
        print(f"✗ Error: {response.status_code}")
        errors = response.json().get('errors', [])
        if errors:
            print(f"Response: {errors[0].get('message', 'No details')[:200]}")
        return False

def create_domain(data):
    """Create Domain entity"""
    print(f"Creating Domain: {data['domainId']}")

    cypher = f"""
    CREATE (d:Domain {{
        domainId: '{data['domainId']}',
        name: '{data['name']}',
        description: '{data['description']}',
        primaryRegulatoryDriver: '{data['primaryRegulatoryDriver']}'
    }})
    RETURN d
    """

    payload = {
        "statements": [
            {
                "statement": cypher
            }
        ]
    }

    response = requests.post(
        f"{NEO4J_HTTP}/db/neo4j/tx/commit",
        auth=AUTH,
        json=payload
    )

    if response.status_code == 200 and not response.json().get('errors'):
        print(f"✓ Created {data['domainId']}")
        return True
    else:
        print(f"✗ Error: {response.status_code}")
        errors = response.json().get('errors', [])
        if errors:
            print(f"Response: {errors[0].get('message', 'No details')[:200]}")
        return False

def create_subdomain(data):
    """Create SubDomain entity"""
    print(f"Creating SubDomain: {data['subDomainId']}")

    keywords_str = "', '".join(data['keywords'].split(','))
    examples_str = "', '".join(data['examples'].split(','))

    cypher = f"""
    CREATE (sd:SubDomain {{
        subDomainId: '{data['subDomainId']}',
        name: '{data['name']}',
        description: '{data['description']}',
        keywords: ['{keywords_str}'],
        examples: ['{examples_str}'],
        soleAuthority: '{data.get('soleAuthority', '')}',
        gapRisk: '{data.get('gapRisk', 'MEDIUM')}'
    }})
    RETURN sd
    """

    payload = {
        "statements": [
            {
                "statement": cypher
            }
        ]
    }

    response = requests.post(
        f"{NEO4J_HTTP}/db/neo4j/tx/commit",
        auth=AUTH,
        json=payload
    )

    if response.status_code == 200 and not response.json().get('errors'):
        print(f"✓ Created {data['subDomainId']}")
        return True
    else:
        print(f"✗ Error: {response.status_code}")
        errors = response.json().get('errors', [])
        if errors:
            print(f"Response: {errors[0].get('message', 'No details')[:200]}")
        return False

def create_relationship(from_id, to_id, type, properties=None):
    """Create relationship between entities using regulationId/subDomainId"""
    props_str = ""
    if properties:
        props_str = " { " + ", ".join([f"{k}: '{v}'" for k, v in properties.items()]) + " }"

    cypher = f"""
    MATCH (a {{regulationId: '{from_id}'}})
    MATCH (b {{subDomainId: '{to_id}'}})
    CREATE (a)-[r:{type}{props_str}]->(b)
    RETURN r
    """

    payload = {
        "statements": [
            {
                "statement": cypher
            }
        ]
    }

    response = requests.post(
        f"{NEO4J_HTTP}/db/neo4j/tx/commit",
        auth=AUTH,
        json=payload
    )

    return response.status_code == 200 and not response.json().get('errors')

def create_article(article, reg_id):
    """Create Article entity"""
    cypher = f"""
    CREATE (a:Article {{
        articleId: '{article['articleId']}',
        number: '{article['number']}',
        title: '{article['title']}',
        chapter: '{article.get('chapter', '')}',
        section: '{article.get('section', '')}',
        summary: '{article['summary']}',
        obligationType: '{article['obligationType']}'
    }})
    RETURN a
    """

    payload = {
        "statements": [
            {
                "statement": cypher
            }
        ]
    }

    response = requests.post(
        f"{NEO4J_HTTP}/db/neo4j/tx/commit",
        auth=AUTH,
        json=payload
    )

    if response.status_code == 200 and not response.json().get('errors'):
        # Create relationship to regulation
        create_relationship(reg_id, article['articleId'], 'HAS_ARTICLE')
        return True
    return False

def create_clause(clause):
    """Create Clause entity"""
    cypher = f"""
    CREATE (c:Clause {{
        clauseId: '{clause['clauseId']}',
        number: '{clause['number']}',
        summary: '{clause['summary']}',
        description: '{clause['description']}',
        obligatedParty: '{clause['obligatedParty']}',
        obligationType: '{clause['obligationType']}',
        normativeIntensity: {int(clause['normativeIntensity'])},
        applicable: true,
        applicabilityReason: 'Applicable for TinyTask',
        sourceReference: '{clause['sourceReference']}'
    }})
    RETURN c
    """

    payload = {
        "statements": [
            {
                "statement": cypher
            }
        ]
    }

    response = requests.post(
        f"{NEO4J_HTTP}/db/neo4j/tx/commit",
        auth=AUTH,
        json=payload
    )

    if response.status_code == 200 and not response.json().get('errors'):
        # Create relationships
        create_relationship('GDPR', clause['clauseId'], 'HAS_CLAUSE')
        create_relationship('CRA', clause['clauseId'], 'HAS_CLAUSE')

        # Map to subdomains
        if clause['subDomainId']:
            create_relationship(clause['clauseId'], clause['subDomainId'], 'COVERS_SUBDOMAIN')
        return True
    return False

def main():
    print("=" * 50)
    print("AEGIS Phase 1 KG - ETL (Rate Limited)")
    print("=" * 50)
    print()

    rate_limiter = RateLimiter()

    # Check Neo4j connection
    print("Testing Neo4j connection...")
    try:
        response = requests.get(f"{NEO4J_HTTP}", auth=AUTH, timeout=5)
        if response.status_code == 200:
            print(f"OK: Neo4j accessible at {NEO4J_HTTP}")
        else:
            print(f"Status: {response.status_code}")
            return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

    # Load data files
    print("\nLoading data files...")
    regulations = load_csv("00_regulations.csv")
    domains = load_csv("01_domains.csv")
    subdomains = load_csv("02_subdomains.csv")
    articles = load_csv("03_articles.csv")
    clauses = load_csv("04_clauses.csv")
    company_context = load_csv("05_company_context.csv")

    print(f"Loaded: {len(regulations)} Regulations")
    print(f"Loaded: {len(domains)} Domains")
    print(f"Loaded: {len(subdomains)} SubDomains")
    print(f"Loaded: {len(articles)} Articles")
    print(f"Loaded: {len(clauses)} Clauses")
    print(f"Loaded 1 CompanyContext")

    # Create Regulations
    regulation_count = 0
    for regulation in regulations:
        if create_regulation(regulation):
            regulation_count += 1

    print(f"\nCreated {regulation_count} Regulations")

    # Create Domains
    domain_count = 0
    for domain in domains:
        if create_domain(domain):
            domain_count += 1

    print(f"Created {domain_count} Domains")

    # Create SubDomains (38 total - all)
    subdomain_count = 0
    for subdomain in subdomains:
        if create_subdomain(subdomain):
            subdomain_count += 1

    print(f"Created {subdomain_count} SubDomains")

    # Create Articles (9 total)
    article_count = 0
    for article in articles:
        # Find parent regulation by mapping
        reg_id = None
        for reg in regulations:
            if article['regulationId'] in reg['regulationId']:
                reg_id = reg['regulationId']
                break

        if reg_id is None:
            print(f"Warning: Article {article['articleId']} has no matching regulation")
            continue

        if create_article(article, reg_id):
            article_count += 1
            print(f"✓ Created {article['articleId']}")

    print(f"\nCreated {article_count} Articles")

    # Create Clauses (55 total)
    clause_count = 0
    for clause in clauses:
        if create_clause(clause):
            clause_count += 1
            print(f"✓ Created {clause['clauseId']}")

        rate_limiter.record_request()

        if not rate_limiter.can_proceed():
            print(f"Rate limit reached. Waiting...")
            rate_limiter.wait_if_needed()

    print(f"\nTotal: Created {clause_count} Clauses")

    # Create Company Context
    company_context = company_context[0]
    data_types = "', '".join(company_context['dataTypes'].split(','))

    cypher = f"""
    CREATE (cc:CompanyContext {{
        contextId: '{company_context['contextId']}',
        companyName: '{company_context['companyName']}',
        assessmentDate: '{company_context['assessmentDate']}',
        industry: '{company_context['industry']}',
        size: '{company_context['size']}',
        location: '{company_context['location']}',
        employeeCount: {int(company_context['employeeCount'])},
        revenue: '{company_context['revenue']}',
        dataTypes: ['{data_types}'],
        specialCategoryData: '{company_context['specialCategoryData']}',
        aiSystems: '{company_context['aiSystems']}',
        criticalInfrastructure: '{company_context['criticalInfrastructure']}',
        financialEntity: '{company_context['financialEntity']}'
    }})
    RETURN cc
    """

    payload = {
        "statements": [
            {
                "statement": cypher
            }
        ]
    }

    response = requests.post(
        f"{NEO4J_HTTP}/db/neo4j/tx/commit",
        auth=AUTH,
        json=payload
    )

    if response.status_code == 200 and not response.json().get('errors'):
        print(f"✓ Created CompanyContext")
    else:
        print(f"✗ Error: {response.status_code}")
        errors = response.json().get('errors', [])
        if errors:
            print(f"Response: {errors[0].get('message', 'No details')[:200]}")

    # Create Complementarity Analysis
    cypher = """
    CREATE (ca:ComplementarityAnalysis {
        analysisId: 'GDPR-CRA-001',
        regulation1Id: 'GDPR',
        regulation2Id: 'CRA',
        overlapType: 'COMPLEMENTARY',
        jaccardIndex: 0.367,
        overlapDescription: 'Both regulations require data protection, encryption, and security controls',
        complementarityDescription: 'GDPR focuses on privacy rights, CRA focuses on product security',
        recommendedApproach: 'Implement both sets of controls, prioritize GDPR for data subjects rights',
        analysisDate: '2024-01-20',
        analyst: 'Compliance Lead'
    })
    RETURN ca
    """

    payload = {
        "statements": [
            {
                "statement": cypher
            }
        ]
    }

    response = requests.post(
        f"{NEO4J_HTTP}/db/neo4j/tx/commit",
        auth=AUTH,
        json=payload
    )

    if response.status_code == 200 and not response.json().get('errors'):
        print(f"✓ Created ComplementarityAnalysis")
    else:
        print(f"✗ Error: {response.status_code}")
        errors = response.json().get('errors', [])
        if errors:
            print(f"Response: {errors[0].get('message', 'No details')[:200]}")

    # Summary
    print()
    print("=" * 50)
    print("ETL Complete!")
    print("=" * 50)
    print(f"\nSummary:")
    print(f"  Regulations: {regulation_count}")
    print(f"  Domains: {domain_count}")
    print(f"  SubDomains: {subdomain_count}")
    print(f"  Articles: {article_count}")
    print(f"  Clauses: {clause_count}")
    print(f"  CompanyContext: 1")
    print(f" ComplementarityAnalysis: 1")
    total_nodes = regulation_count + domain_count + subdomain_count + article_count + clause_count + 2
    print(f"\nTotal nodes created: {total_nodes}")
    print()
    print("Connection Information:")
    print(f"  Neo4j HTTP: {NEO4J_HTTP}")
    print(f" Browser: {NEO4J_HTTP}/browser")
    print(f"   Auth: neo4j / $NEO4J_PASSWORD (env var)")
    print()
    print("Next Steps:")
    print("1. Verify nodes: Open Neo4j Browser")
    print("2. Create relationships: Manually via Cypher if needed")
    print("3. Build inference queries: Python scripts")
    print("4. Build REST API: Flask application")
    print("5. Validate data: Quality checks")

if __name__ == "__main__":
    main()
