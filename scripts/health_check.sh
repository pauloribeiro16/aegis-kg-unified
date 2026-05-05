#!/bin/bash
# health_check.sh — Verify system health before running eval
# Usage: ./scripts/health_check.sh [--verbose]

set -e

VERBOSE=false
if [ "$1" == "--verbose" ]; then
    VERBOSE=true
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    if [ "$VERBOSE" == "true" ]; then
        echo -e "$1"
    fi
}

fail() {
    echo -e "${RED}✗ FAIL: $1${NC}"
    exit 1
}

pass() {
    echo -e "${GREEN}✓ PASS: $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠ WARN: $1${NC}"
}

if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

export NEO4J_URI="${NEO4J_URI:-http://localhost:7474}"
export NEO4J_USER="${NEO4J_USER:-neo4j}"
export NEO4J_PASSWORD="${NEO4J_PASSWORD}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-ministral-3:latest}"
export LANGFUSE_PUBLIC_KEY="${LANGFUSE_PUBLIC_KEY}"
export LANGFUSE_SECRET_KEY="${LANGFUSE_SECRET_KEY}"
export LANGFUSE_BASE_URL="${LANGFUSE_BASE_URL:-http://localhost:3000}"
export MINIMAX_API_KEY="${MINIMAX_API_KEY}"

if [ -z "$NEO4J_PASSWORD" ]; then
    echo -e "${RED}✗ NEO4J_PASSWORD not set. Check .env file.${NC}"
    exit 1
fi

# ============================================
echo "=== AEGIS KG Health Check ==="
echo ""

# 1. Neo4j
log "Checking Neo4j..."
if curl -s -u neo4j:"$NEO4J_PASSWORD" "$NEO4J_URI/db/neo4j/tx/commit" -H "Content-Type: application/json" -d '{"statements":[{"statement":"RETURN 1"}]' > /dev/null 2>&1; then
    pass "Neo4j is running"
else
    fail "Neo4j is not accessible"
fi

# 2. Ollama
log "Checking Ollama..."
if curl -s "$OLLAMA_BASE_URL/api/tags" > /dev/null 2>&1; then
    pass "Ollama is running"
else
    fail "Ollama is not accessible"
fi

# 3. Langfuse
log "Checking Langfuse..."
if curl -s "$LANGFUSE_BASE_URL" > /dev/null 2>&1; then
    pass "Langfuse is running"
else
    warn "Langfuse is not accessible (tracing may fail)"
fi

# 4. Check baseline exists
log "Checking baseline..."
if [ -f "aegis_eval/results/baseline_stable_v1.json" ]; then
    pass "Baseline exists"
else
    fail "baseline_stable_v1.json not found"
fi

# 5. Smoke test (1 task)
log "Running smoke test..."
source /home/epmq/Desktop/Projects/shared-venv/bin/activate > /dev/null 2>&1

cd /home/epmq/Desktop/Projects/aegis-kg-unified
PYTHONPATH=. python3 aegis_eval/run_eval.py --tasks aegis_eval/task_bank.yaml --task list_all_regulations --trials 1 --verbose > /tmp/smoke_test.log 2>&1

if grep -q "Pass rate: 100.0%" /tmp/smoke_test.log; then
    pass "Smoke test passed"
else
    fail "Smoke test failed"
fi

echo ""
echo -e "${GREEN}=== All Health Checks Passed ===${NC}"
echo "System ready for evaluation."
exit 0