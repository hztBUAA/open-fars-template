#!/bin/bash
# SessionStart(compact) hook — restore driver context after compact
# Compact is a normal relay station, not a deadloop trigger.
DRIVER_STATE="$CLAUDE_PROJECT_DIR/.open-fars/meta/driver-state.yaml"
if [ ! -f "$DRIVER_STATE" ]; then
  exit 0
fi
ACTIVE=$(grep "^active:" "$DRIVER_STATE" | awk '{print $2}')
if [ "$ACTIVE" != "true" ]; then
  exit 0
fi

# Reset block counter (compact is normal relay, not deadloop)
BLOCK_COUNT_FILE="$CLAUDE_PROJECT_DIR/.open-fars/meta/.driver-block-count"
echo "0" > "$BLOCK_COUNT_FILE"

# Inject context (stdout is added to Claude's context)
echo "=== DRIVER MODE ACTIVE ==="
echo "Context was compacted. Driver mode is still active."
echo ""
echo "Current driver state:"
cat "$DRIVER_STATE"
echo ""
echo "IMPORTANT: Continue executing the /drive skill driver decision logic."
echo "Read .open-fars/meta/registry.yaml to determine next action."
exit 0
