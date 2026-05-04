# WORKFLOW.md — AEGIS-KG-Unified Development Workflow

**Version:** 1.0
**Created:** 2026-05-04
**Purpose:** Guide for mastertaining stable codebase while incrementing features.

---

## Overview

This project uses a **branch-based workflow** to keep the `master` branch always stable while allowing controlled feature development.

### Core Principle

```
master (stable) ←←←←←←←←←←←←←←←←←←←←←←←←←←←
    ↑
    └── feature/add-sanctions (test here)
          feature/fix-nulls (test here)
```

The `master` branch contains the **verified stable baseline**. All new work happens in feature branches.

---

## Quick Reference

| Action | Command |
|--------|---------|
| Create feature branch | `./scripts/create-feature.sh "add-sanctions"` |
| Run quick test | `./scripts/test-quick.sh` |
| View baseline | `cat aegis_eval/results/baseline_stable_v1.json` |
| Check branch | `git branch` |
| Switch to master | `git checkout master` |

---

## Workflow Steps

### 1. Start New Feature

```bash
# Make sure you're on master
git checkout master

# Create and switch to new feature branch
./scripts/create-feature.sh "add-sanctions"
```

This will:
- Verify you're on `master`
- Pull latest changes
- Create branch `feature/add-sanctions`
- Run smoke test to verify system is stable
- Show next steps

### 2. Develop

Make your changes (code, data, etc.)

### 3. Test During Development

```bash
./scripts/test-quick.sh
```

This runs 5 representative tasks (~5 min) and compares with baseline.

**Pass criteria:** Pass rate >= 85%

### 4. Commit Changes

```bash
git add .
git commit -m "Add: description of changes"
```

### 5. Push Branch

```bash
git push origin feature/add-sanctions
```

### 6. Create Pull Request

1. Go to GitHub: https://github.com/pauloribeiro16/aegis-kg-unified
2. Click "Compare & pull request"
3. Select `feature/add-sanctions` → `master`
4. GitHub Actions will run **automatic tests**

### 7. Review & Merge

After tests pass:
1. Review the changes in the PR
2. Check the "Files changed" tab
3. Comment or request changes if needed
4. **You approve and merge** (manual approval required)

---

## Understanding Test Results

### Quick Test Output

```
=== AEGIS Quick Test (~5 min) ===

1. Checking system health...
   ✓ Neo4j
   ✓ Ollama

2. Running evaluation (5 tasks, ~5 min)...
   [PASS] list_all_regulations_001...
   [PASS] count_total_clauses_001...
   ...

3. Analyzing results...

Baseline pass rate:  88.9%
Current pass rate:   90.0%

✓ PASS: 90.0% >= 85% threshold
```

### If Test Fails

```
Current pass rate:   72.0%

✗ FAIL: 72.0% < 85% threshold

Dimension comparison:
  reasoning_quality: 4.00 → 3.80 (-0.20) [SLIGHT_DROP]
  cypher_correctness: 3.97 → 2.50 (-1.47) [REGRESSION]
```

**What to check:**
1. Did you change schema_context.py or Cypher queries?
2. Did you modify the Neo4j data?
3. Is Ollama running correctly?

---

## Rollback (If Something Goes Wrong)

### Go back to stable master

```bash
git checkout master
```

### Delete broken feature branch

```bash
git branch -D feature/broken-feature
```

### Start fresh

```bash
./scripts/create-feature.sh "fix-the-issue"
```

---

## Branch Naming Convention

| Type | Example | Purpose |
|------|---------|---------|
| Feature | `feature/add-sanctions` | New functionality |
| Fix | `feature/fix-article-nulls` | Bug fixes |
| Enhancement | `enhancement/improve-agent` | Improvements |
| Docs | `docs/update-readme` | Documentation |

**Rules:**
- Use lowercase
- Use hyphens to separate words
- Be descriptive but concise

---

## Baseline Reference

Current stable baseline: `baseline_stable_v1.json`

**Metrics:**
- Pass rate: 88.9% (40/45 tasks)
- reasoning_quality: 4.00
- cypher_correctness: 3.97
- query_effectiveness: 3.90
- tool_usage: 4.28
- feedback_loop_benefit: 3.04

---

## Scripts Reference

| Script | Purpose | Duration |
|--------|---------|----------|
| `create-feature.sh` | Create new feature branch | ~3 min |
| `test-quick.sh` | Run 5-task regression test | ~5 min |
| `health_check.sh` | Full system health check | ~5 min |

---

## Troubleshooting

### "You must be on 'master' branch"
```bash
git checkout master
./scripts/create-feature.sh "your-feature"
```

### Smoke test fails during create
The system may be unstable. Run health check:
```bash
./scripts/health_check.sh
```

### Quick test fails after changes
1. Review what you changed
2. If unrelated: check infrastructure (Neo4j, Ollama)
3. If caused by changes: fix or revert

### GitHub Actions fails
Check the workflow logs on GitHub for details.

---

## Questions?

- Check `AGENTS.md` for project reference
- Check `MEMORY.md` for known issues
- Check `KG_MANIFEST.md` for data model

---

**Version:** 1.0
**Last Updated:** 2026-05-04
