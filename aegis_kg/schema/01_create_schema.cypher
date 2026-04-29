// ============================================================
// AEGIS Phase 1 Knowledge Graph - Schema Creation
// AEGIS Methodology - Phase 1 Implementation
// Week 1, Day 3-4: Schema Design
// ============================================================

// SHOW EXISTING NODES
// Uncomment to see what's already in the graph
// CALL dbms.procedures() YIELD name;

// ============================================================
// 1. CREATE CONSTRAINTS
// ============================================================

CREATE CONSTRAINT regulation_id_unique IF NOT EXISTS FOR (r:Regulation) REQUIRE r.regulationId IS UNIQUE;

CREATE CONSTRAINT article_id_unique IF NOT EXISTS FOR (a:Article) REQUIRE a.articleId IS UNIQUE;

CREATE CONSTRAINT clause_id_unique IF NOT EXISTS FOR (c:Clause) REQUIRE c.clauseId IS UNIQUE;

CREATE CONSTRAINT domain_id_unique IF NOT EXISTS FOR (d:Domain) REQUIRE d.domainId IS UNIQUE;

CREATE CONSTRAINT subdomain_id_unique IF NOT EXISTS FOR (sd:SubDomain) REQUIRE sd.subDomainId IS UNIQUE;

CREATE CONSTRAINT company_context_id_unique IF NOT EXISTS FOR (cc:CompanyContext) REQUIRE cc.contextId IS UNIQUE;

CREATE CONSTRAINT complementarity_analysis_id_unique IF NOT EXISTS FOR (ca:ComplementarityAnalysis) REQUIRE ca.analysisId IS UNIQUE;

// ============================================================
// 2. CREATE INDEXES (for query optimization)
// ============================================================

CREATE INDEX regulation_name IF NOT EXISTS FOR (r:Regulation) ON (r.name);

CREATE INDEX article_number IF NOT EXISTS FOR (a:Article) ON (a.number);

CREATE INDEX clause_applicable IF NOT EXISTS FOR (c:Clause) ON (c.applicable);

CREATE INDEX clause_normative_intensity IF NOT EXISTS FOR (c:Clause) ON (c.normativeIntensity);

CREATE INDEX subdomain_name IF NOT EXISTS FOR (sd:SubDomain) ON (sd.name);

CREATE INDEX clause_regulation_id IF NOT EXISTS FOR (c:Clause) ON (c.regulationId);

CREATE INDEX clause_article_id IF NOT EXISTS FOR (c:Clause) ON (c.articleId);

// ============================================================
// 3. CREATE SAMPLE DATA (for testing)
// ============================================================

// Create Regulations
CREATE (r1:Regulation {
    regulationId: 'GDPR',
    name: 'GDPR',
    fullName: 'General Data Protection Regulation 2016/679',
    type: 'DATA_PROTECTION',
    effectiveDate: date('2018-05-25'),
    lastAmended: date('2023-12-07'),
    officialLink: 'https://eur-lex.europa.eu/eli/reg/2016/679',
    primaryFocus: 'Data protection and privacy'
});

CREATE (r2:Regulation {
    regulationId: 'CRA',
    name: 'CRA',
    fullName: 'Cyber Resilience Act (EU) 2022/2554',
    type: 'CYBER_SECURITY',
    effectiveDate: date('2024-12-12'),
    lastAmended: null,
    officialLink: 'https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52022PC2554',
    primaryFocus: 'Digital product security'
});

// Create Domains
CREATE (d1:Domain {
    domainId: 'D-01',
    name: 'Data Protection & Encryption',
    description: 'Data protection, encryption, pseudonymisation, anonymisation',
    primaryRegulatoryDriver: 'GDPR'
});

CREATE (d2:Domain {
    domainId: 'D-02',
    name: 'Vulnerability Management',
    description: 'Vulnerability assessment, patching, coordinated disclosure',
    primaryRegulatoryDriver: 'CRA'
});

CREATE (d3:Domain {
    domainId: 'D-03',
    name: 'Access Control',
    description: 'Authentication, authorization, session management',
    primaryRegulatoryDriver: 'GDPR,NIS2,CRA'
});

CREATE (d4:Domain {
    domainId: 'D-04',
    name: 'Incident Response',
    description: 'Breach notification, incident handling, lessons learned',
    primaryRegulatoryDriver: 'GDPR,NIS2,CRA,AI Act'
});

CREATE (d5:Domain {
    domainId: 'D-05',
    name: 'Data Lifecycle',
    description: 'Collection, processing, storage, deletion',
    primaryRegulatoryDriver: 'GDPR,AI Act'
});

CREATE (d6:Domain {
    domainId: 'D-06',
    name: 'Supply Chain',
    description: 'Third-party risk, vendor management',
    primaryRegulatoryDriver: 'DORA'
});

CREATE (d7:Domain {
    domainId: 'D-07',
    name: 'Secure Development',
    description: 'Secure coding, testing, certification',
    primaryRegulatoryDriver: 'CRA,NIS2,DORA'
});

CREATE (d8:Domain {
    domainId: 'D-08',
    name: 'Human Factors',
    description: 'Awareness training, security culture',
    primaryRegulatoryDriver: 'NIS2,GDPR'
});

CREATE (d9:Domain {
    domainId: 'D-09',
    name: 'Governance & Documentation',
    description: 'Policies, procedures, documentation, audit',
    primaryRegulatoryDriver: 'GDPR,CRA,NIS2,DORA,AI Act'
});

CREATE (d10:Domain {
    domainId: 'D-10',
    name: 'Monitoring & Audit',
    description: 'Logging, monitoring, intrusion detection',
    primaryRegulatoryDriver: 'DORA,AI Act,NIS2'
});

// Link Domains to Regulations (example)
// In production, you would load these from CSV
CREATE (d1)-[:COVERS]->(r1);
CREATE (d2)-[:COVERS]->(r2);
CREATE (d3)-[:COVERS]->(r1);
CREATE (d3)-[:COVERS]->(r2);
CREATE (d4)-[:COVERS]->(r1);
CREATE (d4)-[:COVERS]->(r2);
CREATE (d5)-[:COVERS]->(r1);
CREATE (d6)-[:COVERS]->(r2);
CREATE (d7)-[:COVERS]->(r1);
CREATE (d7)-[:COVERS]->(r2);
CREATE (d8)-[:COVERS]->(r1);
CREATE (d8)-[:COVERS]->(r2);
CREATE (d9)-[:COVERS]->(r1);
CREATE (d9)-[:COVERS]->(r2);
CREATE (d9)-[:COVERS]->(r1);
CREATE (d10)-[:COVERS]->(r2);
CREATE (d10)-[:COVERS]->(r2);
CREATE (d10)-[:COVERS]->(r1);

// Create Sample Company Context
CREATE (cc:CompanyContext {
    contextId: 'TINYTASK-2024-001',
    companyName: 'TinyTask Lda.',
    assessmentDate: date('2024-01-15'),
    industry: 'Technology',
    size: 'MICRO',
    location: 'Portugal',
    employeeCount: 8,
    revenue: 150000,
    dataTypes: ['Emails', 'Names', 'Passwords', 'Task content'],
    specialCategoryData: false,
    aiSystems: false,
    criticalInfrastructure: false,
    financialEntity: false
});

// ============================================================
// 4. VERIFY SCHEMA CREATION
// ============================================================

// Show created nodes
MATCH (r:Regulation)
RETURN r.regulationId, r.name AS regulation
ORDER BY r.regulationId;

// Show created domains
MATCH (d:Domain)
RETURN d.domainId, d.name AS domain
ORDER BY d.domainId;

// Show constraints
CALL dbms.constraints() YIELD name, type;

// Show indexes
CALL dbms.indexes() YIELD name, tokenNames, properties;

// ============================================================
// 5. SUMMARY
// ============================================================

RETURN '✓ Schema created successfully' AS status,
       '2 Regulations, 10 Domains, 1 CompanyContext' AS summary;
