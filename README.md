# Open-FARS Template

Open-FARS (Fully Automated Research System) template repository. Scaffold a new AI-driven research project with a single command.

## What is Open-FARS?

Open-FARS is a 7-stage automated research pipeline driven by Claude Code:

| Stage | Agent | What it does |
|-------|-------|-------------|
| S1 | `open-fars-survey` | Systematic literature survey via Semantic Scholar API |
| S2 | `open-fars-ideation` | Generate and score research ideas from survey gaps |
| S3 | `open-fars-plan` | Design experiments: RQs, hypotheses, baselines, task graph |
| S4 | `open-fars-assets` | Implement method, baselines, evaluation code |
| S5 | `open-fars-experiment` | Execute experiments, statistical analysis, figures |
| S6 | `open-fars-writing` | Write complete LaTeX paper |
| S7 | `open-fars-revision` | Simulated peer review and revision |

The pipeline runs autonomously with quality gates (judge agent) at each stage, email notifications at decision points, and automatic escalation when issues arise.

## Quick Start

### Install

```bash
git clone https://github.com/hzt/open-fars-template.git
cd open-fars-template
./bin/fars install    # Symlink to /usr/local/bin
```

### Create a new project

```bash
fars init ~/research/my-project
```

The interactive wizard will ask for:
- **Research direction** (slug, e.g. `llm-alignment`)
- **Description** (one line)
- **Target venue** (e.g. `NeurIPS 2026`)
- **Language** (`en` or `zh`)
- **Seed queries** (comma-separated search terms)
- **Compute resources** (describe your GPU setup)
- **Email** (optional, for notification skill)

### Start the pipeline

```bash
cd ~/research/my-project
# Open Claude Code and say:
# "Start the Open-FARS pipeline"
```

## Project Structure (after `fars init`)

```
your-project/
├── CLAUDE.md                    # Points to AGENTS.md
├── AGENTS.md                    # Pipeline orchestration protocol
├── .gitignore
├── .claude/
│   ├── SPEC.md                  # Engineering specification (single source of truth)
│   ├── agents/                  # 8 subagent definitions
│   │   ├── open-fars-survey.md
│   │   ├── open-fars-ideation.md
│   │   ├── open-fars-plan.md
│   │   ├── open-fars-assets.md
│   │   ├── open-fars-experiment.md
│   │   ├── open-fars-writing.md
│   │   ├── open-fars-revision.md
│   │   └── open-fars-judge.md
│   └── skills/                  # 4 user-invocable skills
│       ├── catchup/SKILL.md     # /catchup - research onboarding doc
│       ├── review/SKILL.md      # /review - trigger quality review
│       ├── status/SKILL.md      # /status - project progress report
│       └── email-notify/        # email notification system
│           ├── SKILL.md
│           ├── send-email.py
│           └── config.json.example
└── .open-fars/
    ├── config.yaml              # Your project configuration
    └── meta/
        └── registry.yaml        # Pipeline state tracking
```

## Skills (slash commands in Claude Code)

| Command | Description |
|---------|------------|
| `/review` | Trigger quality review (auto-detects what to review) |
| `/status` | Generate project progress report |
| `/catchup` | Generate research onboarding document |
| `/email-notify` | Send structured notification email |

## Configuration

Edit `.open-fars/config.yaml` after scaffolding to fine-tune:

- Survey parameters (paper counts, citation depth)
- Ideation constraints (idea count, scoring weights)
- Experiment limits (max experiments, ablations)
- Writing settings (template, page limit)
- Revision targets (simulated reviewers, target score)
- Compute resources (GPU description)
- Orchestration (auto-review, escalation thresholds)

Full schema documented in `.claude/SPEC.md`.

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- Git
- Bash 4+
