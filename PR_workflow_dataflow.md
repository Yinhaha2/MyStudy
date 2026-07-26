# PR 分析工作流 — 数据流向说明书

> 版本：2026-07-25  
> 目的：说明一次 API 调用从哪些文件读入、如何拼 prompt、结果写到哪里。实现脚本时按本文档对齐即可。

---

## 1. 流程总览（单 PR 一次调用）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DeepSeek Chat Completions                         │
└─────────────────────────────────────────────────────────────────────────┘
         ▲                                              │
         │  user message（按顺序拼接的多段文本/JSON）      │  assistant
         │                                              ▼
┌────────┴────────┐                              ┌──────────────┐
│ 输入（固定+可变） │                              │ 解析与落盘    │
└────────┬────────┘                              └──────┬───────┘
         │                                              │
         │                                              ▼
         │                                    output_pr_analysis/
         │                                    {pr_id}_analysis.json
```

**固定输入（每次相同）**

| 顺序 | 组成部分 | 源文件 / 目录 |
|------|----------|----------------|
| 1 | 系统级指令 | `prompt.md` |
| 2 | 输出字段模板说明 | `schema.json`（中文占位说明，约束字段名与层级） |
| 3–8 | 6 组 few-shot | 每组 = **该 PR 的源数据载荷** + **金标准** `{pr_id}_analysis.json` |

**可变输入（每条待分析 PR 不同）**

| 顺序 | 组成部分 | 源 |
|------|----------|-----|
| 9 | 待分析 PR 源数据载荷 | 由 `finaldatabase` 按 `pr_id` 组装（见 §3） |
| — | （可选）预计算指标 | 脚本从载荷统计后插入，减轻模型算术负担 |

**输出**

| 步骤 | 动作 |
|------|------|
| API 返回 | 模型应只返回 **一个 JSON 对象**（见 `prompt.md` Output Format） |
| 解析 | 去 markdown 围栏、 `json.loads`、可选 schema 键校验 |
| 写入 | `output_pr_analysis/{pr_id}_analysis.json`（目录不存在则创建） |

---

## 2. Few-shot 固定集合（A+C，6 条）

与 `candidate.md` / `workflow_size_policy.md` 一致：

| # | pr_id | 金标准 JSON | 源数据 |
|---|-------|-------------|--------|
| 1 | 3228424652 | `3228424652_analysis.json` | `finaldatabase` → `build_payload(3228424652)` |
| 2 | 3074351366 | `3074351366_analysis.json` | 同上 |
| 3 | 3194284966 | `3194284966_analysis.json` | 同上 |
| 4 | 3145702280 | `3145702280_analysis.json` | 同上 |
| 5 | 3125029980 | `3125029980_analysis.json` | 同上 |
| 6 | 3022909076 | `3022909076_analysis.json` | 同上 |

**Few-shot 块推荐结构（每个 PR 重复 6 次）**

```text
### Few-shot example {i} — pr_id={pr_id} (reference only; do not re-analyze)

#### Source payload
{JSON or structured text: master row + reviews + comments + timeline + commits + file stats …}

#### Gold analysis
{contents of {pr_id}_analysis.json}
```

模型任务：**只分析**文末「Target PR」；few-shot 仅作结构与文风参考。

---

## 3. 「PR 源数据文件」从哪来（数据流向）

所有 PR（few-shot 与待分析）共用同一套组装逻辑，数据源均在 `finaldatabase/`。

```
finaldatabase/pr_master/perf_prs_expanded_final.csv
        │
        │  pr_id 过滤 → meta（title, body 摘要字段, agent, topic, status, …）
        ▼
finaldatabase/per_pr/{pr_id}/
        ├── commits.parquet          ─┐
        ├── commit_details.parquet   ─┼→ 变更规模、文件列表、commit message
        ├── reviews.parquet          ─┤
        ├── review_comments.parquet  ─┼→ 审查与讨论（含 diff_hunk 时优先）
        ├── comments.parquet         ─┤
        ├── timeline.parquet         ─┘→ 事件序、寿命、是否 revert 等
        └── related_issue.parquet    ─→ 关联 issue（若有）
        │
        ▼
   build_payload(pr_id)  →  单次 workflow 中的「源数据载荷」
   （推荐 mode: standard_no_patch，见 workflow_size_policy.md）
```

### 3.1 载荷内容（推荐 `standard_no_patch`）

| 载荷分区 | 主要来源 | 用途 |
|----------|----------|------|
| `meta` | 主表 CSV 行 | agent、topic、status、URL、detection_source |
| `body` / `body_summary` | 主表或论文 CSV 正文 | 性能声称、复现描述 |
| `reviews` | `reviews.parquet` | formal review 状态与正文 |
| `review_comments` | `review_comments.parquet` | 行内评论 + **diff_hunk**（无完整 patch 时的代码线索） |
| `pr_comments` | `comments.parquet` | 讨论串 |
| `timeline` | `timeline.parquet` | 合并/关闭/auto-merge 等事件 |
| `commits` | `commits.parquet` + `commit_details` 聚合 | commit 数、message、**按文件 additions/deletions**（不含 patch 全文） |
| `linked_issues` | `related_issue` + 可选 issue 文本 | issue 上下文 |
| `data_coverage` | 脚本布尔探测 | 与输出 JSON 的 `data_coverage` 对齐 |

**默认不上传**：`commit_details.patch` 全文（体积极大；见 `workflow_size_policy.md`）。

### 3.2 与输出 JSON 的关系

| 方向 | 说明 |
|------|------|
| 源数据 → 模型 | 原始、偏「证据层」；可体积大、含重复 |
| 模型 → `{pr_id}_analysis.json` | 结构化结论；`quantitative_metrics` 宜与载荷数字一致；`evidence` 为摘要，禁止贴整段 patch |
| 枚举字段 | `prompt.md` 已强调：**所有枚举值必要时可扩展**；与 `schema.json` 列举不完全时不视为冲突 |

---

## 4. Prompt 拼接顺序（与 `prompt.md` 一致）

实际送入 API 的 **单条 user message**（或 system + user 拆分）建议等价于：

1. **`prompt.md` 全文**（含 Controlled Taxonomies、Annotation Rules、Output Format）
2. **`schema.json` 全文**（字段说明模板）
3. **Few-shot × 6**：`源数据载荷` + `金标准 analysis.json`
4. **分隔标题**：`## Target Pull Request — pr_id={target_id}`
5. **`build_payload(target_id)`**
6. **收尾句**：`Analyze the target PR above and return the JSON analysis object only.`

System role 可固定为简短一句「Follow the user message」；也可把 `prompt.md` 放在 `system`、其余放在 `user`——实现时二选一，但**块顺序**不变。

---

## 5. API 调用与返回解析

### 5.1 调用

| 项 | 建议 |
|----|------|
| 端点 | `https://api.deepseek.com/chat/completions`（OpenAI 兼容） |
| 认证 | `Authorization: Bearer`，密钥读 `.deepseekToken`（勿提交 Git） |
| 模型 | 默认 `deepseek-v4-pro`（质量优先；可用 `--model deepseek-v4-flash` 降本） |
| 参数 | `response_format` 若支持 JSON mode 可开启；`temperature` 偏低（如 0–0.3） |

### 5.2 解析流水线

```
raw assistant content
    → strip ```json fences if present
    → json.loads
    → 校验 pr_id == target_id
    → 可选：preflight 同款键路径 / 类型检查
    → 写入 output_pr_analysis/{pr_id}_analysis.json
```

失败时：保留 `output_pr_analysis/{pr_id}_analysis.raw.txt` 与错误日志，便于重试。

---

## 6. 目录与文件一览

| 路径 | 角色 | 读/写 |
|------|------|-------|
| `prompt.md` | 系统级 prompt | 读 |
| `schema.json` | 输出模板说明 | 读 |
| `{pr_id}_analysis.json`（根目录 6 份） | Few-shot 金标准 | 读 |
| `finaldatabase/…` | 源数据 | 读 |
| `.deepseekToken` | API key | 读（本地） |
| `output_pr_analysis/` | 批量/单次分析结果 | **写** |
| `preflight_pr_workflow.py` | 预检（API + JSON + prompt） | 可选 |
| `PR_workflow_preflight_report.md` | 预检报告 | 参考 |

---

## 7. 与体量策略的衔接

- 跑批前可用 `workflow_size_policy.py` 对 **待分析 PR** 打 tier（`workflow_auto` / `manual_xlarge` 等）。
- **B 组超大 PR**（`candidate.md` #5–7）不进入 6-shot，也不建议走本自动流；与本说明书「简单单路 workflow」并行存在，不冲突。

---

## 8. 下一步实现清单（脚本）

1. `build_payload(pr_id, mode="standard_no_patch")` — 统一 few-shot 与 target 的数据出口  
2. `assemble_prompt(...)` — 按 §4 拼接  
3. `call_deepseek(...)` — 调用 + 重试  
4. `parse_and_write_analysis(...)` — §5.2  
5. CLI：`python run_pr_analysis.py --pr-id 1234567890`（及可选 `--dry-run` 只写 prompt 不调用）

---

*枚举扩展策略已写入 `prompt.md` → Controlled Taxonomies 段首句；预检见 `PR_workflow_preflight_report.md`。*
