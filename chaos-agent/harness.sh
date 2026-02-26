#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# Self-Healing Chaos Agent — Agent Harness
#
# Runs Claude Code with the appropriate agent prompt (healer or reviewer).
# Inspired by Anthropic's "Building a C Compiler" article.
#
# Usage:
#   ./harness.sh healer              # Run healer agent once
#   ./harness.sh reviewer            # Run reviewer agent once
#   ./harness.sh healer --loop       # Run healer in continuous loop
# ══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

AGENT_ROLE="${1:-healer}"
LOOP_MODE="${2:-}"
MODEL="${CLAUDE_MODEL:-claude-sonnet-4-20250514}"

# Select prompt based on role
case "$AGENT_ROLE" in
    healer)
        PROMPT_FILE="$SCRIPT_DIR/HEALER_PROMPT.md"
        ;;
    reviewer)
        PROMPT_FILE="$SCRIPT_DIR/REVIEWER_PROMPT.md"
        ;;
    *)
        echo "Usage: $0 <healer|reviewer> [--loop]"
        echo ""
        echo "Options:"
        echo "  healer    Run the healer agent (reads failure report, patches code)"
        echo "  reviewer  Run the reviewer agent (reviews healer patches)"
        echo "  --loop    Run continuously (with 30s pause between iterations)"
        echo ""
        echo "Environment variables:"
        echo "  CLAUDE_MODEL  Model to use (default: claude-sonnet-4-20250514)"
        exit 1
        ;;
esac

if [[ ! -f "$PROMPT_FILE" ]]; then
    echo "ERROR: Prompt file not found: $PROMPT_FILE"
    exit 1
fi

# Create directories
mkdir -p "$REPO_DIR/agent_logs" "$REPO_DIR/current_tasks"

echo "═══════════════════════════════════════════════════════════"
echo "  Self-Healing Chaos Agent"
echo "═══════════════════════════════════════════════════════════"
echo "  Role:      $AGENT_ROLE"
echo "  Model:     $MODEL"
echo "  Prompt:    $PROMPT_FILE"
echo "  Repo:      $REPO_DIR"
echo "═══════════════════════════════════════════════════════════"

run_agent() {
    local iteration=$1
    local commit=$(git -C "$REPO_DIR" rev-parse --short=6 HEAD 2>/dev/null || echo "no-git")
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local logfile="$REPO_DIR/agent_logs/${AGENT_ROLE}_${timestamp}_${commit}.log"

    echo ""
    echo "[Iteration $iteration] Starting $AGENT_ROLE agent session..."
    echo "[Iteration $iteration] Commit: $commit"
    echo "[Iteration $iteration] Log: $logfile"
    echo ""

    # Pull latest changes if in a git repo
    if git -C "$REPO_DIR" rev-parse --git-dir > /dev/null 2>&1; then
        git -C "$REPO_DIR" pull --rebase origin main 2>/dev/null || true
    fi

    # Run Claude Code with the agent prompt
    # Using --dangerously-skip-permissions for autonomous operation
    cd "$REPO_DIR"
    claude --dangerously-skip-permissions \
           -p "$(cat "$PROMPT_FILE")" \
           --model "$MODEL" \
           2>&1 | tee "$logfile"

    echo ""
    echo "[Iteration $iteration] Session complete."
}

# ─── MAIN ─────────────────────────────────────────────────────────────────────

if [[ "$LOOP_MODE" == "--loop" ]]; then
    echo "Running in loop mode (Ctrl+C to stop)..."
    ITERATION=0
    while true; do
        ITERATION=$((ITERATION + 1))
        run_agent $ITERATION
        echo "[Loop] Sleeping 30s before next iteration..."
        sleep 30
    done
else
    run_agent 1
fi
