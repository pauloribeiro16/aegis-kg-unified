#!/bin/bash
# create-feature.sh — Create a new feature branch from master
#
# Usage:
#   ./scripts/create-feature.sh "add-sanctions"
#   ./scripts/create-feature.sh "fix-article-nulls"
#
# This script:
#   1. Verifies you are on the master branch
#   2. Pulls latest changes from master
#   3. Creates a new feature branch
#   4. Runs a quick smoke test to verify master is stable
#   5. Shows next steps

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get feature name from argument
FEATURE_NAME="${1:-}"

if [ -z "$FEATURE_NAME" ]; then
    echo -e "${RED}✗ Usage: ./scripts/create-feature.sh \"feature-name\"${NC}"
    echo ""
    echo "Example: ./scripts/create-feature.sh \"add-sanctions\""
    exit 1
fi

# Sanitize feature name (replace spaces with hyphens, remove special chars)
FEATURE_NAME=$(echo "$FEATURE_NAME" | sed 's/[^a-zA-Z0-9_-]/-/g' | tr '[:upper:]' '[:lower:]')
BRANCH_NAME="feature/$FEATURE_NAME"

echo -e "${BLUE}=== Create Feature Branch ===${NC}"
echo ""

# 1. Check current branch
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD)
echo -e "Current branch: ${YELLOW}$CURRENT_BRANCH${NC}"

if [ "$CURRENT_BRANCH" != "master" ]; then
    echo -e "${RED}✗ You must be on 'master' branch to create a feature.${NC}"
    echo "  Current: $CURRENT_BRANCH"
    echo "  Run: git checkout master"
    exit 1
fi

# 2. Pull latest from main
echo ""
echo -e "${BLUE}1. Pulling latest from master...${NC}"
git pull origin master --quiet 2>/dev/null || echo -e "${YELLOW}⚠ Warning: Could not pull (may be up to date or no remote)${NC}"

# 3. Create feature branch
echo ""
echo -e "${BLUE}2. Creating branch: ${GREEN}$BRANCH_NAME${NC}"
git checkout -b "$BRANCH_NAME" 2>/dev/null || {
    echo -e "${RED}✗ Branch '$BRANCH_NAME' already exists.${NC}"
    echo "  Run: git checkout $BRANCH_NAME"
    exit 1
}

# 4. Run smoke test to verify main is stable
echo ""
echo -e "${BLUE}3. Running smoke test to verify system is stable...${NC}"
echo ""

# Check if dependencies are in venv
if [ ! -f "/home/epmq/Desktop/Projects/shared-venv/bin/activate" ]; then
    echo -e "${RED}✗ Virtual environment not found at /home/epmq/Desktop/Projects/shared-venv/bin/activate${NC}"
    exit 1
fi

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

echo -e "${YELLOW}Running smoke test (1 task, ~1-2 min)...${NC}"
PYTHONPATH=. python3 aegis_eval/run_eval.py --tasks aegis_eval/task_bank.yaml --task list_all_regulations --trials 1 --verbose 2>&1 | tail -20

SMOKE_RESULT=$?

if [ $SMOKE_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Smoke test passed${NC}"
else
    echo -e "${RED}✗ Smoke test failed — system may not be stable${NC}"
    echo ""
    echo -e "${YELLOW}Note: You can still continue, but verify the system before merging.${NC}"
fi

# 5. Show commit template
echo ""
echo -e "${BLUE}=== Next Steps ===${NC}"
echo ""
echo -e "1. ${GREEN}Make your changes${NC} in the codebase"
echo ""
echo -e "2. ${GREEN}Test your changes${NC}:"
echo "   ./scripts/test-quick.sh"
echo ""
echo -e "3. ${GREEN}Commit your changes${NC}:"
echo "   git add ."
echo "   git commit -m \"Add: description of what you did\""
echo ""
echo -e "4. ${GREEN}Push your branch${NC}:"
echo "   git push origin $BRANCH_NAME"
echo ""
echo -e "5. ${GREEN}Create Pull Request${NC} on GitHub"
echo "   - GitHub Actions will run tests automatically"
echo "   - If tests pass, I will notify you"
echo "   - Review the changes and approve the merge"
echo ""
echo -e "${BLUE}Branch created: $BRANCH_NAME${NC}"
echo ""
