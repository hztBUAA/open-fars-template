# Open-FARS 工程规范

本文件是 Open-FARS 项目的**唯一工程规范来源 (Single Source of Truth)**。
所有 skills、agents、以及主线程编排均必须遵守此规范。

---

## 1. Registry Schema (`registry.yaml`)

文件位置：`.open-fars/meta/registry.yaml`

```yaml
# ============================================================
# Open-FARS Registry — 主索引文件
# 所有字段定义见 .claude/SPEC.md
# ============================================================

# --- 顶层元数据 ---
direction: "{direction-slug}"                    # string, required — 研究方向 slug
created: "YYYY-MM-DDTHH:MM+08:00"               # string(ISO8601), required — 首次创建时间
updated: "YYYY-MM-DDTHH:MM+08:00"               # string(ISO8601), required — 最后更新时间

# --- 流水线阶段状态 ---
# 每个阶段的状态值仅允许: "pending" | "in_progress" | "completed"
stages:
  S1_survey: "pending"
  S2_ideation: "pending"
  S3_plan: "pending"
  S4_assets: "pending"
  S5_experiment: "pending"
  S6_writing: "pending"
  S7_revision: "pending"

# --- 审查计数器 ---
# 主编排用于跟踪各阶段 review 次数，判断是否达到邮件升级阈值
# 阈值规则见 AGENTS.md 编排协议
review_counts:                                     # map[string, int], required
  S1_survey: 0
  S2_ideation: 0
  S3_plan: 0
  S4_assets: 0                                     # S4+S5 共享计数器（联合阶段）
  S5_experiment: 0                                  # S4+S5 共享计数器（联合阶段）
  S6_writing: 0
  S7_revision: 0

# --- 方向索引 ---
directions:
  {direction-slug}:                              # string, key = slug
    slug: "{direction-slug}"                     # string, required — 与 key 一致
    description: "..."                           # string, required — 方向描述
    created: "YYYY-MM-DDTHH:MM+08:00"           # string(ISO8601), required
    survey_count: 0                              # int, required — 调研论文数
    ideation_count: 0                            # int, required — 生成创意数
    projects:                                    # list[string], required — 关联项目 slug 列表
      - "{project-slug}"

# --- 项目索引 ---
projects:
  {project-slug}:                                # string, key = slug
    slug: "{project-slug}"                       # string, required — 与 key 一致
    direction: "{direction-slug}"                # string, required — 所属方向
    idea: "idea-{NN}"                            # string, required — 源自哪个 idea
    plan_version: "v{N}"                         # string, required — 当前计划版本
    created: "YYYY-MM-DDTHH:MM+08:00"           # string(ISO8601), required
    status: "planning"                           # string, required — 见下方枚举
    paper_title: "..."                           # string, required — 论文标题
    target_venue: "..."                          # string, required — 目标会议

# project.status 枚举值:
#   "planning"       — S3 进行中
#   "implementing"   — S4 进行中
#   "experimenting"  — S5 进行中
#   "writing"        — S6 进行中
#   "revising"       — S7 进行中
#   "submitted"      — 已投稿
#   "accepted"       — 已录用

# --- 审查记录 ---
# 每次 judge 审查或 audit 后追加一条，只增不删
reviews:                                         # list[ReviewEntry], required — 可为空列表 []
  - path: "reviews/{timestamp}_judge_{type}_r{N}.md"   # string, required — 相对项目目录
    type: "paper_review"                         # string, required — 见下方枚举
    round: 1                                     # int, required — 同类型审查的轮次
    verdict: "FAIL"                              # string, required — "PASS" | "FAIL"
    score: 5.6                                   # float, optional — 仅 paper_review 必填
    date: "YYYY-MM-DDTHH:MM+08:00"              # string(ISO8601), required

# review.type 枚举值:
#   "stage_review"   — 阶段审查 (S1-S5)
#   "paper_review"   — 论文审查 (S6)
#   "audit"          — 计划 vs 实际 审计

# --- 降级记录 ---
# 记录实际执行与研究计划的偏差，只增不删，可更新 status 字段
degradations:                                    # list[DegradationEntry], required — 可为空列表 []
  - id: "D{N}"                                   # string, required — 唯一编号
    severity: "critical"                         # string, required — "critical" | "medium" | "minor"
    item: "..."                                  # string, required — 降级内容简述
    reason: "..."                                # string, required — 降级原因
    status: "open"                               # string, required — "open" | "mitigated" | "fixed" | "accepted"
    fixed_date: null                             # string(ISO8601)|null, optional — 修复时间
```

### 字段更新规则

| 操作 | 谁触发 | 更新哪些字段 |
|------|--------|-------------|
| 阶段开始 | 主线程 spawn agent 前 | `stages.S{N}` → `"in_progress"`, `updated` |
| 阶段完成 | agent 返回后 | `stages.S{N}` → `"completed"`, `updated` |
| Judge 审查 | `/review` skill 完成后 | `reviews` 追加条目, `updated` |
| 发现降级 | audit 后 | `degradations` 追加条目, `updated` |
| 降级修复 | 确认修复后 | `degradations[N].status` → `"fixed"`, `fixed_date`, `updated` |
| 项目状态变更 | 阶段推进时 | `projects.{slug}.status`, `updated` |

### 时间戳格式

统一使用 ISO 8601 + 北京时区：`YYYY-MM-DDTHH:MM+08:00`

生成方式：`TZ=Asia/Shanghai date +"%Y-%m-%dT%H:%M+08:00"`

短格式（用于文件名）：`TZ=Asia/Shanghai date +"%Y-%m-%d_%H%M"`

---

## 1.5 Config Schema (`config.yaml`)

文件位置：`.open-fars/config.yaml`

**定位**：项目配置的唯一入口。用户设定研究意图和约束边界，Claude 在流水线推进过程中补充和完善具体参数。

**权限模型**：config.yaml 是一个**活文档（Living Document）**，不是一次性静态配置。

- **用户**：可自由编辑所有字段。用户显式设定的值具有最高优先级。
- **Claude（主线程，阶段完成后）**：可以**补充和完善**用户未指定的字段，但**禁止覆盖**用户已显式设定的值。

### 字段分类

每个字段属于以下三类之一：

| 类别 | 含义 | 谁写 | 示例 |
|------|------|------|------|
| 🔒 **user-locked** | 用户必须设定，Claude 禁止修改 | 仅用户 | `project.direction`, `target_venue`, `language` |
| 🌱 **user-seeds, Claude-augments** | 用户给出初始意图（可以是模糊的），Claude 在相关阶段完成后补充具体值 | 用户初始化 + Claude 补充 | `seed_queries`（用户给论文标题→S1 解析为检索词+CorpusId），`experiment.models`（S3 plan 确定后补充） |
| 🤖 **Claude-fills** | 用户通常不需要关心，Claude 根据阶段产出自动填充；用户如果写了则作为约束 | Claude 为主，用户可覆盖 | `must_include_papers`, `experiment.tasks`, `prompt_methods` |

对于用户未指定的字段，agent 应使用文档中标注的**学术默认值（Academic Default）**。

### Config 更新协议

```python
# 伪代码：Claude 更新 config.yaml 的标准流程
config = yaml.safe_load(open(".open-fars/config.yaml"))

# 规则 1：永远不覆盖用户已设定的值
if config["experiment"].get("tasks"):
    # 用户已指定 → 至少包含这些，可以追加但不可删除
    pass
else:
    # 用户未指定 → Claude 从 plan 产出中填充
    config["experiment"]["tasks"] = derived_from_plan

# 规则 2：追加而非替换（对 list 类型）
# 用户写了 ["task-a", "task-b"]，S3 plan 建议加 "task-c"
# → 结果是 ["task-a", "task-b", "task-c"]

# 规则 3：每次更新必须添加注释说明来源
# tasks:                         # [S3-plan] 从研究计划 v1 填充
#   - "task-a"                   # [user] 用户指定
#   - "task-c"                   # [S3-plan] 计划建议

yaml.dump(config, open(".open-fars/config.yaml", "w"), allow_unicode=True)
```

### 更新时机

| 阶段完成 | 可更新的 config 字段 |
|---------|-------------------|
| S1 survey 完成 | `survey.must_include_papers`（解析用户给的论文标题为 CorpusId） |
| S2 ideation 完成 | （通常无需更新 config） |
| S3 plan 完成 | `experiment.tasks`, `experiment.models`, `experiment.prompt_methods`, `plan.*` 细化 |
| S4 assets 完成 | `assets.python_version`（确认实际版本）, `assets.framework_preferences`（确认实际使用） |
| S5 实验中 | `experiment.*` 降级调整（如 eval_samples 实际值） |

### Schema

```yaml
# --- 🔒 user-locked 字段 ---
project:                                       # 项目基本信息
  direction: string                            # required — 研究方向 slug
  description: string                          # required — 方向描述
  target_venue: string                         # required — 目标投稿会议
  language: "en" | "zh"                        # required — 论文语言（default: "en"）
  communication_language: "en" | "zh"          # required — 沟通语言（default: "en"）

# --- 🌱 user-seeds, Claude-augments 字段 ---
survey:                                        # S1 约束
  min_papers: int                              # optional — 最少调研论文数（default: 50）
  max_papers: int                              # optional — 最多调研论文数（default: 150）
  seed_queries: list[string]                   # required — 初始检索词或论文标题（用户可给标题，S1 agent 解析）
  must_include_papers: list[string]            # optional — 必须包含的论文（CorpusId 或标题均可，S1 自动解析）
  citation_depth: int                          # optional — 引用链追踪深度 (1-3)（default: 2）

ideation:                                      # S2 约束
  min_ideas: int                               # optional — 至少生成创意数（default: 5）
  max_ideas: int                               # optional — 最多创意数（default: 10）
  novelty_check: bool                          # optional — 是否新颖性检查（default: true）
  scoring_criteria:                            # optional — 评分权重 (sum=1.0)
    novelty: float                             #   default: 0.3
    feasibility: float                         #   default: 0.25
    impact: float                              #   default: 0.25
    clarity: float                             #   default: 0.2

plan:                                          # S3 约束
  max_experiments: int                         # optional — 主实验数量上限（default: 6）
  max_ablations: int                           # optional — 消融实验上限（default: 5）
  require_baselines: bool                      # optional（default: true）
  require_statistical_tests: bool              # optional（default: true）

assets:                                        # S4 约束
  require_tests: bool                          # optional（default: true）
  min_test_coverage: int                       # optional — 百分比 (0-100)（default: 60）
  python_version: string                       # optional（default: 运行时检测）
  framework_preferences: list[string]          # optional — 偏好框架（无 default，agent 自选）

# --- 🤖 Claude-fills 字段（用户指定则作为约束） ---
experiment:                                    # S5 约束
  min_eval_samples: int                        # optional — 每 task 最少样本（default: 200）
  min_seeds: int                               # optional — 最少随机种子数（default: 3）
  tasks: list[string]                          # optional — task 列表（S3 plan 完成后自动填充）
  models: list[string]                         # optional — 实验模型名列表（S3 plan 完成后自动填充）
  prompt_methods: list[string]                 # optional — prompt 生成方法（S3 plan 完成后自动填充）
  allow_degradation: bool                      # optional（default: true）
  max_degradation_severity: "critical" | "medium" | "minor"  # optional（default: "medium"）

writing:                                       # S6 约束
  template: string                             # optional — LaTeX 模板名（default: 根据 target_venue 推断）
  max_pages: int                               # optional — 正文页数限制（default: 根据 target_venue 推断）
  require_appendix: bool                       # optional（default: true）
  figure_format: "pdf" | "png" | "both"        # optional（default: "pdf"）

revision:                                      # S7 约束
  num_simulated_reviewers: int                 # optional — 模拟审稿人数（default: 3）
  target_score: float                          # optional — 目标评分 /10（default: 6.0）
  max_revision_rounds: int                     # optional — 最大修改轮次（default: 3）

# --- 🔒 user-locked 字段 ---
orchestration:                                 # 编排控制
  auto_review: bool                            # optional（default: true）
  escalation_thresholds:                       # optional — 各阶段升级阈值
    S1_survey: int                             #   default: 3
    S2_ideation: int                           #   default: 3
    S3_plan: int                               #   default: 3
    S4_assets: int                             #   default: 5
    S5_experiment: int                         #   default: 5
    S6_writing: int                            #   default: 5
    S7_revision: int                           #   default: 3
  email_on_decision_points: bool               # optional（default: true）
  pause_on_escalation: bool                    # optional（default: true）

compute:                                       # 计算资源描述（供 agent 了解可用算力）
  gpus: string                                 # optional — e.g. "8x NVIDIA H20D"
  gpu_memory_each: string                      # optional — e.g. "140GB"
  interconnect: string                         # optional

model_discovery:                               # 模型发现配置（替代硬编码模型列表）
  local_model_paths:                           # optional — 本地模型搜索路径
    - string                                   # e.g. "/mnt/workspace/models/"
  local_scan_command: string                   # optional — 扫描本地模型的命令
  api_base_url: string                         # optional — API 模型的 base URL
  api_list_command: string                     # optional — 查询可用 API 模型的命令

paths:                                         # 外部路径
  prior_work: string                           # optional — 已有研究数据路径
```

### config.yaml 与 registry.yaml 的职责划分

| 维度 | `config.yaml` | `registry.yaml` |
|------|---------------|-----------------|
| **谁编辑** | 用户 + Claude（受限补充） | Claude（主线程/agents） |
| **内容** | 研究意图、约束参数、阶段产出衍生配置 | 运行状态、审查记录、降级 |
| **变更频率** | 用户初始化 + 每个阶段完成后可能补充 | 每次阶段变更/审查时更新 |
| **读取方** | 所有 agents/skills/主线程 | 所有 agents/skills/主线程 |

### Agents 读取 config.yaml 协议

所有 agents 在开始工作前**必须**：

```python
# 伪代码：标准读取流程
config = yaml.safe_load(open(".open-fars/config.yaml"))

# 根据自身阶段读取对应 section
# S1 agent → config["survey"]
# S2 agent → config["ideation"]
# Judge agent → config["revision"]["target_score"] 等
# 主线程 → config["orchestration"]

# 对于缺失字段，使用 schema 中标注的 Academic Default
min_papers = config.get("survey", {}).get("min_papers", 50)  # default: 50
```

---

## 2. 目录结构规范

```
{project-root}/
├── CLAUDE.md                          # 项目级 Claude 指令入口 (@AGENTS.md)
├── AGENTS.md                          # 编排协议 + agents/skills 索引
├── .claude/
│   ├── SPEC.md                        # ★ 本文件 — 唯一工程规范
│   ├── agents/                        # Subagent 定义
│   │   ├── open-fars-survey.md
│   │   ├── open-fars-ideation.md
│   │   ├── open-fars-plan.md
│   │   ├── open-fars-assets.md
│   │   ├── open-fars-experiment.md
│   │   ├── open-fars-writing.md
│   │   ├── open-fars-revision.md
│   │   └── open-fars-judge.md
│   └── skills/                        # Skill 定义
│       ├── review/SKILL.md
│       ├── status/SKILL.md
│       ├── catchup/SKILL.md
│       └── email-notify/
│           ├── SKILL.md
│           ├── send-email.py
│           └── config.json
│
├── .open-fars/                        # ★ 研究数据（只增不删）
│   ├── config.yaml                    # ★ 用户配置（schema 见 § 1.5）
│   ├── meta/
│   │   └── registry.yaml             # 主索引（schema 见 § 1）
│   │
│   ├── survey/{direction-slug}/       # S1 产出
│   │   ├── {timestamp}_{topic}.md    # 调研记录（时间戳前缀）
│   │   ├── papers/{corpusId}.md      # 论文记录（Semantic Scholar CorpusId 去重）
│   │   ├── gaps.md                   # 研究空白（增量更新）
│   │   ├── literature-network.md     # 引用网络
│   │   └── INDEX.md                  # 汇总索引
│   │
│   ├── ideation/{direction-slug}/     # S2 产出
│   │   ├── {timestamp}_{session}.md  # 创意会议记录
│   │   ├── ideas/idea-{NN}-{slug}.md # 独立创意文件
│   │   └── INDEX.md                  # 创意排名索引
│   │
│   ├── plan/{direction-slug}/{project-slug}/  # S3 产出
│   │   ├── {timestamp}_v{N}.md       # 版本化计划快照
│   │   ├── LATEST.md                 # → 最新版本（符号链接或复制）
│   │   └── INDEX.md                  # 版本变更日志
│   │
│   └── projects/{project-slug}/       # S4-S7 产出
│       ├── code/                      # S4: 代码实现
│       │   ├── src/
│       │   ├── tests/
│       │   ├── configs/
│       │   └── requirements.txt
│       ├── experiments/               # S5: 实验结果
│       │   └── results/
│       │       └── e{N}_{name}/{task}/   # 按实验编号和 task 分目录
│       ├── paper/                     # S6: LaTeX 论文
│       │   ├── main.tex
│       │   ├── sections/
│       │   ├── figures/
│       │   └── references.bib
│       ├── reviews/                   # S7 + Judge 审查记录
│       │   └── {timestamp}_judge_{type}_r{N}.md
│       ├── status/                    # /status 产出
│       │   └── {timestamp}_status.md
│       └── catchup/                   # /catchup 产出
│           └── {timestamp}_catchup.md
```

### 目录规则

1. **只增不删**：`.open-fars/` 下的文件只追加不删除（审查、降级、调研记录等）
2. **时间戳前缀**：所有产出文件使用 `YYYY-MM-DD_HHmm` 前缀，北京时间
3. **去重**：survey 论文按 Semantic Scholar CorpusId 去重
4. **实验结果按 task 分目录**：`results/e{N}_{name}/{task}/`
5. **reviews 统一存放**：stage review、paper review、audit 全部存在 `reviews/` 下

---

## 3. 文件命名规范

| 文件类型 | 命名模式 | 示例 |
|---------|---------|------|
| 调研记录 | `{timestamp}_{topic}.md` | `2026-03-01_1400_transformer-scaling.md` |
| 创意文件 | `idea-{NN}-{slug}.md` | `idea-01-adaptive-routing.md` |
| 计划版本 | `{timestamp}_v{N}.md` | `2026-03-02_0900_v1.md` |
| Judge 审查 | `{timestamp}_judge_{type}_r{N}.md` | `2026-03-05_1342_judge_paper_review_r1.md` |
| Audit | `{timestamp}_audit_{scope}.md` | `2026-03-05_1350_audit_plan_vs_actual.md` |
| 状态报告 | `{timestamp}_status.md` | `2026-03-06_1604_status.md` |
| 串讲文档 | `{timestamp}_catchup.md` | `2026-03-06_1616_catchup.md` |
| 实验结果 | `e{N}_results_{timestamp}.json` | `e2_results_2026-03-10_2028.json` |

---

## 4. Skills 与 Registry 交互协议

所有 skills 在读写 registry.yaml 时必须遵守：

### 读取

```python
# 伪代码：标准读取流程
registry = yaml.safe_load(open(".open-fars/meta/registry.yaml"))
project_slug = [k for k, v in registry["projects"].items() if v["status"] not in ("submitted", "accepted")][0]
stages = registry["stages"]
reviews = registry.get("reviews", [])
degradations = registry.get("degradations", [])
```

### 写入

```python
# 伪代码：标准写入流程
registry["updated"] = now_iso8601()  # 必须更新 updated 字段
# 修改目标字段...
yaml.dump(registry, open(".open-fars/meta/registry.yaml", "w"), allow_unicode=True)
```

### 追加 review

```yaml
# 追加到 reviews 列表末尾，禁止修改已有条目
reviews:
  - path: "reviews/2026-02-21_1342_judge_paper_review_r1.md"
    type: "paper_review"       # 必须是 stage_review | paper_review | audit
    round: 1                   # 同 type 的递增序号
    verdict: "FAIL"            # 必须是 PASS | FAIL
    score: 5.6                 # paper_review 必填，其他可选
    date: "2026-02-21T13:42+08:00"
```

### 追加/更新 degradation

```yaml
# 追加新降级：
degradations:
  - id: "D7"                   # 递增编号，不复用
    severity: "medium"         # critical | medium | minor
    item: "..."
    reason: "..."
    status: "open"             # 新建必须为 open
    fixed_date: null

# 更新降级状态（仅允许 status 和 fixed_date 字段变更）：
degradations:
  - id: "D1"
    status: "fixed"            # open → mitigated | fixed | accepted
    fixed_date: "2026-02-21T07:08+08:00"
```

---

## 5. 版本与变更

| 版本 | 日期 | 变更 |
|------|------|------|
| v1 | 2026-02-21 | 初始版本：registry schema, 目录结构, 命名规范, 交互协议 |
| v2 | 2026-02-21 | 新增 config.yaml schema (§ 1.5), review_counts, 编排阈值参数化到 config |
| v3 | 2026-02-21 | config.yaml 升级为活文档：字段三分类（🔒/🌱/🤖），Claude 可补充不可覆盖；models 改为 model_discovery；所有字段 optional + academic defaults |
| v4 | 2026-02-21 | 模板化：移除项目特定内容，泛化为通用 Open-FARS 规范 |
