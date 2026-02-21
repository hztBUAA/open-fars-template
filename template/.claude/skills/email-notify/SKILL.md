---
name: email-notify
description: Use when a task reaches a milestone, completes, fails after retries, or needs human decision - sends structured notification email to the user
---

# Email Notify

## Overview

Send structured notification emails to the user (god/human-in-the-loop) via SMTP. This is the sole communication channel between Claude Code and the user in autonomous/god-mode scenarios.

## Setup

The send-email.py script and config.json live alongside this SKILL.md in the project's `.claude/skills/email-notify/` directory.

```bash
# First-time setup:
python3 .claude/skills/email-notify/send-email.py --init
# Edit .claude/skills/email-notify/config.json with your credentials
```

`config.json` fields:
- `smtp_host` — SMTP server (e.g. `smtp.qq.com`, `smtp.gmail.com`)
- `smtp_port` — SMTP SSL port (typically `465`)
- `smtp_user` — sender email address
- `smtp_auth_code` — SMTP authorization code (not login password)
- `recipient` — notification recipient email
- `sender_name` — display name in From header (default: `Claude Code`)

## When to Use

- Task completed and ready for user acceptance
- Judge review failed 3+ times, needs human escalation
- Critical decision point that requires human judgment
- Periodic progress report for long-running tasks
- Unexpected error or blocker that cannot be resolved autonomously

## Usage

Send email via the asset script:

```bash
python3 .claude/skills/email-notify/send-email.py \
  --subject "[Claude Code] <concise subject>" \
  --body "<structured report>"
```

Or with a body file for longer reports:

```bash
python3 .claude/skills/email-notify/send-email.py \
  --subject "[Claude Code] <subject>" \
  --body-file /path/to/report.md
```

Optional attachment:

```bash
python3 .claude/skills/email-notify/send-email.py \
  --subject "[Claude Code] <subject>" \
  --body "See attachment" \
  --attachment /path/to/file
```

## Email Content Template

Always structure the email body as follows:

```
[Session Subject]
<what this task/session is about>

[Status]
COMPLETED / NEEDS_REVIEW / ESCALATION / PROGRESS_UPDATE

[Summary]
<2-5 bullet points of what was done>

[Original Prompt]
<the user's original task prompt, abbreviated if very long>

[Details]
<specifics: test results, judge review scores, blockers, etc.>

[Action Required]
<what the user needs to do: review PR, make decision, provide input, or nothing>

[References]
<git branch, PR link, file paths, session ID if available>
```

## Subject Line Convention

Always prefix with `[Claude Code]`:
- `[Claude Code] Task Complete: <task name>`
- `[Claude Code] ESCALATION: <issue summary>`
- `[Claude Code] Progress: <milestone name>`
- `[Claude Code] Decision Needed: <question>`

## Common Mistakes

- Sending emails too frequently (batch updates, don't spam)
- Vague subject lines (be specific about what happened)
- Missing action-required section (user must know what to do next)
- Forgetting to include references (branch name, file paths)
