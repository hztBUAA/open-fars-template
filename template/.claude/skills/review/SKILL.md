---
name: review
description: Run a quality review (Judge agent) on the current Open-FARS project. Auto-detects what to review based on pipeline state — no arguments needed.
user_invocable: true
---

# Open-FARS Review (Judge)

## Overview

Trigger the `open-fars-judge` agent to perform a quality review. **Intelligently detects what to review** based on the current pipeline state — you usually just type `/review` and it figures out the rest.

## Usage

```
/review                           # Auto-detect target, no extra context
/review paper                     # Force paper review
/review stage S5                  # Force specific stage review
/review audit                     # Force plan-vs-actual audit
/review 实验的 H2 假设结果怎么样     # Auto-detect + user focus query
/review paper 关注 tautology 数据一致性  # Force paper review + user focus
```

Any text beyond the mode keyword (`paper`/`stage S{N}`/`audit`) is treated as a **user focus query** — an additional area of emphasis the judge should pay special attention to during the review. This query is appended to the judge prompt.

### Parsing rules for arguments

1. Extract mode keyword from the beginning (if present): `paper`, `stage S{N}`, `audit`
2. Everything remaining after the mode keyword is the **user focus query**
3. If no mode keyword is found, the entire argument string is the user focus query (auto-detect mode applies)

Examples:
- `/review` → auto-detect, no focus
- `/review paper` → paper review, no focus
- `/review 实验降级` → auto-detect + focus on "实验降级"
- `/review stage S5 关注 H2 假设检验的 p 值` → S5 stage review + focus on "关注 H2 假设检验的 p 值"
- `/review audit 重点看 eval 样本量和 prompt 方法` → audit + focus on "重点看 eval 样本量和 prompt 方法"

## Workflow

### Step 1: Read pipeline state

Read `.open-fars/meta/registry.yaml` to get:
- Active project and direction
- Each stage's status (`pending` / `in_progress` / `completed`)
- Prior reviews (paths, types, rounds, verdicts)
- Known degradations

### Step 2: Auto-detect review target (when no explicit argument)

Apply these rules **in order** — the first match wins:

```
Priority 1: Un-reviewed completed stage
  - Find the LATEST stage whose status == "completed"
    that has NO prior "stage_review" with verdict "PASS" in reviews list.
  - → Stage Review for that stage.
  - Rationale: a completed stage without a passing review is the most urgent gate.

Priority 2: In-progress stage with new results since last review
  - If a stage is "in_progress" AND there exists a prior review for it,
    check if experiment results have been updated since that review's date.
    (Compare file modification times in the stage's output directory against review date.)
  - If newer results exist → Stage Review (re-review) for that stage.
  - Rationale: new data means the prior review may be stale.

Priority 3: Paper exists and has unresolved review
  - If S6_writing status is "in_progress" or "completed"
    AND paper/main.tex exists
    AND (no prior paper_review exists, OR the last paper_review verdict was "FAIL")
  - → Paper Review.
  - Rationale: paper with no review or failed review needs attention.

Priority 4: Degradations exist but no recent audit
  - If registry.yaml has a non-empty `degradations` list
    AND (no prior audit exists, OR last audit is > 24h old)
  - → Audit.
  - Rationale: tracked degradations should be periodically re-audited.

Priority 5: Fallback — review the furthest-along stage
  - Pick the highest-numbered stage that is "in_progress" or "completed".
  - If it's S6/S7 → Paper Review.
  - Otherwise → Stage Review for that stage.
```

After determining the target, **tell the user what you decided and why** before launching the judge. Example:

> 检测到 S5 实验阶段已有新结果（e1_landscape 5个task完成），但上次评审是 2 小时前。
> 将执行 **S5 Stage Review (Round 2)**。

### Step 3: Find the project

From `registry.yaml`, identify the active project. If multiple projects exist, use the one with `status: "experimenting"` or the most recently updated.

### Step 4: Determine round number

Count existing reviews of the same type in `reviews/`:
```bash
ls .open-fars/projects/{project}/reviews/ | grep "judge_{type}" | wc -l
```
Round = count + 1.

### Step 5: Launch the judge agent

Use the Task tool to launch `open-fars-judge` with the appropriate prompt:

**Paper Review**:
```
Review the paper at .open-fars/projects/{project}/paper/main.tex using Paper Review mode.
This is round {N}. {If N > 1: Read prior reviews at reviews/ and verify Required Fixes from round {N-1} are addressed.}
Project: {project-slug}
Target venue: {target_venue from registry}
Working directory: {cwd}
{If user_focus_query: "\n\nADDITIONAL FOCUS: The user specifically wants you to pay attention to: {user_focus_query}. Make sure your review addresses this area in detail."}
```

**Stage Review**:
```
Review stage S{X} ({stage_name}) output for project {project-slug} using Stage Review mode.
This is round {N}. {If N > 1: Read prior review and check fixes.}
Stage output directory: .open-fars/projects/{project}/{stage_dir}/
Plan file: .open-fars/plan/{direction}/{project}/LATEST.md
Working directory: {cwd}
Check for degradations from plan: {list degradations from registry if any}
{If user_focus_query: "\n\nADDITIONAL FOCUS: The user specifically wants you to pay attention to: {user_focus_query}. Make sure your review addresses this area in detail."}
```

**Audit**:
```
Compare the research plan at .open-fars/plan/{direction}/{project}/LATEST.md against actual execution.
Working directory: {cwd}
Check: experiments actually run, models used, sample sizes, methods implemented, ablations completed.
Prior degradations on record: {list from registry}
Document all degradations with severity ratings (critical/medium/minor).
{If user_focus_query: "\n\nADDITIONAL FOCUS: The user specifically wants you to pay attention to: {user_focus_query}. Make sure your review addresses this area in detail."}
```

### Step 6: Persist the review

After the judge agent returns:

1. Generate timestamp: `TZ=Asia/Shanghai date +"%Y-%m-%d_%H%M"`
2. Save to: `.open-fars/projects/{project}/reviews/{timestamp}_judge_{type}_r{round}.md`
3. Update `registry.yaml` reviews list:
   ```yaml
   - path: "reviews/{timestamp}_judge_{type}_r{round}.md"
     type: "{paper_review|stage_review|audit}"
     round: N
     verdict: "{PASS|FAIL}"
     score: X.X
     date: "YYYY-MM-DDTHH:MM+08:00"
   ```
4. If audit found new degradations, update `degradations` section in registry.

### Step 7: Escalation check

- If this is the **3rd consecutive FAIL** for the same stage/type, send email via `email-notify`:
  ```
  Subject: [Claude Code] ESCALATION: {stage} failed review 3 times
  Body: <review summary + required fixes>
  ```

### Step 8: Report to user

Print a concise summary:

```
## Review Complete: {type} Round {N}

Target: {what was reviewed}
Verdict: {PASS|FAIL}
Score: {X.X}/10 (paper) or {X.X}/5 (stage)
File: reviews/{filename}

### Top Issues
1. ...
2. ...

### Required Fixes (if FAIL)
1. ...
2. ...

### Suggested Next Action
{e.g., "Fix issues and run /review again" or "Stage passed, proceed to S6"}
```

## Important

- The judge agent is READ-ONLY — it cannot modify files
- This skill handles all file persistence (save review, update registry)
- Reviews are cumulative — never delete prior reviews
- Always tell the user what you're about to review and why before launching the judge
- After 3 consecutive FAILs on same target, escalate to human via email
