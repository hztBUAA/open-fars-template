# Open-FARS Agents & Skills

## Architecture

Claude Code subagents **cannot nest-spawn other subagents** (official limitation). Therefore:

- **Main thread Claude acts as orchestrator** (coordinator role)
- Main thread follows the orchestration protocol in this file to **autonomously drive** the entire pipeline
- Skills (`/review`, `/status`, `/catchup`) execute in main thread context
- Each `open-fars-*` agent is spawned by main thread as needed
- **Automation first**: except at explicitly marked decision points, all transitions, reviews, and fixes are handled autonomously

---

## Pipeline Orchestration Protocol (main thread follows)

### Stage Flow Overview

| Stage | Subagent | Prerequisite | Key Output | Auto Review | Email Trigger |
|-------|----------|-------------|---------|---------|------------|
| S1 | `open-fars-survey` | Direction set | survey/, papers/, gaps.md | Yes | -- |
| S2 | `open-fars-ideation` | S1 PASS | ideation/, ideas/ | Yes | **PASS -> email user to pick idea** |
| S3 | `open-fars-plan` | S2 PASS + idea chosen | plan/LATEST.md | Yes | **PASS -> email user to confirm plan** |
| S4 | `open-fars-assets` | S3 PASS + user confirmed | code/, tests | Yes | review >=5 -> email |
| S5 | `open-fars-experiment` | S4 PASS | experiments/, figures | Yes | review >=5 -> email |
| S6 | `open-fars-writing` | S5 PASS | paper/ | Yes | PASS or >=5 -> email |
| S7 | `open-fars-revision` | S6 PASS | revised paper | Yes | **Done -> email** |

### Core Orchestration Loop

Each stage follows this automated loop:

```
1. Update registry: stages.S{N} -> "in_progress"
2. Spawn corresponding subagent to execute stage work
3. Agent returns: auto-spawn judge agent for review
4. Judge returns result:
   PASS -> Check if decision point (see below)
           Yes -> send email, pause for user
           No  -> update registry, auto-advance to next stage
   FAIL -> review_count += 1
           count < threshold -> pass judge feedback to agent, re-run stage
           count >= threshold -> send email to escalate, pause for user
```

### Auto Review Rules

**Main thread MUST auto-trigger judge agent after each stage completes. No need to wait for manual `/review`.**

Flow:
1. Subagent finishes -> main thread immediately spawns `open-fars-judge` agent
2. Judge returns verdict (PASS/FAIL) + feedback
3. Persist review to `reviews/` and update registry.yaml
4. Decide next step based on verdict (see per-stage rules below)

### Per-Stage Rules

#### S1 Literature Survey

- **Auto review** -> PASS -> auto-advance to S2
- **Auto review** -> FAIL -> re-run survey agent with feedback
- **FAIL threshold**: 3 -> email escalation

#### S2 Idea Generation

- **Auto review** -> PASS -> **Send email**
  - Email content: ideas list, score ranking, judge comments, recommended choice
  - Subject: `[Claude Code] Open-FARS ideas ready, please choose`
  - **Pause for user reply** (user specifies idea number via chat)
- **Auto review** -> FAIL -> re-run ideation agent with feedback
- **FAIL threshold**: 3 -> email escalation

#### S3 Research Plan

- Prerequisite: user has chosen idea
- **Auto review** -> PASS -> **Send email**
  - Email content: plan summary (RQs, hypotheses, experiment design, baselines), judge comments
  - Subject: `[Claude Code] Open-FARS research plan ready, please confirm`
  - **Pause for user confirmation** (user replies to confirm or request changes)
- **Auto review** -> FAIL -> re-run plan agent with feedback
- **FAIL threshold**: 3 -> email escalation

#### S4 Code Implementation

- Prerequisite: user confirmed plan
- **Auto review** -> PASS -> auto-advance to S5
- **Auto review** -> FAIL -> re-run assets agent with feedback
- **FAIL threshold**: 5 -> email escalation
  - Subject: `[Claude Code] ESCALATION: code review failed 5 times`
  - Content: 5 rounds of judge feedback summary, core blockers, attempted fixes

#### S4+S5 Joint Stage (Experiment Execution)

S4 and S5 need tight coordination. Experiment issues may require going back to fix code:

- **Issue during experiments** -> auto-spawn judge for advice -> attempt fix
- **Self-resolvable** (code bug, config error, param tuning) -> fix and continue
- **Degradation** -> record in registry.yaml `degradations`, continue
- **Unresolvable** (model download failure, dataset unavailable, GPU shortage, API down) -> try judge-suggested fix first
- **S4+S5 cumulative reviews >= 5** -> **Send email**
  - Subject: `[Claude Code] ESCALATION: experiment stage needs human intervention`
  - Content: issue list, degradation log, judge suggestions, attempted solutions

#### S6 Paper Writing

- **Auto review** -> PASS -> **Send email notification**
  - Subject: `[Claude Code] paper draft complete, Judge passed`
  - Content: judge score, paper abstract, key findings
  - **Auto-advance to S7** (no wait for user reply)
- **Auto review** -> FAIL -> re-run writing agent with feedback
- **FAIL threshold**: 5 -> **Send email**
  - Subject: `[Claude Code] ESCALATION: paper review failed 5 times`
  - Pause for user intervention

#### S7 Simulated Review & Revision

S7 is driven by main thread, simulating a full academic review process:

1. Spawn `open-fars-judge` in **simulated reviewer** mode
   - Judge outputs formatted review opinions (simulating N reviewers + AC opinion)
2. Pass review opinions to `open-fars-revision` agent for revision
3. After revision agent completes, spawn judge again to review revised version
4. Repeat until judge deems paper quality sufficient
5. Done -> **Send email notification**
   - Subject: `[Claude Code] Open-FARS final paper ready`
   - Content: final score, revision rounds summary, paper PDF path

---

### Email Notification Summary

| Trigger | Email Type | User Action | Main Thread Behavior |
|---------|---------|--------------|-----------|
| S2 PASS | Decision request | Choose idea number | **Pause** |
| S3 PASS | Decision request | Confirm plan or request changes | **Pause** |
| S4+S5 review >= 5 | Escalation alert | Investigate | **Pause** |
| Degradation/infra review >= 5 | Escalation alert | Investigate | **Pause** |
| S6 PASS | Progress notification | No action needed | **Auto-advance S7** |
| S6 FAIL >= 5 | Escalation alert | Investigate | **Pause** |
| S7 complete | Final notification | Review paper, decide submission | **Pipeline ends** |

### Email Format

All emails sent via `email-notify` skill:

```
python3 .claude/skills/email-notify/send-email.py \
  --subject "[Claude Code] {type}: {summary}" \
  --body-file {persisted report file path}
```

Email body structure:
```
[Project] {paper_title}
[Stage] S{N} {stage_name}
[Status] {PASS/FAIL/ESCALATION}

[Summary]
- {key info 1}
- {key info 2}

[Details]
{Judge comments / issue list / degradation log}

[Action Required]
{specific action items, or "no action needed"}

[File Locations]
{relevant output file paths}
```

---

### State Management

Main thread during orchestration must:
1. Read `.open-fars/meta/registry.yaml` for current state
2. Update registry.yaml after each stage change
3. Persist each judge review to `reviews/` and update registry
4. **Maintain per-stage review counters** for email escalation threshold checks

**Registry schema, directory structure, naming conventions, read/write protocols** are all defined in `.claude/SPEC.md` as the single source of truth.

---

## Subagents (in `.claude/agents/`)

Spawned by main thread to execute specific stage work:

| Agent | File | Purpose |
|-------|------|------|
| `open-fars-survey` | `open-fars-survey.md` | S1 Literature survey + citation network + gap analysis |
| `open-fars-ideation` | `open-fars-ideation.md` | S2 Generate research ideas from gaps and score them |
| `open-fars-plan` | `open-fars-plan.md` | S3 Experiment design: RQs, hypotheses, baselines, task graph |
| `open-fars-assets` | `open-fars-assets.md` | S4 Implement method, baselines, evaluation code |
| `open-fars-experiment` | `open-fars-experiment.md` | S5 Execute experiments, statistical analysis, generate figures |
| `open-fars-writing` | `open-fars-writing.md` | S6 Write complete LaTeX paper |
| `open-fars-revision` | `open-fars-revision.md` | S7 Revise paper based on review feedback |
| `open-fars-judge` | `open-fars-judge.md` | Quality review (read-only), review + simulated peer review modes |

Note: `open-fars-coordinator` is **no longer a subagent**; its orchestration logic is executed by main thread following this file.

## Skills (in `.claude/skills/`)

User commands executed in main thread context:

| Command | Directory | Purpose | Persistence |
|------|------|------|--------|
| `/review` | `review/` | Manually trigger judge review (not needed during auto-orchestration) | `reviews/` |
| `/status` | `status/` | Generate project progress report | `status/` |
| `/catchup` | `catchup/` | Research onboarding document | `catchup/` |
| `/email-notify` | `email-notify/` | Send structured notification email | -- |
| `/drive` | `drive/` | Perpetual project driver — auto-advances pipeline until completion or human decision | `driver-state.yaml` |

## Data Persistence

Detailed directory structure and file naming conventions in `.claude/SPEC.md`.

Overview:
```
.open-fars/
  meta/registry.yaml          # Main index (schema in SPEC.md)
  survey/{direction}/          # S1 Literature survey
  ideation/{direction}/        # S2 Idea generation
  plan/{direction}/{project}/  # S3 Research plan
  projects/{project}/
    code/                      # S4 Code implementation
    experiments/               # S5 Experiment results
    paper/                     # S6 Paper
    reviews/                   # S7 Review records + judge reviews
    status/                    # Progress reports
    catchup/                   # Onboarding documents
```

Timestamps use Beijing time: `TZ=Asia/Shanghai date +"%Y-%m-%d_%H%M"`
