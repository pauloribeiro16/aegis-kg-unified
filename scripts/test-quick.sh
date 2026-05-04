#!/bin/bash
# test-quick.sh — Quick regression test (5 tasks, ~5 min)
#
# Usage:
#   ./scripts/test-quick.sh
#
# This script:
#   1. Verifies system health (Neo4j, Ollama)
#   2. Runs 5 representative tasks
#   3. Compares results with baseline
#   4. Reports pass/fail with detailed analysis

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== AEGIS Quick Test (~5 min) ===${NC}"
echo ""

echo -e "${BLUE}1. Loading environment...${NC}"

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
    echo -e "${RED}✗ NEO4J_PASSWORD not set. Check .env file or environment.${NC}"
    exit 1
fi

if [ -z "$MINIMAX_API_KEY" ]; then
    echo -e "${RED}✗ MINIMAX_API_KEY not set. Check .env file or environment.${NC}"
    exit 1
fi

echo -e "   ${GREEN}✓${NC} Environment loaded"

echo ""
echo -e "${BLUE}2. Checking system health...${NC}"

if curl -s -u neo4j:${NEO4J_PASSWORD} "${NEO4J_URI}/db/neo4j/tx/commit" -H "Content-Type: application/json" -d '{"statements":[{"statement":"RETURN 1"}]' > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} Neo4j"
else
    echo -e "   ${RED}✗${NC} Neo4j not accessible"
    exit 1
fi

if curl -s "${OLLAMA_BASE_URL}/api/tags" > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} Ollama"
else
    echo -e "   ${RED}✗${NC} Ollama not accessible"
    exit 1
fi

echo ""
echo -e "${BLUE}3. Running evaluation (5 tasks)...${NC}"

if [ ! -f "/home/epmq/Desktop/Projects/shared-venv/bin/activate" ]; then
    echo -e "${RED}✗ Virtual environment not found${NC}"
    exit 1
fi

source /home/epmq/Desktop/Projects/shared-venv/bin/activate > /dev/null 2>&1

cd /home/epmq/Desktop/Projects/aegis-kg-unified

TEMP_TASKS=$(mktemp)
cat > "$TEMP_TASKS" << 'EOF'
tasks:
- id: list_all_regulations
  category: basic_retrieval
  question: List all regulations in the knowledge graph
- id: count_total_clauses
  category: basic_retrieval
  question: How many clauses are there in total?
- id: gdpr_clause_count
  category: clause_lookup
  question: How many clauses does GDPR have?
- id: shared_subdomains_between_regulations
  category: cross_regulation
  question: Which subdomains have clauses from both GDPR and CRA?
- id: nist_controls_by_function
  category: nist_retrieval
  question: How many controls does each NIST function have?
EOF

PYTHONPATH=. python3 aegis_eval/run_eval.py --tasks "$TEMP_TASKS" --trials 1 2>&1 | tee /tmp/test-quick-output.log
rm -f "$TEMP_TASKS"

echo ""
echo -e "${BLUE}4. Analyzing results...${NC}"

RESULT_FILE=$(ls -t aegis_eval/results/summary_*.json 2>/dev/null | head -1)

if [ -z "$RESULT_FILE" ] || [ ! -f "$RESULT_FILE" ]; then
    echo -e "${RED}✗ No result file found${NC}"
    exit 1
fi

python3 << 'PYEOF'
import json
import sys
import os

os.chdir("/home/epmq/Desktop/Projects/aegis-kg-unified")

baseline_file = "aegis_eval/results/baseline_stable_v1.json"
current_file = sys.argv[1] if len(sys.argv) > 1 else None

if not current_file:
    import glob
    files = sorted(glob.glob("aegis_eval/results/summary_*.json"), reverse=True)
    current_file = files[0] if files else None

try:
    baseline = json.load(open(baseline_file))
    current = json.load(open(current_file))
except Exception as e:
    print(f"Error loading files: {e}")
    sys.exit(1)

baseline_pr = baseline.get("pass_rate", 0) * 100
current_pr = current.get("pass_rate", 0) * 100

print("")
print(f"Baseline pass rate:  {baseline_pr:.1f}%")
print(f"Current pass rate:   {current_pr:.1f}%")

threshold = 85.0
if current_pr >= threshold:
    print(f"\nPASS: {current_pr:.1f}% >= {threshold}% threshold")
    sys.exit(0)
else:
    print(f"\nFAIL: {current_pr:.1f}% < {threshold}% threshold")
    print("")
    print("Dimension comparison:")
    for dim in baseline.get("by_dimension", {}):
        b_avg = baseline["by_dimension"][dim].get("overall_avg", 0)
        c_avg = current.get("by_dimension", {}).get(dim, {}).get("overall_avg", 0)
        diff = c_avg - b_avg
        if diff < -0.5:
            status = "REGRESSION"
        elif diff < 0:
            status = "degraded"
        else:
            status = "OK"
        print(f"  {status} {dim}: {b_avg:.2f} -> {c_avg:.2f} ({diff:+.2f})")
    sys.exit(1)
PYEOF

TEST_RESULT=$?

echo ""
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}=== TEST PASSED ===${NC}"
else
    echo -e "${RED}=== TEST FAILED ===${NC}"
fi

exit $TEST_RESULT