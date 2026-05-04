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

FEATURE_NAME="${1:-}"

if [ -z "$FEATURE_NAME" ]; then
    echo -e "${RED}✗ Usage: ./scripts/create-feature.sh \"feature-name\"${NC}"
    echo ""
    echo "Example: ./scripts/create-feature.sh \"add-sanctions\""
    exit 1
fi

FEATURE_NAME=$(echo "$FEATURE_NAME" | sed 's/[^a-zA-Z0-9_-]/-/g' | tr '[:upper:]' '[:lower:]')
BRANCH_NAME="feature/$FEATURE_NAME"

echo -e "${BLUE}=== Create Feature Branch ===${NC}"
echo ""

CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD)
echo -e "Current branch: ${YELLOW}$CURRENT_BRANCH${NC}"

if [ "$CURRENT_BRANCH" != "master" ]; then
    echo -e "${RED}✗ You must be on 'master' branch to create a feature.${NC}"
    echo "  Current: $CURRENT_BRANCH"
    echo "  Run: git checkout master"
    exit 1
fi

echo ""
echo -e "${BLUE}1. Pulling latest from master...${NC}"
git pull origin master --quiet 2>/dev/null || echo -e "${YELLOW}⚠ Warning: Could not pull${NC}"

echo ""
echo -e "${BLUE}2. Creating branch: ${GREEN}$BRANCH_NAME${NC}"
git checkout -b "$BRANCH_NAME" 2>/dev/null || {
    echo -e "${RED}✗ Branch '$BRANCH_NAME' already exists.${NC}"
    exit 1
}

echo ""
echo -e "${BLUE}3. Running smoke test to verify system is stable...${NC}"
echo ""

if [ ! -f "/home/epmq/Desktop/Projects/shared-venv/bin/activate" ]; then
    echo -e "${RED}✗ Virtual environment not found${NC}"
    exit 1
fi

source /home/epmq/Desktop/Projects/shared-venv/bin/activate > /dev/null 2>&1

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

cd /home/epmq/Desktop/Projects/aegis-kg-unified

echo -e "${YELLOW}Running smoke test (1 task, ~1-2 min)...${NC}"
PYTHONPATH=. python3 aegis_eval/run_eval.py --tasks aegis_eval/task_bank.yaml --task list_all_regulations --trials 1 --verbose 2>&1 | tail -10

SMOKE_RESULT=$?

if [ $SMOKE_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Smoke test passed${NC}"
else
    echo -e "${RED}✗ Smoke test failed${NC}"
fi

echo ""
echo -e "${BLUE}=== Next Steps ===${NC}"
echo ""
echo -e "1. ${GREEN}Make your changes${NC} in the codebase"
echo -e "2. ${GREEN}Test your changes${NC}: ./scripts/test-quick.sh"
echo -e "3. ${GREEN}Commit your changes${NC}: git add . && git commit -m \"Add: description\""
echo -e "4. ${GREEN}Push your branch${NC}: git push origin $BRANCH_NAME"
echo -e "5. ${GREEN}Create Pull Request${NC} on GitHub"
echo ""
echo -e "${BLUE}Branch created: $BRANCH_NAME${NC}"
echo ""
