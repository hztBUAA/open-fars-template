#!/bin/bash
# PreCompact hook — reset block counter before compact
# Prevents counter accumulation across compact boundaries.
BLOCK_COUNT_FILE="$CLAUDE_PROJECT_DIR/.open-fars/meta/.driver-block-count"
echo "0" > "$BLOCK_COUNT_FILE" 2>/dev/null
exit 0
