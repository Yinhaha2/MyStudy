# Few-shot 候选 PR 选取说明

> 数据来源：`finaldatabase/`（1221 条 Agent 性能 PR，截至 2026-06-21）  
> 选取目标：8 条代表性 PR（A 组 4 + B 组 2 + C 组 2），用于毕业设计 few-shot 标注与 RQ2/RQ4 试点分析；**实际构建 few-shot 优先使用 A + C 组**

---

## 选取标准

| 维度 | 要求 | 实现方式 |
|------|------|----------|
| 总量 | 8 条（A 4 + B 2 + C 2） | 见下表 |
| 合并结果 | merged 4 条 / closed 4 条 | A+C 组各 2:2；B 组 1:1 作重量级参照 |
| 变更规模（A 组 4 条） | 代码变更量、review 数或 comment 数接近全库均值 | 以 `auxiliary/` 聚合指标与全库均值比对；因 `total_changes` 分布极度右偏（均值 1956 vs 中位数 156），"接近平均"同时参考 **中位数区间** 与 **review/comment 均值** |
| 适度增量（C 组 2 条） | 变更量高于 A 组约 50%–100%，但不重量级 | 约为 p75 的 **1.5–2×**（约 950–1270 changes）；文件数 ≤30、commit ≤12；**有关联 issue**；**1–2 轮有实质内容的 review**（`CHANGES_REQUESTED` / `APPROVED` / 长文 `COMMENTED`） |
| 高活动参照（B 组 2 条） | 代码修改与审查明显偏多（保留备查，非 few-shot 首选） | 选取 `activity_score` Top 档；变更达数万行、review 十余轮，适合作为"极端案例"对照 |

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

> **说明**：B 组保留为"高活动极端案例"备查；日常 few-shot 构建建议跳过，避免标注负担过重。

---

### C 组：适度增量 · 优质轻量（2 条，1 merged + 1 closed）⭐ few-shot 优先

> 选取逻辑：在关联 issue + 有实质 review 的交集中，取变更量约为全库 **p75 的 1.5–2×**（约 950–1270 行），远低于 B 组（10 万行级），但信息密度高、适合人工标注与 LLM few-shot 示范。

#### 7. `3125029980` — merged · Copilot

| 字段 | 值 |
|------|-----|
| 仓库 | [nearai/nearai](https://github.com/nearai/nearai) |
| 标题 | Implement asynchronous API calls for file and message creation in environment.py |
| Agent | Copilot |
| Topic | 19_knowledge_deepseek_crew_cache |
| 关联 Issue | body 链接 issue（`source: body`） |
| 变更 | 6 commits · 1 file · **959 changes**（≈ p75 的 1.5×） |
| 协作 | 3 reviews · 0 review comment · 2 comments |

**选取理由**：典型 **"一轮 CR → 按意见修改 → 合并"** 路径。维护者 `CHANGES_REQUESTED`："Don't do async execution in completions_and_run_tools()"，作者撤回有问题的异步路径后获 `APPROVED`；评论给出可复现的性能数据（**~8s 降至 4–5s**）。单文件集中改动，体量适中，非常适合作为 **合并成功 + 性能证据可引用** 的 few-shot 正例。

---

#### 8. `3022909076` — closed · Devin

| 字段 | 值 |
|------|-----|
| 仓库 | [risingwavelabs/risingwave](https://github.com/risingwavelabs/risingwave) |
| 标题 | feat: improve DAG visualization in RisingWave UI |
| Agent | Devin |
| Topic | 2_hydration_species_component_children |
| 关联 Issue | body 链接 issue（`source: body`） |
| 变更 | 3 commits · 5 files · **1213 changes**（≈ p75 的 1.9×） |
| 协作 | 2 reviews · 0 review comment · 2 comments |

**选取理由**：将 D3/dagre 替换为 ReactFlow 以改善大型 DAG 可读性，首轮 review 有完整 PR Overview；维护者随后以截图回复 **"还是不 work"** 并 👎，最终因 **7 天不活跃** 关闭。变更与审查强度均适度，拒因清晰（**功能未达预期**），适合作为 **有关联 issue、有 review 往返、但未合并** 的 few-shot 负例，与 #7 形成鲜明对照。

---

## 汇总矩阵

| # | PR ID | 分组 | 结果 | Agent | changes | reviews | comments | 代表性 |
|---|-------|------|------|-------|---------|---------|----------|--------|
| 1 | 3228424652 | A·平均 | merged | Cursor | 79 | 1 | 2 | 小改动轻审查即合并 |
| 2 | 3074351366 | A·平均 | merged | Devin | 1115 | 1 | 1 | 中等 API 资源限制修复 |
| 3 | 3194284966 | A·平均 | closed | Cursor | 230 | 2 | 2 | 缺 benchmark 被拒 |
| 4 | 3145702280 | A·平均 | closed | Copilot | 815 | 0 | 1 | 重构无审查文本即关闭 |
| 5 | 3226043406 | B·高活动 | closed | Claude_Code | 158472 | 11 | 6 | 大范围 lazy-load 引发回归争议 |
| 6 | 3119512382 | B·高活动 | merged | Copilot | 98479 | 18 | 13 | 大规模构建优化多轮协作后合并 |
| 7 | 3125029980 | C·适度 | merged | Copilot | 959 | 3 | 2 | CR 后修正，8s→4-5s 有数据 |
| 8 | 3022909076 | C·适度 | closed | Devin | 1213 | 2 | 2 | DAG 改版未达预期，截图拒 |

**Agent 覆盖**：Cursor(2) · Devin(2) · Copilot(3) · Claude_Code(1)  
**合并结果**：merged 4 / closed 4 ✓  
**Few-shot 推荐**：优先 #1–4 + #7–8（A+C）；#5–6 仅作极端对照备查

---

## 后续 few-shot 标注建议

1. **RQ2 优先字段**：`outcome_reason`、`review_dimensions`、`inefficiency_antipattern`；#3、#8 已有明确拒因文本；#7 有 CR 往返。  
2. **RQ4 优先字段**：`detection_method`、`reproducibility`、`regression_handling`；#3（benchmark 缺失）、#7（实测耗时对比）、#8（截图验证失败）形成对比。  
3. **配对分析**：#7 vs #8（同 C 组适度增量、异结局）；#3 vs #4（有/无 review 的 closed 对照）；#5 vs #6（B 组极端高活动对照，可选）。  
4. **构建顺序建议**：先标注 C 组（#7–8）定模板 → 扩至 A 组（#1–4）→ 视需要参考 B 组。  
5. 明细数据路径：`finaldatabase/per_pr/{pr_id}/` 及各 `auxiliary/*.parquet`。

---

*生成方式：基于 `finaldatabase/auxiliary/` 聚合指标与 `pr_master/perf_prs_expanded_final.csv` 主表筛选；C 组于 2026-07-07 增补（适度增量 + issue + 优质 review，非重量级）。*
