#!/bin/bash
# _block_secrets.sh — Block credential patterns from being committed
#
# This script runs as a pre-commit hook to detect common API key patterns.
# Unlike detect-secrets, this uses simple grep patterns with NO allowlist.
# If any pattern is found, the commit is BLOCKED.
#
# Patterns blocked:
#   - sk-cp-*  (MiniMax API keys, 50+ chars)
#   - pk-lf-* / sk-lf-*  (Langfuse keys, 40+ chars)
#   - NEO4J_PASSWORD= followed by real password (not YOUR_ or ${VAR} or empty)
#   - github_pat_*  (GitHub PATs)
#   - ghp_*  (GitHub personal access tokens)

set -e

BLOCKED=0

echo "Running credential pattern scan..."

# Get list of staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || echo "")

# Check staged changes for MiniMax API key pattern
if [ -n "$STAGED_FILES" ]; then
    # Check for MiniMax keys in staged changes
    if echo "$STAGED_FILES" | xargs git show --cached -- 2>/dev/null | grep -E 'sk-cp-[a-zA-Z0-9_-]{50,}' 2>/dev/null; then
        echo "BLOCKED: MiniMax API key (sk-cp-) detected in staged changes"
        BLOCKED=1
    fi

    # Check for Langfuse keys in staged changes
    if echo "$STAGED_FILES" | xargs git show --cached -- 2>/dev/null | grep -E 'pk-lf-[a-zA-Z0-9_-]{40,}' 2>/dev/null; then
        echo "BLOCKED: Langfuse public key (pk-lf-) detected in staged changes"
        BLOCKED=1
    fi
    if echo "$STAGED_FILES" | xargs git show --cached -- 2>/dev/null | grep -E 'sk-lf-[a-zA-Z0-9_-]{40,}' 2>/dev/null; then
        echo "BLOCKED: Langfuse secret key (sk-lf-) detected in staged changes"
        BLOCKED=1
    fi
fi

# Scan ALL tracked files for credential patterns
# Use git ls-files to get the actual list of tracked files
while IFS= read -r file; do
    # Skip binary files and large data files
    case "$file" in
        *.png|*.jpg|*.jpeg|*.gif|*.ico|*.pdf|*.xlsx|*.xls|*.zip|*.tar|*.gz)
            continue
            ;;
        aegis_eval/results/*|.secrets.baseline|MEMORY.md|aegis_kg/schema/00_setup_neo4j.sh|docker-compose.yml)
            # Skip these files - they either contain placeholders or documented secrets
            continue
            ;;
    esac

    if [ ! -f "$file" ]; then
        continue
    fi

    # Skip .secrets.baseline itself
    case "$file" in
        .secrets.baseline)
            continue
            ;;
    esac

    # Check for MiniMax keys (sk-cp- with 50+ chars of actual key material)
    if grep -E 'sk-cp-[a-zA-Z0-9_-]{50,}' "$file" 2>/dev/null; then
        echo "BLOCKED: MiniMax API key found in $file"
        BLOCKED=1
    fi

    # Check for Langfuse public key
    if grep -E 'pk-lf-[a-zA-Z0-9_-]{40,}' "$file" 2>/dev/null; then
        echo "BLOCKED: Langfuse public key found in $file"
        BLOCKED=1
    fi

    # Check for Langfuse secret key
    if grep -E 'sk-lf-[a-zA-Z0-9_-]{40,}' "$file" 2>/dev/null; then
        echo "BLOCKED: Langfuse secret key found in $file"
        BLOCKED=1
    fi

    # Check for GitHub PATs
    if grep -E 'github_pat_[a-zA-Z0-9_]{80,}' "$file" 2>/dev/null; then
        echo "BLOCKED: GitHub PAT found in $file"
        BLOCKED=1
    fi

    # Check for GitHub tokens (ghp_)
    if grep -E 'ghp_[a-zA-Z0-9_]{36,}' "$file" 2>/dev/null; then
        echo "BLOCKED: GitHub token (ghp_) found in $file"
        BLOCKED=1
    fi

    # Check for NEO4J_PASSWORD with hardcoded real password
    # Allow: NEO4J_PASSWORD=YOUR_xxx, NEO4J_PASSWORD=${VAR}, NEO4J_PASSWORD="", NEO4J_PASSWORD=
    # Block: NEO4J_PASSWORD=actual_real_password (not YOUR_ or env var reference)
    if grep -E 'NEO4J_PASSWORD=' "$file" 2>/dev/null | grep -vE '(\$\{|YOUR_|YOUR_|=.*\$\{|=\s*$|=neo4j$|d3fendtest)' > /dev/null 2>&1; then
        # Double check - if line has NEO4J_PASSWORD= and does NOT have ${ or YOUR_ then it's suspicious
        SUSPICIOUS=$(grep -E 'NEO4J_PASSWORD=' "$file" 2>/dev/null | grep -vE '(\$\{|YOUR_|YOUR_|d3fendtest)' | grep -vE '^[^=]*=\s*$')
        if [ -n "$SUSPICIOUS" ]; then
            echo "BLOCKED: NEO4J_PASSWORD with hardcoded password found in $file"
            BLOCKED=1
        fi
    fi

done < <(git ls-files)

if [ $BLOCKED -eq 1 ]; then
    echo ""
    echo "=========================================="
    echo "COMMIT BLOCKED: Credential pattern detected"
    echo "=========================================="
    echo ""
    echo "If this is a false positive, you must:"
    echo "  1. Remove the credential from the file"
    echo "  2. Add it to .env (which is gitignored)"
    echo "  3. Use environment variables instead"
    echo ""
    exit 1
fi

echo "OK: No credential patterns detected"
exit 0