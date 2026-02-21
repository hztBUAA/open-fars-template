#!/bin/bash
# Stop hook — perpetual driver core
# When driver is active, blocks stop to keep Claude working.
# Three-layer protection against compact deadloops:
#   1. stop_hook_active check (already blocked once → let go)
#   2. External counter (>10 consecutive blocks → let go)
#   3. Post-compact SessionStart hook re-injects driver context
INPUT=$(cat)

# --- Check if driver is activated ---
DRIVER_STATE="$CLAUDE_PROJECT_DIR/.open-fars/meta/driver-state.yaml"
if [ ! -f "$DRIVER_STATE" ]; then
  exit 0
fi
ACTIVE=$(grep "^active:" "$DRIVER_STATE" | awk '{print $2}')
if [ "$ACTIVE" != "true" ]; then
  exit 0
fi

# --- Protection 1: stop_hook_active check ---
# Compact resets this, so this only guards non-compact consecutive blocks
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
  # Already blocked once, let go (post-compact SessionStart will restore driver)
  exit 0
fi

# --- Protection 2: External counter ---
BLOCK_COUNT_FILE="$CLAUDE_PROJECT_DIR/.open-fars/meta/.driver-block-count"
COUNT=0
if [ -f "$BLOCK_COUNT_FILE" ]; then
  COUNT=$(cat "$BLOCK_COUNT_FILE" 2>/dev/null || echo "0")
fi
COUNT=$((COUNT + 1))
echo "$COUNT" > "$BLOCK_COUNT_FILE"
if [ "$COUNT" -gt 10 ]; then
  # Fallback: 10 consecutive blocks, force let go
  echo "0" > "$BLOCK_COUNT_FILE"
  exit 0
fi

# --- Check if awaiting human decision ---
AWAITING=$(grep "^awaiting_human:" "$DRIVER_STATE" | awk '{print $2}')
if [ "$AWAITING" = "true" ]; then
  exit 0
fi

# --- All checks passed: block stop, continue driving ---
jq -n '{
  "decision": "block",
  "reason": "DRIVER MODE ACTIVE. Read .open-fars/meta/registry.yaml and .open-fars/meta/driver-state.yaml, then execute the next priority action per the /drive skill driver decision logic. After completing the action, update driver-state.yaml with last_action and last_action_time."
}'
