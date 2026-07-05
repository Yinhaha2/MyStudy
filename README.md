# AIDev-pop 性能类 PR 子研究（MyStudy）

本目录在 [AIDev](https://huggingface.co/datasets/hao-li/AIDev) 的 **AIDev-pop**（`>100 stars` 仓库）子集上，抽取 `pr_task_type` / `human_pr_task_type` 中 **`type == perf`** 的 PR，并与原文 `analysis/productivity.ipynb` 的 **合并率（merged_pct）** 口径对齐，做描述统计与可视化。

## 数据集之间的关联（核心外键）

| 表 | 说明 | 与 PR 的关联 |
| --- | --- | --- |
| `pull_request.parquet` | 各 Agent 在 AIDev-pop 中的 PR | 主表：`id` |
| `pr_task_type.parquet` | 对 Agent PR 的 Conventional-Commit 风格 LLM 分类 | `id`（与 `pull_request.id` 对齐）；列 `type` 含 `perf` |
| `human_pull_request.parquet` | 人类开发者 PR **对照样本**（见下方“可比性”说明） | 主表：`id`；`agent` 恒为 `Human` |
| `human_pr_task_type.parquet` | 人类 PR 的任务类型 | `id`；`type` |
| `pr_reviews.parquet` | PR 评审（含 `APPROVED` / `CHANGES_REQUESTED` 等） | `pr_id` → `pull_request.id` / `human_pull_request.id` |
| `pr_review_comments_v2.parquet` | 行内评审评论 | `pull_request_review_id` → `pr_reviews.id`，再得到 `pr_id` |
| `pr_comments.parquet` | Issue 线程评论 | `pr_id` |

更完整的字段说明见仓库内 `AIDev/data_table.md` 与 Hugging Face 数据集文档。

## “性能 PR” 的操作定义

- **来源**：数据集已发布的 **`pr_task_type.type == "perf"`**（性能优化类变更），与 `analysis/classify_pr.py` 中 Conventional Commits 的 `perf` 定义一致。
- **说明**：这是 **任务类型标签**，不是 GitHub 上名为 “performance” 的 label；若需按标题关键词再筛一遍，可在 `performance_pr_analysis.py` 中扩展规则。

## 指标口径（与 `productivity.ipynb` 一致）

对每条 PR 定义 `status`：

- `open`：`state == "open"`
- `merged`：`merged_at` 非空
- `closed`：其余（已关闭但未合并）

**合并率 merged_pct**（默认报告）：`100 * mean(status == "merged")`，**分母含仍处于 open 的 PR**（与 `productivity.ipynb` 中 `analyze_agent` 一致）。

另报告 **终态合并率**（补充）：仅 `state == "closed"` 的 PR 中，`merged_at` 非空的比例（避免 open 拉低分母 interpretability）。

## “未合并原因” 说明（重要限制）

GitHub API 汇总的表中 **通常没有单一的 “关闭原因” 字段**。本研究脚本的策略是：

1. 优先取该 PR 在 `pr_reviews` 中 **`state == CHANGES_REQUESTED`** 的评审正文（`body`）摘要；
2. 若无，则拼接行内评论（`pr_review_comments_v2` 经 `pr_reviews` 关联到 `pr_id`）与 `pr_comments` 的前若干条正文做 **关键词粗分桶**（测试/正确性/设计讨论/性能相关/构建与 CI/无可用文本等）。

因此：**“原因”是审查与讨论信号的近似，不是官方关闭理由**；许多 closed PR 在数据集中 **没有任何评审/评论行**，会被记为 `no_review_text_in_dataset`。

## Human 与 Agent 子集的可比性（方法提醒）

- **Agent PR（`pull_request.parquet`）**：AIDev-pop，对应 **stars > 100** 的仓库（见 `AIDev/README.md`）。
- **Human PR（`human_pull_request.parquet`）**：README 写明来自 **与 Agent 相同挖掘流程** 下、但限定在 **stars > 500** 仓库中抽样的对照集。

因此两者 **不是同一母体上的平行样本**；本仓库脚本给出的 Agent vs Human 通过率对比应视为 **描述性**，正式论文式对比建议再按 `repo_id` / `repo_url` 做子总体对齐。

## 输出文件：`all_perfPR.json`

- **路径**：`MyStudy/output/all_perfPR.json`
- **内容**：全部 `perf` PR（AIDev-pop Agent + Human 对照集），结构为 `{ "meta": {...}, "pull_requests": [ {...}, ... ] }`。
- **`pull_requests`**：每条记录 **键名完全一致**（并集字段），某子集不存在的列填 `null`；`subset` 取 `AIDev_pop_agent` 或 `human_pull_request_baseline`，`classification_table` 标明所用分类表；`all_perfPR_row_1based` 为该文件中的全局序号。

## 全量 Agent 表（`all_pull_request.parquet`）流水线

AIDev **官方 LLM `pr_task_type` 标签仅覆盖约 33596 条 AIDev-pop PR**；全集 **93万+行** 无法在不做新分类的前提下逐个得到 `perf` 语义标签。

脚本 **`performance_pr_analysis_all.py`** 会：

1. 以 **`all_pull_request.parquet`** 为 Agent 全集，计算 **逐 Agent** 的总体合并率等；
2. **左联接** `pr_task_type.parquet`：对已覆盖的 Pop PR 填入 `type` / `reason` / `confidence`，从而得到与原 `output/` **完全相同的 340 条 LLM perf**（列来自全集表，内容与 pop 等价）；
3. 在全集标题上套用 **`analysis/classify_pr.py` Stage-1** 的 `perf(...):` 正则，导出 **`performance_prs_agents_title_regex.parquet`**（条数远低于 LLM perf，但能覆盖未打标签的行）；
4. Human 部分仍仅用 **`human_pull_request.parquet`**（论文对照集）；**不写** `all_perfPR.json`。

```bash
cd MyStudy
python performance_pr_analysis_all.py
python performance_pr_analysis_all.py --local
```

产物对齐 `output/` 的命名习惯，写入 **`output_all/`**（另含 `figures/performance_pr_dashboard_all.png`、`performance_prs_agents_title_regex.parquet`）。

## 如何复现

在项目根目录已安装依赖的前提下：

```bash
cd MyStudy
python performance_pr_analysis.py
```

默认从 `hf://datasets/hao-li/AIDev/*.parquet` 流式读取。若你已按 `analysis/helper.py` 将 Parquet 下载到 `AIDev/`，可：

```bash
python performance_pr_analysis.py --local
```

输出写入本目录下 `output/`：`performance_prs_*.parquet`、`all_perfPR.json`（全部 perf PR，JSON 逐项对齐字段）、`summary_metrics.json`、`rejection_signal_examples.json`、`figures/` 等。

## 引用

- 数据集与论文：见 `AIDev/README.md`（arXiv: 2507.15003, 2602.09185）及官方复现笔记本 `analysis/productivity.ipynb`。



databasephase1 是我们基于论文 How Do Agentic AI Systems Address Performance Optimizations? 与 Hugging Face AIDev-pop 数据集构建的性能 PR 研究库：以论文最终扩容集 1,221 条 Agent 生成的性能相关 Pull Request 为核心（由 LLM 初筛 1,160 条与官方 pr_task_type=perf 补入的 61 条合并而成），主表 pr_master/perf_prs_expanded_final 提供每条 PR 的元数据（标题/正文、Agent、状态与时间、仓库链接）、合并结果（约 668 已合并、406 关闭未合并、147 仍 open）、检测来源、AIDev 任务类型分类，以及 BERTopic 主题（52 个 topic + 1 个 outlier，可进一步映射到论文人工归纳的 10 大类）；classification/ 存放主题与分类相关表，paper_source_copy/ 保留论文原始 CSV 副本。Commit、review、comment、timeline、issue 等过程性细节不在主表一行内，而是存放在 auxiliary/ 的 1:N 关联分表中，统一通过 pr_id（= 主表 id） 联接——其中 timeline 13,910 行（1,221 条 PR 全覆盖，平均约 11 个事件/PR）、commit 摘要 4,282 行、文件级变更 31,510 行、PR 讨论 comment 1,968 行、review 1,422 行、行内评审 comment 1,518 行、关联 issue 217 行（对应 209 个 issue 实体），并附带 447 个相关仓库元数据；因此该库既可用于主题/合并率等宏观分析，也可下钻到单条 PR 的完整协作与变更过程。