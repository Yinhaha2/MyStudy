# Full Analysis — Agent Performance PR Corpus

> 生成自 `finaldatabase/per_pr/{pr_id}/{pr_id}_analysis.json`（及 6 条根目录 few-shot 金标）；样本量 **1219** 条，与主表对齐。
> 配套宽表：`full_analysis_distilled.csv`（由 `python3 generate_full_analysis.py` 再生成）。

---

## 1. 合并结果总体分布

| 状态 | 数量 | 占比 |
|------|------|------|
| merged | 671 | 55.0% |
| closed（终态未合并） | 509 | 41.8% |
| open（仍开放） | 39 | 3.2% |

- **全库合并率**（含 open）：55.0%（671/1219）
- **终态合并率**（仅 merged + closed，n=1180）：**56.9%**

说明：closed 在本数据集中指 GitHub 上已关闭但未合并的 PR，不等同于「审查通过」；open 为截至数据快照仍开放。

---

## 2. 通过（merged）与不通过（closed）的主要原因

依据 `perf_labels.outcome_reason` 归并（分析 JSON 中的归纳标签，非原始 review 原文）。

### 2.1 Merged — 归并后的主要原因

| 归并类别 | 数量 | 占 merged 比例 |
|----------|------|----------------|
| small_scope_low_risk | 437 | 65.1% |
| after_review_iteration | 88 | 13.1% |
| without_formal_review | 77 | 11.5% |
| other | 69 | 10.3% |

**解读（描述性，非因果）**：绝大多数合并 PR 被标为 **小范围、低风险**（`small_scope_low_risk`）；其次为 **经 review 迭代后合并**（`after_review_iteration`）；另有约一成合并路径 **缺乏 formal review 信号**（`without_formal_review`）。

Merged `outcome_reason` 原始 Top 5：

| outcome_reason | 数量 |
|----------------|------|
| `merged_small_scope_low_risk` | 388 |
| `merged_after_review_fix` | 70 |
| `merged_small_scope_no_review` | 18 |
| `merged_self_merge_no_review` | 7 |
| `merged_small_scope_self_merge` | 6 |

### 2.2 Closed — 归并后的主要原因

| 归并类别 | 数量 | 占 closed 比例 |
|----------|------|----------------|
| other | 203 | 39.9% |
| stale_or_inactivity | 140 | 27.5% |
| closed_without_meaningful_review | 127 | 25.0% |
| functional_or_correctness | 24 | 4.7% |
| missing_evidence_or_benchmark | 11 | 2.2% |
| performance_regression_or_no_gain | 3 | 0.6% |
| scope_too_large | 1 | 0.2% |

**解读**：closed 的 dominant 模式是 **流程性关闭**（stale / 无审查互动 / 作者自行关闭），而非单一「性能不达标」标签；在 **有 review 文本** 的子集中，`functional_failure`、`correctness_edge_case` 等才会更突出。

Closed `outcome_reason` 原始 Top 5：

| outcome_reason | 数量 |
|----------------|------|
| `stale_no_review_engagement` | 49 |
| `stale_inactivity` | 32 |
| `closed_by_author_no_review` | 13 |
| `closed_no_review_engagement` | 12 |
| `self_closed_no_review` | 12 |

---

## 3. 合并结果与变更规模 / 评论规模

### 3.1 代码变更量（changes）

| changes 分箱 | 终态 PR 数 | 合并率 |
|-------------|-----------|--------|
| ≤100 | 476 | 63.2% |
| 101–500 | 349 | 52.4% |
| 501–2k | 195 | 54.4% |
| 2k–10k | 107 | 56.1% |
| >10k | 40 | 52.5% |

- merged 中位数 changes：**141**；closed 中位数：**172**
- **未发现「修改越多越容易合并」**：≤100 行合并率最高（约 63%），>10k 行合并率约 52%。

### 3.2 评论规模（review comment + PR comment）

| comment 分箱 | 终态 PR 数 | 合并率 |
|-------------|-----------|--------|
| 0 | 161 | 47.8% |
| 1–2 | 202 | 35.1% |
| 3–9 | 197 | 47.7% |
| ≥10 | 75 | 50.7% |

- merged 评论总数中位数：**0**；closed：**2**
- 评论极少（0 条）的 PR 合并率反而较高，与「无 review 快速合并」路径一致；高评论量并不对应更高合并率。

---

## 4. 合并结果与 PR 存活时间

| 存活时间 | 终态 PR 数 | 合并率 |
|----------|-----------|--------|
| <1h | 573 | 76.6% |
| 1–24h | 236 | 57.2% |
| 1–7d | 180 | 40.0% |
| >7d | 150 | 16.7% |

- merged 存活时间中位数：**0.077 小时**（约 5 分钟）
- closed 存活时间中位数：**23.6 小时**（约 1.0 天）
- merged 中 `fast_merge=true` 占比：**78.7%**；closed 为 0%

**关联描述**：合并 PR 显著更「短命」；长寿命 closed 多与 stale / 无互动相关，而非慢审后拒绝。

---

## 5. 性能优化与性能问题出现的层面

### 5.1 优化所在层面（`optimization_layer`，Top 12）

| optimization_layer | 数量 | 占比 |
|-------------------|------|------|
| `application_service` | 201 | 16.5% |
| `build` | 165 | 13.5% |
| `frontend_ui` | 137 | 11.2% |
| `runtime_library` | 122 | 10.0% |
| `application_control_flow` | 87 | 7.1% |
| `compiler` | 45 | 3.7% |
| `infrastructure` | 35 | 2.9% |
| `runtime_vm` | 29 | 2.4% |
| `compiler_backend` | 26 | 2.1% |
| `compiler_optimization` | 15 | 1.2% |
| `compiler_codegen` | 14 | 1.1% |
| `test_infrastructure` | 12 | 1.0% |

### 5.2 低效/问题反模式（`inefficiency_antipattern` ≠ none）

**Merged 侧 Top：** `repeated_io`(32), `nested_loop`(9), `unknown`(4), `lock_misuse`(2), `main_thread_blocking`(2), `memory_leak`(2)

**Closed 侧 Top：** `repeated_io`(36), `nested_loop`(5), `lock_misuse`(3), `repeated_computation`(2), `redundant_computation`(2), `blocking_io`(2)

两侧出现最多的均为 `repeated_io`；closed 侧 `repeated_io` 略多。整体反模式标签覆盖率有限（多数 PR 为 `none`）。

---

## 6. 维护者识别性能问题的方式

字段：`perf_labels.detection_method`（可多选）。

| detection_method | 出现 PR 数 | 占全库 |
|------------------|-----------|--------|
| `unknown` | 786 | 64.5% |
| `code_reading` | 378 | 31.0% |
| `ci_auto` | 93 | 7.6% |
| `manual_testing` | 18 | 1.5% |
| `manual_test` | 8 | 0.7% |
| `benchmark` | 6 | 0.5% |
| `load_test` | 5 | 0.4% |
| `(empty)` | 4 | 0.3% |
| `profiler` | 3 | 0.2% |
| `unit_test` | 3 | 0.2% |

- **最主要方式**：在可识别时以 **`code_reading`（静态读码审查）** 为主（约 378 条 PR 至少出现一次）。
- 其次为 **`ci_auto`**（约 93 条）；`profiler`、`load_test`、`benchmark` 单独出现极少。
- 约 **786 条** 标为 `unknown`，与全库 **~71% 无 formal review** 一致——识别方式大量不可观测。

---

## 7. PR 材料能否支撑性能缺陷复现

| reproducibility | 数量 | 占比 |
|-----------------|------|------|
| `insufficient` | 754 | 61.9% |
| `partial` | 240 | 19.7% |
| `unknown` | 200 | 16.4% |
| `sufficient` | 25 | 2.1% |

辅助信号：
- `body_has_repro_steps=true`：**55**（4.5%）
- `body_has_benchmark_table=true`：**51**
- `material_reproducibility=sufficient`：**25**

**结论（材料维度）**：绝大多数 PR 的材料被标为 **insufficient 或 partial**；仅约 **2%** 达到 sufficient。

---

## 8. 性能退化 / 审查问题的处置方式

| regression_handling | 数量 | 占比 |
|---------------------|------|------|
| `not_applicable` | 626 | 51.4% |
| `reject_close` | 397 | 32.6% |
| `fix_in_pr` | 148 | 12.1% |
| `unknown` | 20 | 1.6% |
| `ignore` | 18 | 1.5% |
| `revert` | 2 | 0.2% |
| `fix_followup` | 2 | 0.2% |
| `close_no_merge` | 1 | 0.1% |
| `fix_pending` | 1 | 0.1% |
| `abandon` | 1 | 0.1% |
| `recreated_in_new_pr` | 1 | 0.1% |
| `closed_no_merge` | 1 | 0.1% |
| `draft_converted_no_fix` | 1 | 0.1% |

- **`not_applicable`**（51.4%）：无明确退化处置语境，多为直接合并或流程性关闭。
- **`reject_close`**（32.6%）：以拒绝/关闭为主，多见于 closed。
- **`fix_in_pr`**（148 条）：同一 PR 内修复；`revert` 仅 **2** 条。

### 8.1 `fix_in_pr` 的修复主体（启发式文本分类，非 ground truth）

| 修复模式 | 数量 | 占 fix_in_pr |
|----------|------|--------------|
| human_led_or_requested | 82 | 55.4% |
| ai_author_in_pr | 33 | 22.3% |
| human_ai_collaborative | 22 | 14.9% |
| unclear | 11 | 7.4% |

- 数据集 **每条 PR 仅一个 `meta.agent`**，无结构化 multi-agent 字段；文本中偶发多 bot 审查，但 **无法系统统计多 Agent 协同修复比例**。
- 修复引入新问题信号：`antipattern_in_fix` 非 none 共 **8** 条（0.7%），仅供参考。

---

## 9. 与 Issue 的关联

- `linked_issue_count > 0`：**215** 条（**17.6%**）
- 无关联 issue：**1004** 条（**82.4%**）

多数 Agent 性能 PR **并非**明确为修复某一 linked issue 而开；性能优化常直接由 Agent 发起。

---

## 10. 通过率、问题分布与能力边界（描述性归纳）

- **AI 性能 PR 终态合并率：约 56.9%**（671/1180）。

### 10.1 合并成功侧常见的性能关注点（`perf_focus` Top，merged）

`constant_folding`(23), `compiler_optimization`(21), `benchmark_infrastructure`(11), `cache`(8), `lazy_loading`(7), `compile_time_optimization`(7), `caching`(6), `compiler_codegen`(6)

### 10.2 未合并侧常见的性能关注点（`perf_focus` Top，closed）

`bundle_size_reduction`(12), `constant_folding`(10), `cache`(9), `build_performance`(7), `caching`(6), `lazy_load`(6), `code_splitting`(6), `compiler_optimization`(6)

### 10.3 `boundary_tag` 分布

| boundary_tag | 数量 |
|--------------|------|
| `technical_stack` | 608 |
| `process` | 575 |
| `evidence_required` | 35 |
| `unknown` | 1 |

### 10.4 可能的特长点与边界点（基于标签分布，待人工验证）

**特长点（合并侧信号）**
- 小范围、控制流/编译器常量折叠、构建与缓存类改动，在 **低审查摩擦** 路径下易合并。
- `technical_stack` 边界占多数（608 条），表示问题落在 Agent 可处理的常规技术栈层级。

**边界点（未合并或高风险信号）**
- 流程性关闭（stale / 无 review）占比极高，掩盖了真实「性能否决」比例。
- `evidence_required` 类边界（35 条）与 `missing_benchmark` / insufficient reproducibility 呼应。
- 大范围改动（>10k changes）合并不占优；`repeated_io` 等反模式在 closed 略多。
- 性能效果缺乏可复现材料时，审查难以闭环。

---

## 11. Agent 分层合并率（n≥30）

| Agent | PR 数 | 合并率 |
|-------|-------|--------|
| OpenAI_Codex | 639 | 70.7% |
| Claude_Code | 38 | 55.3% |
| Cursor | 95 | 50.5% |
| Copilot | 222 | 34.7% |
| Devin | 225 | 32.4% |

---

## 12. 数据与方法说明

- 统计基于分析 JSON 中的 **标签与叙述字段**，不是对 GitHub 原始事件的重新跑批。
- `outcome_reason` 等标签由 LLM 分析生成，存在 **同义标签膨胀**；本报告对 merge/close 做了粗归并。
- 修复主体、是否引入新问题等结论来自 **文本启发式**，写入论文前建议抽样人工复核。
- open 状态 PR 在计算「通过率」时通常应剔除或单独报告。
