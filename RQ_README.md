# 研究问题定稿（RQ1–RQ4）

本文档是当前实证研究的 **RQ 定稿**，用于和导师对齐叙事，并把已完成分析（`FullAnalysis.md`、`full_analysis_distilled.csv`、`finaldatabase/per_pr/` 分析 JSON、能力边界 / 维护者实践 / 排查方式标注）串进同一套问题。

- **语料**：`finaldatabase` 分析 JSON，n = **1219**（merged 671 / closed 509 / open 39）。终态合并率 = 671 / 1180 = **56.9%**。
- **数字出处**：除非另注，均来自 `FullAnalysis.md` 或对 `full_analysis_distilled.csv` 的核对。
- **旧 RQ 对照**：早期划分见 `RQ_fewshot_guide.md`（过程/反模式、能力边界、维护者实践）。那些工作没有丢掉，映射关系见文末。

---

## RQ1 PR分布：AI 性能 PR 的生存现状如何？不同 Agent 表现差在哪？未合并是否等于被拒？

**RQ1.1** 总体分布与不同 Agent 的合并率表现如何  
支撑数据/材料事实：全库 n=1219，merged 671（55.0%）、closed 509（41.8%）、open 39（3.2%）；终态合并率 **56.9%**。Agent 分层（n≥30）：OpenAI_Codex 70.7%（639）、Claude_Code 55.3%、Cursor 50.5%、Copilot 34.7%、Devin 32.4%（225）。优化层面以 `application_service`（16.5%）、`build`（13.5%）、`frontend_ui`（11.2%）为主。上述为描述性差异，不直接等同于「模型能力」因果（任务类型、仓库、补丁规模可能混杂）。承接已完成的 Agent 合并率统计与 `optimization_layer` 分布。

**RQ1.2** Merged 的真实情况如何划分  
支撑数据/材料事实：合入不是单一路径。按 `outcome_reason` 归并：`small_scope_low_risk` 占 merged 的 **65.1%**（437），`after_review_iteration` **13.1%**（88），`without_formal_review` **11.5%**（77），other **10.3%**。行为上：merged 存活中位数约 **5 分钟**，`fast_merge` **78.7%**；**58.3%** 评论数为 0，**67.1%** 无 formal review；**82.4%** 无关联 Issue。建议将 Merged 划分为：低摩擦快合并（小范围 / 短命 / 无审）、经 review 迭代后合入、无 formal review 的自合并/作者合入、其他。原始高频标签：`merged_small_scope_low_risk`（388）、`merged_after_review_fix`（70）。

**RQ1.3** Closed 的真实情况如何划分  
支撑数据/材料事实：打破 Closed=Rejected。建议全库四分终态——**Merged**；**Waiting**=仍 open（39，3.2%）；**Silent abandonment**=关闭但无明确技术否决（现口径 `stale_or_inactivity` 27.5% + `closed_without_meaningful_review` 25.0%，粗映射约占 closed 一半）；**Real rejection**=有否决信号的关闭（现技术类合计仅 ~7.5% 被低估，因 `other` 占 closed 的 39.9%；粗映射约占 closed 的 1/4）。字段已具备：`outcome_reason`、`rejection_signals`（约 499/506 非空）、`primary_concern`、`blocking`（closed 中 87 条 true）、`review_count`（closed 中 75.6% 为 0）。精确比例需按该三分法重标后再锁定。Closed 原始 Top：`stale_no_review_engagement`（49）、`stale_inactivity`（32）、作者/自行关闭无审查类。

---

## RQ2 成功路径与评审注意力：为何大量性能 PR 能在极短周期低审查下合入？维护者为何放行为何不审？

**RQ2.1** 合并成功的 PR 呈现出哪些行为与特征？  
支撑数据/材料事实：主流是「短命、小步、低互动」，不是审完再合。merged 存活中位数约 **5 分钟**（closed 为 23.6 小时）；`fast_merge` 占 merged 的 **78.7%**（closed 为 0）；merged 中 **58.3%** 评论数为 0（中位数 0）；**67.1%** `review_count=0`；**82.4%** 无关联 Issue。终态合并率随存活时间下降：`<1h` **76.6%** → `1–24h` 57.2% → `1–7d` 40.0% → `>7d` **16.7%**。≤100 行终态合并率最高（**63.2%**）；merged 变更中位数 141 行。成功侧 `perf_focus` 偏 `constant_folding`、`compiler_optimization`、`cache`。

**RQ2.2** 维护者在缺乏深度审查时凭何放行？无人审更像质量门槛导致，还是由评审注意力/流程错配等原因导致？  
支撑数据/材料事实：放行更像「补丁小 + 读得懂」，不是 benchmark 过关。`boundary_tag=technical_stack` 终态合并率 **79.6%**。可观测排查方式以 `code_reading` 为主（全库 31.0%，merged 侧 225 条），`ci_auto` 仅 7.6%（merged 侧 48 条），`profiler` / `benchmark` / `load_test` 极少；64.5% 为 `unknown`，不能写成「靠 CI 放行」。材料普遍不足（`insufficient` 61.9%，`sufficient` 仅 2.1%，有 repro steps 4.5%），成功 PR 同样缺少可复现性能材料。无人审可合也可关：merged 67.1%、closed 75.6% 均无 formal review；`process` 边界 575 条、终态合并率仅 **35.7%**；大量 PR 无 linked issue，不在维护者既有任务队列中——卡住的经常是注意力与流程，而不是质量门槛。承接已完成的 `detection_method`、维护者实践与 process 边界标注。

---

## RQ3 失败模式与能力边界：真正被审/被拒的性能 PR 卡在哪里？AI 的能力边界如何体现？

**RQ3.1** 在真正被审过或被否决的子集中，核心失败类型是什么？  
支撑数据/材料事实：先限制样本（有 formal review / `blocking` / 有审查文本），不要把 509 条 closed 都当「被拒」。已有失败信号：closed 中 `review_comment_bucket` 为 `correctness_or_bug`（65）、`design_or_approach`（60）；`blocking=true` 87 条。类型包括：功能/正确性失败（例 #3098901968，CI 全平台挂、`functional_failure`）；设计/方案否决（例 #3102876964，maintainer 要求 rollback）；CI / Agent 修不完（例 #2976324699）；证据不足（`missing_benchmark` / `evidence_required`）。反模式两侧均为 `repeated_io` 最多（closed 36 vs merged 32），覆盖率低、区分弱，作伴随现象而非主拒因。静默 maintainer 关闭（例 #3097420465）需单独规则，避免与 abandonment 混淆。承接已完成的拒因摘要、review 分桶与反模式 taxonomy。

**RQ3.2** 证据生成、流程协作与同 PR 修复，分别暴露了哪些能力边界？  
支撑数据/材料事实：三条边界对应既有 `boundary_tag`。证据边界：`evidence_required` 终态合并率跌至 **12.5%**（32 条终态中仅 4 条 merged）；材料 `insufficient` 61.9%，`sufficient` 仅 2.1%。流程边界：`process` 终态合并率 **35.7%**，对比 `technical_stack` **79.6%**；closed 主导形态仍是 stale / 无审查。修复边界：`reject_close` 占全库 32.6%（closed 中 397 条），`revert` 仅 2 条；能在同 PR 内修复的仅 **12.1%**（148 条），其中人类主导 **55.4%**、AI 作者自行修 22.3%、人机协同 14.9%。`antipattern_in_fix` 仅 8 条（0.7%），记为稀有二次风险。承接已完成的能力边界、`reproducibility`、`regression_handling` 与 fix 主体启发式。

---

## RQ4 核心差异：合入与关闭差异在哪些维度？如何按路径提升合并率？

**RQ4.1** 成功合入与失败/搁置的 PR 在核心维度上有何显著差异？  
支撑数据/材料事实：寿命（merged 中位 ~5 min vs closed 23.6 h）；规模（≤100 行合并率 63.2%，中位 changes 141 vs 172；>10k 仍有 52.5%，故不是「越大越不能合」）；互动（merged 评论中位数 0，closed 为 2；高评论量并不对应更高合并率）；焦点（merged 偏常量折叠 / 编译优化 / cache，closed 偏 bundle size / 复杂构建 / code splitting）；层面（`compiler` / `compiler_backend` 约 80–85% 但 n 小，`runtime_vm` 仅 24.1%）。材料上 Closed 反而更常带数字声称（24.8% vs 13.0%）和 benchmark 表（6.3% vs 2.4%）——证据是难 PR 的门槛，不是成功 PR 的标配。

**RQ4.2** 合入和关闭的 PR 在 AI 能力边界上有哪些区别？是否存在 AI 能力边界影响合并结果的现象？  
支撑数据/材料事实：存在明显分层，但是描述性关联而非严格因果。`technical_stack` 608 条、终态合并率 **79.6%**；`process` 575 条、**35.7%**；`evidence_required` 35 条、**12.5%**。Merged 侧大量落在常规技术栈、小范围可读改动；Closed / 搁置更常落入流程边界（无人审、stale）或证据边界（维护者要求可复现材料但 PR 给不出）。优化层面亦有边界信号：编译器相关合入高、`runtime_vm` 合入低。成功侧 `perf_focus` 偏 Agent 可模板化的常量/缓存/编译优化；失败侧更常是包体积、复杂构建等需业务或全局上下文的改动。此节把既有 RQ3「能力边界归纳」接到合并结果上，而不是另起炉灶。

**RQ4.3** 针对现有缺陷，有哪些可操作的工具链或流程改进能提高合并率？  
支撑数据/材料事实：按两条路径写，避免单一药方。路径 A（低摩擦合入，对应 RQ1.2 / RQ2）——保持原子补丁、落在 `technical_stack`（缓存 / 常量 / 构建），降低维护者注意力成本；不把无 Issue 的主动优化默认丢进深度审队列；不要强制「所有 PR <100 行」。路径 B（需被认真审的难 PR，对应 RQ1.3 / RQ3）——补可复现材料（benchmark 表 + 复现步骤）以对准 `evidence_required` 12.5% 悬崖；Review 阶段强化消化 `CHANGES_REQUESTED`（`fix_in_pr` 中 55.4% 已是人类主导）；谨慎默认大范围控制流 / `runtime_vm`。加 benchmark 本身与更高合并率无简单正相关，改进应对准「被要求举证的难 PR」，而不是给快合并路径加表。

---

## 与已完成研究的对应关系

| 已完成工作 | 落在本定稿 |
|------------|------------|
| Agent / 全库合并率、优化层面分布 | RQ1.1 |
| Merged `outcome_reason` 归并、fast_merge、无 Issue | RQ1.2、RQ2.1 |
| Closed `outcome_reason`、`rejection_signals`、stale / 无审查 | RQ1.3 |
| 存活时间、变更规模、评论规模 | RQ2.1、RQ4.1 |
| `detection_method`（读码 / CI / profiler） | RQ2.2 |
| Review 分桶、拒因、反模式 | RQ3.1 |
| `boundary_tag`、`reproducibility`、`regression_handling`、fix 主体 | RQ3.2、RQ4.2 |
| `perf_focus` 正反对比、材料信号 | RQ4.1、RQ4.3 |
| 旧 `RQ_fewshot_guide.md` 的 RQ2（过程/失效）、RQ3（边界）、RQ4（维护者实践） | 分别并入本 RQ3.1、RQ3.2/RQ4.2、RQ2.2 |

## 方法边界（和导师对齐时主动说明）

1. `outcome_reason` 取值膨胀（约 510 个），RQ1.2 / RQ1.3 的精确百分比需按定稿分类重标；当前 `close_reason_group` 中 `other` 占 closed 的 39.9%，不能据此写成「技术性拒绝极少数」。
2. 标签来自 LLM 分析 JSON，不是 GitHub 官方关闭原因；`rejection_signals` 可抽样人工核对。
3. Agent 差异、benchmark 与合并率、边界与合并率均为**相关不是因果**。
4. `fix_in_pr` 主体与 `antipattern_in_fix`（8 例）是启发式，写入论文前建议抽检。
5. `waiting` 对应快照时仍 `open` 的 PR，不要塞进 Closed。
