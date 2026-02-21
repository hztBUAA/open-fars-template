---
name: drive
description: Perpetual project driver — automatically advances the Open-FARS pipeline until completion or human decision needed. Use /drive to start, /drive off to stop, /drive status to check.
user_invocable: true
---

# Open-FARS Perpetual Driver (`/drive`)

## Overview

The driver keeps Claude working non-stop on the Open-FARS pipeline. Once activated, Claude never stops — it reads pipeline state, determines the next action, executes it, and repeats. The Stop hook blocks session exit so the loop continues.

Driving stops only when:
- User runs `/drive off`
- All stages complete (S7 done)
- A human decision point is reached (email sent, then pause)

## Usage

```
/drive              # Activate driver (same as /drive on)
/drive on           # Activate driver
/drive off          # Deactivate driver
/drive status       # Show current driver state
```

## Activation (`/drive` or `/drive on`)

1. Create/update `.open-fars/meta/driver-state.yaml`:
   ```yaml
   active: true
   awaiting_human: false
   awaiting_reason: ""
   last_action: ""
   last_action_time: ""
   total_actions: 0
   history: []
   ```
2. Reset block counter: `echo "0" > .open-fars/meta/.driver-block-count`
3. Read `.open-fars/meta/registry.yaml`
4. Execute the first priority action (see Driver Decision Logic below)
5. After action completes, update `driver-state.yaml`:
   - Set `last_action` to a brief description
   - Set `last_action_time` to current Beijing timestamp
   - Increment `total_actions`
   - Append to `history` (keep last 20 entries)

## Deactivation (`/drive off`)

1. Update `driver-state.yaml`: set `active: false`
2. Remove block counter file: `.open-fars/meta/.driver-block-count`
3. Run `/status` skill to generate a final progress report
4. Send email notification via `email-notify`:
   - Subject: `[Claude Code] Driver deactivated — progress report`
   - Body: status report summary

## Status Check (`/drive status`)

Read and display:
1. `driver-state.yaml` — active state, last action, total actions
2. Recent history entries
3. Current block counter value
4. Registry pipeline state summary

## Driver Decision Logic

After each action, determine the next one. Priority from highest to lowest:

### P1: Human Decision Points

Check if any stage requires human input:
- S2 PASS but no idea chosen → send reminder email, set `awaiting_human: true`, `awaiting_reason: "Waiting for idea selection (S2)"`
- S3 PASS but no user confirmation → send reminder email, set `awaiting_human: true`, `awaiting_reason: "Waiting for plan confirmation (S3)"`
- Any stage with `awaiting_human: true` in driver state → do nothing, let Stop hook release

### P2: Failed Reviews Needing Re-run

Find stages where the latest review verdict is FAIL and review count < threshold:
- Re-run the corresponding subagent with judge feedback
- After subagent returns, auto-trigger `/review` (judge review)
- Thresholds: S1/S2/S3 = 3, S4/S5/S6/S7 = 5

If review count >= threshold → send escalation email, set `awaiting_human: true`

### P3: Completed Stage Without Review

Find stages with status `completed` but no review (or no PASS review):
- Auto-trigger `/review` for that stage

### P4: PASS Review — Advance to Next Stage

Find the latest stage that has a PASS review and whose next stage is still `pending`:
- Follow the per-stage rules in AGENTS.md:
  - S1 PASS → auto-advance to S2 (spawn ideation)
  - S2 PASS → email user for idea selection, set awaiting_human
  - S3 PASS → email user for plan confirmation, set awaiting_human
  - S4 PASS → auto-advance to S5 (spawn experiment)
  - S5 PASS → auto-advance to S6 (spawn writing)
  - S6 PASS → send notification email, auto-advance to S7
  - S7 done → send final email, set `active: false`
- Update registry stage status to `in_progress`
- Spawn the corresponding subagent

### P5: Monitor Running Experiments

If S5 is `in_progress`:
- Check tmux sessions for running experiments
- Check experiment output directories for new results
- If experiments complete, collect results and mark stage `completed`

### P6: Periodic Maintenance

- If no `/status` report in last 6 hours → run `/status`
- If no `/catchup` document in last 24 hours → run `/catchup`
- If degradations exist and no recent audit → run `/review audit`

### P7: Nothing To Do

If no action matches:
- Generate a brief summary of current state
- Set `active: false`
- Send email: `[Claude Code] Driver completed — no more actions available`

## State File Schema

`driver-state.yaml`:
```yaml
active: true                              # Whether driver is active
awaiting_human: false                     # Whether paused for human decision
awaiting_reason: ""                       # Why we're waiting
last_action: "Spawned S4 assets agent"    # Last completed action
last_action_time: "2026-02-21T14:30+08:00" # Beijing time
total_actions: 12                         # Cumulative action count
history:                                  # Last 20 actions
  - time: "2026-02-21T14:30+08:00"
    action: "Spawned S4 assets agent"
  - time: "2026-02-21T14:15+08:00"
    action: "S3 plan review PASS"
```

## How the Stop Hook Works

The Stop hook (`driver-stop.sh`) is the engine:

```
Normal cycle: Stop → block → Claude continues → Stop → block → ...
Compact:      Stop → let go → compact → SessionStart(compact) injects driver context
              → Claude continues → Stop → block → normal cycle resumes
```

Three-layer deadloop protection:
1. `stop_hook_active` check — if already blocked once, let go
2. External file counter — >10 consecutive blocks, force let go
3. Post-compact SessionStart hook resets counter and re-injects driver context

## Important Notes

- The driver follows AGENTS.md orchestration protocol for all stage transitions
- All email notifications use the `email-notify` skill
- Registry.yaml is the source of truth for pipeline state
- Driver state is separate from registry — it only tracks the driving mechanism
- When `awaiting_human` is true, the Stop hook lets Claude exit normally
- User can always `/drive off` to stop, or `/drive on` to resume after providing input
