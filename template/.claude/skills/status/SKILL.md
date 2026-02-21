---
name: status
description: Generate a comprehensive project status report for the Open-FARS research pipeline. Shows pipeline progress, experiment status, paper progress, degradations, and next actions. Suitable for reporting to supervisors.
user_invocable: true
---

# Open-FARS Status Report

## Overview

Generate a structured, comprehensive status report for the current Open-FARS research project. The report is designed to be **presentable to a supervisor/PI** — concise, factual, with clear progress indicators.

## Usage

```
/status                    # Full report, printed to terminal
/status email              # Full report + send via email-notify
/status 重点关注实验进度      # Full report with emphasis on user's focus area
/status email 给老板看的周报  # Email report with user context
```

### Parsing rules

1. If arguments contain `email` → generate report AND send via email-notify
2. Remaining text after `email` keyword → user focus / additional context to highlight
3. If no `email` keyword, all text is user focus

## Data Collection Steps

Collect ALL of the following before generating the report. Use parallel tool calls where possible.

### Step 1: Pipeline State (registry.yaml)

Read `.open-fars/meta/registry.yaml`:
- Direction and project names
- Each stage status (S1-S7)
- Paper title and target venue
- Known degradations
- Review history (rounds, verdicts, scores)

### Step 2: Experiment Progress

For each active experiment, collect:

**Running processes:**
```bash
ps aux | grep -E "run_e[0-9]|chain|gemma" | grep -v grep
```

**E1 eval cache progress** (for each task):
```bash
for task in ioi sentiment arithmetic country_capital nli; do
  db=".open-fars/projects/{project}/experiments/results/e1_landscape/$task/eval_cache.db"
  sqlite3 "$db" "SELECT COUNT(*) FROM eval_cache" 2>/dev/null
done
```

**Latest experiment result files:**
```bash
find .open-fars/projects/{project}/experiments/results -name "*.json" -newer <last_report_date> | sort
```

**GPU utilization:**
```bash
nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader
```

### Step 3: Paper Status

Check `.open-fars/projects/{project}/paper/`:
- Does `main.tex` exist? When was it last modified?
- Count TODO markers: `grep -c "TODO" paper/sections/*.tex`
- Page count (from compilation log or aux file)
- Latest judge review score and verdict

### Step 4: Code Health

```bash
cd .open-fars/projects/{project}/code && python -m pytest tests/ --tb=no -q 2>&1 | tail -5
```

### Step 5: Key Results Summary

Read the latest experiment result JSON files for each completed experiment (E1-E4) and extract headline numbers:
- E1: fitness distribution (mean, std, range), autocorrelation, FDC
- E2: number of circuit families, clustering quality
- E3: H2 test result (within vs between, p-value)
- E4: SAE FDC, tautology test result

## Report Format

Generate the report in the following structure. Use Chinese for section headers (the user's supervisor is Chinese-speaking), but keep technical terms in English.

```markdown
# Open-FARS 项目进展报告

**项目**: {paper_title}
**目标会议**: {target_venue}
**日期**: {today}
**方向**: {direction description}

---

## 一、流水线总览

| 阶段 | 状态 | 完成度 | 备注 |
|------|------|--------|------|
| S1 文献调研 | ✅ 完成 | 90 篇 | — |
| S2 创意生成 | ✅ 完成 | 5 个创意 | idea-01 入选 |
| S3 实验计划 | ✅ 完成 | v1 | 6 实验 + 5 消融 |
| S4 代码实现 | ✅ 完成 | 294 tests | — |
| S5 实验执行 | 🔄 进行中 | XX% | {detail} |
| S6 论文撰写 | 🔄 进行中 | 初稿 | Judge {score}/10 |
| S7 修改完善 | ⏳ 待开始 | — | 待 full data |

## 二、实验进度

### 正在运行

| 实验 | 任务 | 进度 | 预计 |
|------|------|------|------|
| E1 景观特征化 | IOI | 84% | — |
| ... | ... | ... | — |

### 已完成结果

{Key numbers from completed experiments}

### 降级与修复

| 编号 | 问题 | 严重度 | 修复状态 |
|------|------|--------|---------|
| D1 | ... | critical | ✅ 已修复 |
| ... | ... | ... | ... |

## 三、论文进展

- **页数**: {N} 页
- **Judge 评分**: {score}/10 ({verdict})
- **主要问题**: {top 3 issues from judge}
- **TODO 标记**: {count} 个

## 四、计算资源

| 资源 | 状态 |
|------|------|
| GPU | {N}×{type}, {utilization} |
| API | {model}, {status} |

## 五、风险与阻塞

{List any blockers, risks, or items needing human decision}

## 六、下一步计划

1. {next action 1}
2. {next action 2}
3. {next action 3}

{If user_focus_query: "\n## 七、重点关注\n\n{Detailed discussion of user's focus area}"}
```

## Report Persistence

**Every** report (regardless of whether `email` is specified) must be saved to disk:

1. Generate timestamp: `TZ=Asia/Shanghai date +"%Y-%m-%d_%H%M"`
2. Save to: `.open-fars/projects/{project}/status/{timestamp}_status.md`
3. Directory: `.open-fars/projects/{project}/status/` (create if not exists)
4. Files are append-only — never delete or overwrite prior reports
5. After saving, print the file path to the user

This ensures a persistent history of all status reports for the project, useful for tracking progress over time and providing to supervisors.

## Email Mode

If `email` is in the arguments, after saving the report to `status/`:

1. Send via email-notify:
   ```bash
   python3 .claude/skills/email-notify/send-email.py \
     --subject "[Claude Code] Open-FARS 项目进展: {one-line summary}" \
     --body-file .open-fars/projects/{project}/status/{timestamp}_status.md
   ```

## Important

- **Facts only**: never inflate progress or hide problems — the user needs accurate info for their supervisor
- **Quantify everything**: use numbers, percentages, counts — not vague words
- **Flag risks early**: if something might block progress, say so explicitly
- **Compare to plan**: always reference the original research plan when discussing progress
- **Degradation transparency**: always include the degradation table, even if all are fixed
