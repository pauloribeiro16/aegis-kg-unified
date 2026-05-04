#!/bin/bash
# test-quick.sh — Quick regression test (5 tasks, ~5 min)
#
# Usage:
#   ./scripts/test-quick.sh
#
# This script:
#   1. Verifies system health (Neo4j, Ollama)
#   2. Runs 5 representative tasks
#   3. Compares results with baseline_stable_v1.json
#   4. Reports pass/fail with detailed analysis
#
# This verifies that the current codebase is stable against the master baseline.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Colors for JSON output (if jq available)
has_jq() {
    command -v jq &> /dev/null
}

echo -e "${BLUE}=== AEGIS Quick Test (~5 min) ===${NC}"
echo ""

# 1. Check dependencies
echo -e "${BLUE}1. Checking system health...${NC}"

# Neo4j
if curl -s -u neo4j:d3fendtest http://localhost:7474/db/neo4j/tx/commit -H "Content-Type: application/json" -d '{"statements":[{"statement":"RETURN 1"}]' > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} Neo4j"
else
    echo -e "   ${RED}✗${NC} Neo4j not accessible"
    exit 1
fi

# Ollama
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓${NC} Ollama"
else
    echo -e "   ${RED}✗${NC} Ollama not accessible"
    exit 1
fi

# 2. Run eval
echo ""
echo -e "${BLUE}2. Running evaluation (5 tasks, ~5 min)...${NC}"

source /home/epmq/Desktop/Projects/shared-venv/bin/activate > /dev/null 2>&1

export NEO4J_URI=http://localhost:7474
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=d3fendtest
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=ministral-3:latest
export LANGFUSE_PUBLIC_KEY=pk-lf-ea927dac-58fd-48f5-b98e-1eaf0aeab892
export LANGFUSE_SECRET_KEY=sk-lf-5b2e0db7-d911-444f-9971-3f5699147ac7
export LANGFUSE_BASE_URL=http://localhost:3000
export MINIMAX_API_KEY=sk-cp-yta9jJd1FoaX91wTwoVjoICfZm-wjFqKLccscXuVCdHp8huqOLAY_T6yScB3eO35cfxqBzXvlMYXfxQcPCOlDeBhkyTrMxGGwgv6UdICKK93Xi-_6dHubz4

cd /home/epmq/Desktop/Projects/aegis-kg-unified

# Create temp task list with 5 representative tasks
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

# 3. Extract results
echo ""
echo -e "${BLUE}3. Analyzing results...${NC}"

RESULT_FILE=$(ls -t aegis_eval/results/summary_*.json 2>/dev/null | head -1)

if [ -z "$RESULT_FILE" ] || [ ! -f "$RESULT_FILE" ]; then
    echo -e "${RED}✗ No result file found${NC}"
    exit 1
fi

# Compare with baseline
python3 << EOF
import json
import sys

baseline_file = "aegis_eval/results/baseline_stable_v1.json"
current_file = "$RESULT_FILE"

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
    print(f"\n{GREEN}✓ PASS: {current_pr:.1f}% >= {threshold}% threshold{NC}")
    sys.exit(0)
else:
    print(f"\n{RED}✗ FAIL: {current_pr:.1f}% < {threshold}% threshold{NC}")
    print("")
    print("Dimension comparison:")
    for dim in baseline.get("by_dimension", {}):
        b_avg = baseline["by_dimension"][dim].get("overall_avg", 0)
        c_avg = current.get("by_dimension", {}).get(dim, {}).get("overall_avg", 0)
        diff = c_avg - b_avg
        if diff < -0.5:
            status = "❌"
        elif diff < 0:
            status = "⚠️ "
        else:
            status = "✅"
        print(f"  {status} {dim}: {b_avg:.2f} → {c_avg:.2f} ({diff:+.2f})")
    sys.exit(1)
EOF

TEST_RESULT=$?

# Summary
echo ""
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}=== TEST PASSED ===${NC}"
    echo "System is stable. You can proceed with your changes or create a Pull Request."
else
    echo -e "${RED}=== TEST FAILED ===${NC}"
    echo "There may be a regression. Review the analysis above."
    echo ""
    echo "If you just made changes:"
    echo "  1. Review what you changed"
    echo "  2. If unrelated to your changes, it may be infrastructure"
    echo "  3. If caused by your changes, revert or fix"
fi

exit $TEST_RESULT
