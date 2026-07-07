# Few-shot 候选 PR 选取说明

> 数据来源：`finaldatabase/`（1221 条 Agent 性能 PR，截至 2026-06-21）  
> 选取目标：6 条代表性 PR，用于毕业设计 few-shot 标注与 RQ2/RQ4 试点分析

---

## 选取标准

| 维度 | 要求 | 实现方式 |
|------|------|----------|
| 总量 | 6 条 | 见下表 |
| 合并结果 | merged 3 条 / closed（未合并）3 条 | 严格 3:3 |
| 变更规模（4 条） | 代码变更量、review 数或 comment 数接近全库均值 | 以 `auxiliary/` 聚合指标与全库均值比对；因 `total_changes` 分布极度右偏（均值 1956 vs 中位数 156），"接近平均"同时参考 **中位数区间** 与 **review/comment 均值** |
| 高活动（2 条） | 代码修改与审查明显偏多 | 选取 `activity_score`（changes + review×50 + review_comment×20 + comment×10）Top 档，且同时具备大量文件变更与多轮 review |

### 全库基线（merged + closed，n=1172）

| 指标 | 均值 | 中位数 | p75 |
|------|------|--------|-----|
| commit 数 | 3.47 | 1 | 4 |
| 改动文件数 | 20.81 | 4 | 9 |
| 代码变更行数 (changes) | 1956 | 156 | 636 |
| review 数 | 1.16 | 0 | 1 |
| 行内 review comment 数 | 1.21 | 0 | 0 |
| PR comment 数 | 1.62 | 0 | 2 |

---

## 候选 PR 一览

### A 组：接近平均水平（4 条，2 merged + 2 closed）

#### 1. `3228424652` — merged · Cursor

| 字段 | 值 |
|------|-----|
| 仓库 | [browser-use/browser-use](https://github.com/browser-use/browser-use) |
| 标题 | Limit wait action to 10 seconds |
| Agent | Cursor |
| Topic | 0_workflow_jobs_job_ci |
| 变更 | 4 commits · 9 files · **79 changes** |
| 协作 | 1 review · 1 review comment · 2 comments |

**选取理由**：review/comment 数量与全库均值几乎一致（0.86–1.24×）；变更规模偏小但处于中位数附近，代表"小步快改、轻量审查即合并"的典型成功路径。性能点明确（限制 wait 动作最长 10 秒，防止 Agent 操作阻塞过久）。

---

#### 2. `3074351366` — merged · Devin

| 字段 | 值 |
|------|-----|
| 仓库 | [mendableai/firecrawl](https://github.com/mendableai/firecrawl) |
| 标题 | FIR-2006: Fix maxUrls and timeLimit parameters in Deep Research API |
| Agent | Devin |
| Topic | 45_firecrawl_scrape_scraping_authority |
| 变更 | 6 commits · 3 files · **1115 changes** |
| 协作 | 1 review · 1 review comment · 1 comment |

**选取理由**：commit/review/comment 均接近均值（0.86–1.44×）；变更行数约为均值的 0.57×、中位数的 7×，属于中等规模功能修复。修复 Deep Research API 的 `maxUrls`/`timeLimit` 未生效问题，兼具**性能/资源控制**与**正确性**语义，适合 RQ2 拒因/合并对比。

---

#### 3. `3194284966` — closed · Cursor

| 字段 | 值 |
|------|-----|
| 仓库 | [vercel/turborepo](https://github.com/vercel/turborepo) |
| 标题 | perf: improve hashing performance for manual path |
| Agent | Cursor |
| Topic | 33_ahash_uint_methods_fnv |
| 变更 | 5 commits · 2 files · **230 changes** |
| 协作 | 2 reviews · 1 review comment · 2 comments |

**选取理由**：review 数（1.73×）、comment 数（1.24×）略高于均值；变更规模适中。维护者以 `CHANGES_REQUESTED` 明确要求使用 `BufReader` 并**补充 benchmark 验证**，作者随后表示"关闭直至有真实 benchmark"——是 RQ2 **缺少性能证据** 拒因与 RQ4 **材料可复现性不足** 的教科书式案例。

---

#### 4. `3145702280` — closed · Copilot

| 字段 | 值 |
|------|-----|
| 仓库 | [polkadot-cloud/polkadot-staking-dashboard](https://github.com/polkadot-cloud/polkadot-staking-dashboard) |
| 标题 | Move BarChart to ui-graphs package with SCSS modules and bigint support |
| Agent | Copilot |
| Topic | 24_bundle_css_components_splitting |
| 变更 | 4 commits · 22 files · **815 changes** |
| 协作 | 0 review · 0 review comment · 1 comment |

**选取理由**：commit 数、文件数、变更行数均接近均值区间（0.42–1.15×）；无 formal review 但存在 package 拆分与 bigint 支持改动，代表**重构类性能 PR 在未获审查文本时即被关闭**的情形，可对比有 review 的 closed 案例（#3）。

---

### B 组：高变更 + 高审查（2 条，1 merged + 1 closed）

#### 5. `3226043406` — closed · Claude_Code

| 字段 | 值 |
|------|-----|
| 仓库 | [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) |
| 标题 | feat: lazy load CLI command actions for improved startup performance |
| Agent | Claude_Code |
| Topic | 11_constructors_claude_parsing_startup |
| 变更 | 24 commits · 392 files · **158,472 changes** |
| 协作 | 11 reviews · 28 review comments · 6 comments |

**选取理由**：全库 `activity_score` 最高档。声称 CLI 启动性能提升 15.7%，但改动面极广（动态 import 重构全命令模块），review 中密集出现 **Bug / CLI 选项不匹配 / 回归** 等行内评论；维护者评论"信息太多无法测试"。适合标注 **范围过大、正确性争议导致关闭** 的高活动失败案例。

---

#### 6. `3119512382` — merged · Copilot

| 字段 | 值 |
|------|-----|
| 仓库 | [Azure/azure-sdk-for-java](https://github.com/Azure/azure-sdk-for-java) |
| 标题 | Remove unnecessary Maven plugins from azure-openrewrite pom.xml |
| Agent | Copilot |
| Topic | 0_workflow_jobs_job_ci |
| 变更 | 17 commits · 1417 files · **98,479 changes** |
| 协作 | 18 reviews · 16 review comments · 13 comments |

**选取理由**：变更规模与审查强度均处全库 Top（changes 50×均值，review 16×均值），但**最终合并**。通过逐个移除 Maven 插件并验证 `mvn clean install` 的系统性方法，review 中维护者纠正了"不可删除 compiler 插件"——代表 **大规模构建优化 PR 在多轮人机协作后成功落地** 的对照样本，与 #5 形成"同量级活动、不同结局"配对。

---

## 汇总矩阵

| # | PR ID | 分组 | 结果 | Agent | changes | reviews | comments | 代表性 |
|---|-------|------|------|-------|---------|---------|----------|--------|
| 1 | 3228424652 | 平均 | merged | Cursor | 79 | 1 | 2 | 小改动轻审查即合并 |
| 2 | 3074351366 | 平均 | merged | Devin | 1115 | 1 | 1 | 中等 API 资源限制修复 |
| 3 | 3194284966 | 平均 | closed | Cursor | 230 | 2 | 2 | 缺 benchmark 被拒 |
| 4 | 3145702280 | 平均 | closed | Copilot | 815 | 0 | 1 | 重构无审查文本即关闭 |
| 5 | 3226043406 | 高活动 | closed | Claude_Code | 158472 | 11 | 6 | 大范围 lazy-load 引发回归争议 |
| 6 | 3119512382 | 高活动 | merged | Copilot | 98479 | 18 | 13 | 大规模构建优化多轮协作后合并 |

**Agent 覆盖**：Cursor(2) · Devin(1) · Copilot(2) · Claude_Code(1)  
**合并结果**：merged 3 / closed 3 ✓

---

## 后续 few-shot 标注建议

1. **RQ2 优先字段**：`outcome_reason`、`review_dimensions`、`inefficiency_antipattern`；#3、#5 已有明确拒因文本。  
2. **RQ4 优先字段**：`detection_method`、`reproducibility`、`regression_handling`；#3（benchmark 缺失）、#5（测试不可行）、#6（逐插件验证）形成对比。  
3. **配对分析**：#5 vs #6（同高活动、异结局）；#3 vs #4（均有/无 review 的 closed 对照）。  
4. 明细数据路径：`finaldatabase/per_pr/{pr_id}/` 及各 `auxiliary/*.parquet`。

---

*生成方式：基于 `finaldatabase/auxiliary/` 聚合指标与 `pr_master/perf_prs_expanded_final.csv` 主表筛选，2026-07-07。*
