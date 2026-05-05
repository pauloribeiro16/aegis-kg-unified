# PHASE 1 ENRICHMENT PLAN — AEGIS-KG-Unified

**Version:** 1.0
**Created:** 2026-05-05
**Purpose:** Canonical reference for Phase 1 analytical enrichment batches.

---

## Context

Phase 1 data (Regulations, Articles, Clauses, Domains, SubDomains, NIST CSF 2.0) is fully loaded and validated. The foundational mapping `(Clause)-[:MAPPED_TO]->(SubDomain)` and `(Domain)-[:HAS_SUBDOMAIN]->(SubDomain)` relationships are established. However, all analytical computations (Jaccard, density, sole authority) are **hardcoded static values**, not derived from the graph.

This plan adds **14 batches** of dynamic analytical capabilities to Phase 1.

---

## Schema Files — Both Must Be Updated Together

Two files must always be updated together for every batch (they power the agent and judge):

| File | Used By | Purpose |
|------|---------|---------|
| `aegis_agents/tools/schema_tool.py` | LangGraph agent (Cypher generation) | Node properties, relationship names, useful query patterns |
| `aegis_eval/schema_context.py` | Minimax judge (answer evaluation) | Full schema description + working query patterns |

**Rule:** When adding new properties, add them to BOTH files. When adding query patterns, add them to BOTH files under matching sections.

---

## Relationship Name Reference (RESOLVED)

| Relationship | Count | Status |
|-------------|-------|--------|
| `MAPPED_TO` (Clause→SubDomain) | 150 | ✅ Canonical |
| `HAS_SUBDOMAIN` (Domain→SubDomain) | 38 | ✅ Canonical |
| `HAS_CLAUSE` (Regulation→Clause) | 150 | ✅ Canonical |
| `OVERLAPS_WITH` (ComplementarityAnalysis→Regulation) | 20 | ✅ Canonical |

---

## Batches

### Batch 9 — Dynamic Jaccard + Density
**Goal:** Compute SubDomain density metrics from graph; replace static Jaccard with dynamic computation.

**New SubDomain Properties:**
- `clauseCount: Integer` — count of clauses mapped to this SubDomain
- `regulationCount: Integer` — count of distinct regulations covering this SubDomain
- `coveringRegulations: List[String]` — list of regulationIds covering this SubDomain
- `densityScore: Float` — clauseCount / 5.0 (normalized by max 5 regulations)
- `avgNormativeIntensity: Float` — average NI of covering clauses
- `weightedDensity: Float` — sum(NI) / 15.0 (NI-weighted, max theoretical 1.0)

**ComplementarityAnalysis Changes:**
- Add `dynamicJaccard: Float` — recomputed from actual graph
- Add `dynamicSharedSubDomainCount: Integer` — actual shared SubDomain count
- Add `jaccardSource: String` — 'DYNAMIC' or 'STATIC'

**ETL Script:** `12_compute_density_metrics.py`

**API New/Modified:**
- `GET /api/density` — SubDomain density ranking (new)
- `GET /api/coverage` — add `by_subdomain` (modified)
- `GET /api/overlap` — use `dynamicJaccard` (modified)
- `GET /api/domains` — add density fields to SubDomain output

**Task Bank Additions (7 tasks):**
- `subdomain_density_ranking`
- `multi_regulation_subdomains`
- `regulation_density_comparison`
- `dynamic_jaccard_overlap`
- `normative_intensity_density`
- `sparse_coverage_subdomains`
- `density_by_domain`

---

### Batch 10 — NI-Weighted Coverage
**Goal:** Weight coverage by normative intensity. SubDomains with high-NI clauses have higher effective coverage.

**New SubDomain Properties:**
- `effectiveCoverage: Float` — sum of NI values of all clauses mapped to this SubDomain (max theoretical: 3 × 38 = 114)
- `effectiveCoverageTier: String` — HIGH (>= 8.0), MEDIUM (>= 4.0), LOW (< 4.0)

**New Regulation Properties:**
- `effectiveCoverageScore: Float` — sum of all clause NI values for this regulation's clauses
- `effectiveCoverageTier: String` — HIGH (>= 50.0), MEDIUM (>= 25.0), LOW (< 25.0)

**ETL Script:** `13_compute_effective_coverage.py`

**API New/Modified:**
- `GET /api/coverage` — add `effectiveCoverage`, `effectiveCoverageTier` to `by_subdomain`; add `effectiveCoverageScore`, `effectiveCoverageTier` to `by_regulation`

**Task Bank Additions (5 tasks):**
- `effective_coverage_top_subdomains`
- `effective_coverage_tier_distribution`
- `regulation_effective_coverage_ranking`
- `low_effective_coverage_subdomains`
- `high_effective_coverage_detail`

---

### Batch 11 — Coverage Heatmap
**Goal:** Expose a 38×5 matrix (SubDomain × Regulation) of clause counts.

**API New:**
- `GET /api/heatmap` — full matrix of clause counts per SubDomain per regulation

---

### Batch 12 — Multi-Regulation Hotspots
**Goal:** Identify SubDomains covered by 3+ regulations (regulatory "hot spots").

**Changes:**
- Compute `hotspotScore: Integer` — number of regulations covering this SubDomain
- Add `hotspotTier: String` — CRITICAL (5), HIGH (4), MODERATE (3), LOW (1-2)

**API New/Modified:**
- `GET /api/hotspots` — SubDomains with 3+ regulations
- `/api/domains` — add hotspotTier to SubDomain output

---

### Batch 13 — Dynamic Strategic Tensions
**Goal:** Replace 4 hardcoded StrategicTension nodes with automatic detection from graph topology.

**Detection Logic:**
- For each SubDomain with clauses from 2+ regulations
- Compare avgNI deltas, check timeline conflicts, identify overlapping clauses
- Create `StrategicTension` nodes for detected tensions
- Flag: TEMPORAL_CONFLICT (different notification deadlines), REQUIREMENT_CONFLICT (NI delta > 0.5), FREQUENCY_MISMATCH (different obligation types)

**ETL Script:** `13_compute_strategic_tensions.py`

**Changes:**
- Add `conflictType: String`
- Add `normativeIntensityDelta: Float`
- Add `triggerSubDomains: List[String]`

**API New/Modified:**
- `GET /api/tensions` — dynamically computed tensions

---

### Batch 14 — Conflict Severity Score
**Goal:** Quantify conflict severity between regulation pairs.

**Changes:**
- Add `conflictSeverityScore: Float` — computed from: Jaccard (overlap weight) + NI delta + timeline delta
- Add `severityComponents: Map` — breakdown of contributing factors

**API New:**
- `GET /api/conflicts/severity` — ranked list of regulation pair conflicts

---

### Batch 15 — NIST API + Cross-Framework Gap
**Goal:** Expose NIST CSF 2.0 data via API; compute EU-vs-NIST gap analysis.

**API New:**
- `GET /api/nist/functions` — 6 NIST functions
- `GET /api/nist/categories` — 34 categories
- `GET /api/nist/controls` — all controls
- `GET /api/nist/controls?function=PR` — controls by function
- `GET /api/nist/mappings` — all FrameworkControl→SubDomain mappings

**Cross-Framework Gap:**
- For each SubDomain: EU-coverage (exists) vs NIST-coverage (has MAPS_TO_SUBDOMAIN)
- Identify SubDomains where NIST has controls but EU doesn't cover
- Identify SubDomains where EU covers but NIST has no control mapping

**API New:**
- `GET /api/gap-analysis/cross-framework` — EU-vs-NIST gap matrix

---

### Batch 16 — NIST Control Effectiveness Scoring
**Goal:** Score each NIST control by how many EU regulation clauses map to its SubDomains.

**Changes:**
- Add `euClauseCount: Integer` — how many EU clauses map to SubDomains this control covers
- Add `euCoverageScore: Float` — normalized 0-1
- Add `controlEffectivenessTier: String` — HIGH/MEDIUM/LOW

**API New:**
- `GET /api/nist/controls/effectiveness` — NIST controls ranked by EU coverage

---

### Batch 17 — Clause-Level Overlap Detail
**Goal:** For each regulation pair, list specific SubDomains and clauses that overlap.

**Changes:**
- Add `overlapDetail: List[Map]` — per pair: shared SubDomains + specific clauses from each regulation

**API New:**
- `GET /api/overlap/detail?reg1=GDPR&reg2=CRA` — detailed clause-level overlap

---

### Batch 18 — Dynamic Sole Authority
**Goal:** Replace 8 hardcoded `SOLE_AUTHORITY` relationships with graph-derived computation.

**Detection Logic:**
- For each SubDomain, count distinct regulations covering it via `MAPPED_TO`
- If count == 1 → create `SOLE_AUTHORITY` relationship to that sole regulation

**Changes:**
- Recompute from graph, update SubDomain `soleAuthority` property
- Add `soleAuthoritySource: String` — 'DYNAMIC' or 'GROUND_TRUTH'
- Remove hardcoded sole authority ETL; replace with dynamic computation

**API:** `GET /api/sole-authority` already exists; validate it matches graph-derived data

---

### Batch 19 — Applicability Engine
**Goal:** Filter regulations/clauses by company profile.

**CompanyContext Enhancement:**
- Add properties: `sector`, `size`, `country`, `dataProcessingVolume`, `cloudProvider`
- Add `aiSystems: Boolean`, `financialEntity: Boolean`, `criticalInfrastructure: Boolean`

**ApplicabilityCondition Nodes:**
- Create for each regulation: conditions that trigger applicability
- E.g., CRA applies if company develops products with digital elements

**API New:**
- `GET /api/applicability/check` — given a company profile, return applicable regulations, clauses, obligations
- `GET /api/company-context` — return company context

---

### Batch 20 — SubDomain Criticality Score
**Goal:** Composite score per SubDomain: density × avgNI × gapRisk weight.

**Formula:**
```
criticality = densityScore * (avgNI / 3.0) * gapRiskWeight
gapRiskWeight: HIGH=3, MEDIUM=2, LOW=1
```

**Changes:**
- Add `criticalityScore: Float`
- Add `criticalityTier: String` — CRITICAL (≥2.0), HIGH (≥1.0), MODERATE (≥0.5), LOW (<0.5)

**API New:**
- `GET /api/domains/criticality` — domains and SubDomains ranked by criticality

---

### Batch 21 — Regulation Aggressiveness Index
**Goal:** Rank regulations by "aggressiveness" (how many high-NI clauses, how many sole-authority SubDomains).

**Formula per regulation:**
```
aggressiveness = (ni3Clauses / totalClauses) * 0.4
              + (soleAuthoritySubDomains / 8) * 0.3
              + (coveredSubDomains / 38) * 0.3
```

**Changes:**
- Add `Regulation.aggressivenessIndex: Float`
- Add `Regulation.aggressivenessTier: String` — HIGH/MEDIUM/LOW

**API New:**
- `GET /api/regulations/aggressiveness` — ranked list

---

### Batch 22 — Compliance Burden Score
**Goal:** Estimate compliance effort per regulation given the company's regulatory footprint.

**Formula per regulation:**
```
burden = obligationCount * avgNI * timelinePressureFactor
timelinePressureFactor = max(1.0, count(breach_notifications_with_deadline < 72h) / 3)
```

**Changes:**
- Add `Regulation.complianceBurdenScore: Float`
- Add `Regulation.burdenComponents: Map`

**API New:**
- `GET /api/regulations/burden` — ranked list

---

## Execution Rule

**Iterative approach — one batch at a time:**
1. Implement batch ETL, schema, API changes
2. Add task_bank entries for the new capability
3. Test **only the new tasks** with agent eval (not the full task bank)
4. If agent score ≥ 3.0 → commit, move to next batch
5. If agent score < 3.0 → diagnose error, fix ETL/schema/API/prompts, retry only the failed task
6. Never proceed to next batch until current batch passes eval

**CRITICAL — Don't Break Previous Batches:**
- Never rename or remove properties that previous batches depend on
- Never change relationship names that are already canonical (HAS_SUBDOMAIN, MAPPED_TO, etc.)
- Never delete or alter data that earlier ETLs have computed
- If a new batch needs to change something, create a NEW property with a new name

**Schema Files — Always Update Both:**
- `aegis_agents/tools/schema_tool.py` (used by LangGraph agent for cypher generation)
- `aegis_eval/schema_context.py` (used by eval judge for answer evaluation)
- Update both simultaneously for every batch

**New Batch Checklist:**
- [ ] ETL script written and run against Neo4j
- [ ] `aegis_agents/tools/schema_tool.py` — new properties + patterns added
- [ ] `aegis_eval/schema_context.py` — new properties + patterns added
- [ ] API endpoints modified or created
- [ ] Task bank entries added (3–6 per batch)
- [ ] New tasks tested individually with `run_eval.py --task <id> --trials 1`
- [ ] All new tasks pass (score ≥ 3.0)
- [ ] Committed to feature branch

**Diagnosis & Fix Protocol (when a task fails):**
1. Read the judge JSON output to identify which dimension scored low
2. Check generated Cypher vs expected Cypher — find the mismatch
3. If property name wrong → update both schema files
4. If relationship name wrong → update both schema files
5. If ETL not computing → re-run ETL or fix it
6. If API returning wrong shape → fix API endpoint
7. If query pattern wrong → update schema USEFUL QUERIES section
8. Re-test only the failed task, not the whole bank

**After All Batches Complete:**
Run full eval: `PYTHONPATH=. python3 aegis_eval/run_eval.py --tasks aegis_eval/task_bank.yaml --trials 1`

---

## Batch Dependency Graph

```
Batch 9 (Density)
  └─ Batch 10 (NI-Weighted) ← requires Batch 9 properties
  └─ Batch 11 (Heatmap) ← requires Batch 9 properties
  └─ Batch 12 (Hotspots) ← requires Batch 9 properties
  └─ Batch 18 (Sole Authority) ← requires Batch 9 properties

Batch 13 (Tensions) ← requires Batch 9 + Batch 12
  └─ Batch 14 (Conflict Severity) ← requires Batch 13

Batch 15 (NIST API) ← standalone, but feeds Batch 16
  └─ Batch 16 (NIST Effectiveness) ← requires Batch 15

Batch 17 (Clause Overlap) ← requires Batch 9

Batch 19 (Applicability Engine) ← requires Batch 18

Batch 20 (Criticality) ← requires Batch 9 + Batch 12 + Batch 18

Batch 21 (Aggressiveness) ← requires Batch 9 + Batch 18

Batch 22 (Burden) ← requires Batch 9 + Batch 21
```

---

## Validation

After each batch, run:
```bash
cd aegis_kg && python validation/01_validate_phase1.py
PYTHONPATH=. python3 aegis_eval/run_eval.py --tasks aegis_eval/task_bank.yaml --trials 1 --verbose
```

Pass threshold: **≥ 3.0 average** on new tasks.

---

## Baseline Reference

- **Baseline v1.1:** 84.4% pass rate (38/45 tasks), 5 categories, 45 tasks
- **Weakest category:** nist_retrieval (avg ~3.04)
- **Strongest dimension:** tool_usage (4.13)
- **Target for enrichment batches:** maintain ≥ 3.0 on all new analytical tasks

---

**End of PHASE1_ENRICHMENT_PLAN.md**
