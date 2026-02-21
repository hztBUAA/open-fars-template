---
name: catchup
description: Generate a research onboarding document for the current Open-FARS project. Explains the field, survey findings, our innovation, hypotheses, experiment design, and current results in accessible language. Persisted to project catchup/ directory.
user_invocable: true
---

# Open-FARS Research Catch-Up

## Overview

Generate an accessible, structured research onboarding document for the current Open-FARS project. Designed for someone who needs to **quickly understand what this research is about, why it matters, what we're doing, and where we are** — without prior domain knowledge.

Each run produces a **self-contained document** that reflects the latest project state: new experiment results, updated hypotheses, revised plans. Prior catch-up documents are preserved for history.

## Usage

```
/catchup                              # Full catch-up, auto-detect project
/catchup 重点讲 SAE 和电路              # Full catch-up with emphasis area
/catchup email                        # Full catch-up + send via email-notify
/catchup email 给新加入的同学看          # Email catch-up with context
```

### Parsing rules

1. If arguments contain `email` → generate document AND send via email-notify
2. Remaining text after `email` keyword → user focus / emphasis area
3. If no `email` keyword, all text is user focus

## Data Collection Steps

Collect ALL of the following before generating the document. Use parallel tool calls where possible.

### Step 1: Project Metadata

Read `.open-fars/meta/registry.yaml`:
- Direction slug, project slug, paper title, target venue
- Current pipeline stage statuses
- Known degradations

### Step 2: Survey Foundation

Read from `.open-fars/survey/{direction}/`:
- `gaps.md` — research gaps (the "why" of this project)
- `INDEX.md` — paper count, categories
- `literature-network.md` — key citation chains (if exists)
- Scan `papers/` directory for count and topic coverage

Extract:
- Total papers surveyed
- Top 3-5 gaps that motivated this project
- Key prior work chain (the 5-8 papers that form the intellectual lineage)

### Step 3: Ideation Context

Read from `.open-fars/ideation/{direction}/`:
- `INDEX.md` — how many ideas were generated, which was selected
- The selected idea file (e.g., `ideas/idea-01-*.md`) — core proposal, novelty check

Extract:
- Why this idea scored highest
- What makes it novel (the novelty check results)
- The core insight in one sentence

### Step 4: Research Plan

Read from `.open-fars/plan/{direction}/{project}/LATEST.md`:
- Research questions (RQ1-RQ4)
- Hypotheses (H1-H4) with thresholds
- Model and task selection rationale
- Experiment design (E1-E6) overview
- Ablation design (A1-A5) overview

### Step 5: Current Results

Read latest experiment result JSON files from `.open-fars/projects/{project}/experiments/results/`:
- For each completed/in-progress experiment, extract headline numbers
- Compare results against hypothesis thresholds from the plan
- Note any surprises or failures

### Step 6: Prior Catch-Up Documents

```bash
ls .open-fars/projects/{project}/catchup/ 2>/dev/null
```

If prior documents exist, read the most recent one to understand what has changed since last time. The new document should note "what's new since last catch-up" if a prior exists.

## Document Structure

Generate the document in the following structure. Use Chinese for section headers and narrative (user's primary language for communication), keep technical terms in English.

```markdown
# {project_title} — 研究入门与进展串讲

**项目**: {paper_title}
**目标会议**: {target_venue}
**日期**: {today}
**方向**: {direction description}

---

## 一、一句话概括

{用一句通俗的话说清楚这个研究在干什么，不用任何术语}

## 二、从日常经验出发

{用 2-3 个具体例子，让没有 ML 背景的人也能理解这个问题的直觉}

## 三、研究领域概览

{画出领域的两个(或多个)社区，说明我们在它们之间的位置}
{说明为什么这个交叉点是空白的}

### 文献调研概况

- 调研论文数: {N}
- 核心论文链: {5-8 篇关键论文，按逻辑链排列，每篇一句话说明它贡献了什么}
- 研究空白: {top 3 gaps，每个用 2-3 句话解释}

## 四、关键术语表

{按逻辑顺序（不是字母顺序）列出所有关键术语}
{每个术语: 一句定义 + 一个类比或例子}

| 术语 | 解释 | 类比/例子 |
|------|------|----------|
| ... | ... | ... |

## 五、我们的创新点

{3 个创新点，每个:}
{1. 一句话概括}
{2. 为什么之前没人做}
{3. 为什么它重要}

## 六、研究设计

### 假设

{每个假设用「通俗版」+ 「技术版」两种方式表述}
{标注当前验证状态: ✅ 通过 / ❌ 失败 / 🔄 待验证}

### 实验一览

| 实验 | 做什么 | 回答哪个问题 | 当前状态 | 关键结果 |
|------|--------|-------------|---------|---------|
| E1 | ... | RQ1 / H1 | ... | ... |
| ... | ... | ... | ... | ... |

### 任务选择

{为什么选这 5 个任务，每个任务一句话说明}

### 模型选择

{为什么选这些模型，各自的角色}

## 七、当前实验结果

{对每个已有结果的实验:}
{- 关键数字}
{- 对照假设阈值的判断}
{- 意味着什么（通俗解释）}

{如果有假设失败的情况，诚实说明并讨论可能原因}

## 八、降级与风险

{当前存在的降级，用通俗语言解释每个降级为什么重要}
{最大的风险是什么}

## 九、数据流与实验依赖图

{用 ASCII 图画出 E1→E2→E3, E1→E4 等依赖关系}
{标注当前进度}

## 十、下一步

{接下来要做什么，优先级排序}

{If prior_catchup_exists: "\n## 附：本次更新内容\n\n{与上次 catch-up 相比有什么新进展}"}

{If user_focus_query: "\n## 重点补充: {user_focus_query}\n\n{针对用户关注领域的深入讨论}"}
```

## Document Persistence

**Every** catch-up document must be saved to disk:

1. Generate timestamp: `TZ=Asia/Shanghai date +"%Y-%m-%d_%H%M"`
2. Save to: `.open-fars/projects/{project}/catchup/{timestamp}_catchup.md`
3. Directory: `.open-fars/projects/{project}/catchup/` (create if not exists)
4. Files are append-only — never delete or overwrite prior documents
5. After saving, print the file path to the user

## Email Mode

If `email` is in the arguments, after saving the document:

1. Send via email-notify:
   ```bash
   python3 .claude/skills/email-notify/send-email.py \
     --subject "[Claude Code] Open-FARS 研究串讲: {paper_title_short}" \
     --body-file .open-fars/projects/{project}/catchup/{timestamp}_catchup.md
   ```

## Important

- **Accessible first**: the primary audience is someone who does NOT know this field. Jargon must be explained on first use.
- **Grounded in data**: every claim must reference actual files (survey papers, plan, results). Do not fabricate or extrapolate.
- **Honest about failures**: if a hypothesis failed, say so. If data is insufficient, say so.
- **Evolving document**: each run captures the project state at that moment. Compare against prior catch-ups when available.
- **Terminology consistency**: use the same English terms as the paper and plan. Do not translate technical terms into Chinese — keep them in English with Chinese explanation.
- **Prior catch-up diff**: if a prior catch-up exists, include a "what's new" section highlighting changes in results, status, or understanding.
