# 性能 PR 实证研究：RQ 划分与 Few-shot 构建指南

**数据底库**：`MyStudy/finaldatabase/`（1221 条 Agent 性能 PR；主表 + `auxiliary/`）  
**逻辑**：整体（RQ1）→ 过程与低效原因（RQ2）→ 能力边界归纳（RQ3）→ 开发者性能工程实践（RQ4，导师指导）

---

## 与既有研究的关系（必读）

| 内容 | 既有产出 | 本研究定位 |
|------|----------|------------|
| 合并率按 Agent 分层 | `MyStudy/output/`（340 条官方 perf）、`performance_pr_analysis.py` | **部分重复** |
| 1221 扩容集合并率 | `report_stats_for_teacher.json`（~56.6%） | **已算过，RQ1 仅引用** |
| BERTopic 主题分布 | 论文 arXiv:2512.24630 / `bertopic_topic_info.csv` | **不重复做主题建模** |
| 不协调调用等反模式 | **组内先前实证研究**（taxonomy 已有） | **RQ2 复用分类体系** |
| Review 关键词分桶 | `performance_pr_analysis.py` → `text_bucket()` | **RQ2 扩展，非从零** |

**结论**：RQ1 与先前工作**高度重复**，正文中应压缩为「1221 扩容集验证性描述 + 变更规模增量」；**创新点集中在 RQ2–RQ4**。

---

## RQ1：PR 合并结果基线（宏观，压缩呈现）

**研究问题**：Agent 性能 PR 的整体合并格局如何？变更规模是否与结果相关？

| 小点 | 内容 | 与先前关系 |
|------|------|------------|
| 1.1 | 合并率 / 失败率（含 open vs 仅 closed 终态）；按 Agent 分层 | **重复** `output/summary_metrics.json`；1221 集更新数字即可 |
| 1.2 | 变更规模 vs 结果：文件数、additions/deletions、commit 数 | **增量**：先前脚本未系统做 |
| 1.3 | （可选）生命周期：存活天数、open 占比 | **增量**，篇幅从简 |

**方法**：脚本聚合；**不需 LLM**。  
**写作建议**：1–2 段 + 1 表 1 图；明确写「与 AIDev-pop 340 条 / 论文口径对齐，1221 扩容集为验证性延伸」。

---

## RQ2：Agent 性能 PR 的过程、失效与低效原因（微观，核心）

**研究问题**：AI Agent 生成的性能 PR 为何未合并或效果不佳？人机协同中 review 关注什么？低效是否呈现可复用的反模式？

> 原 RQ2（Review/拒因）与原 RQ3（Topic/Agent 边界）**合并为本 RQ**：本质均为「性能 PR 低效/失效的原因分析」。

| 小点 | 内容 |
|------|------|
| 2.1 | **Review/Comment 维度**：测试、正确性、设计/API、性能可证性、范围、CI/构建、文档等 |
| 2.2 | **拒因 / 未合并画像**：closed PR；`CHANGES_REQUESTED` 优先，否则 comment 推断 |
| 2.3 | **性能低效反模式**（复用组内先前 taxonomy）：不协调函数调用——循环嵌套、重复 I/O、频繁 GC、重复字符串遍历、锁使用失误等；从 patch / commit message / review 中标注 |
| 2.4 | **Topic × Agent 差异**：哪些主题合并率低、哪些 Agent 在哪些主题更易失败（用已有 BERTopic 标签，不重新建模） |

**方法**：LLM few-shot + 关键词分桶校验 + 反模式标签（与先前研究编码表对齐）。  
**限制**：~29% 有 formal review；拒因/低效原因为推断；结论分「有文本子集」与「全量」两层报告。

---

## RQ3：Agent 性能优化能力边界归纳（总结）

**研究问题**：综合 RQ1 结果与 RQ2 失效模式，Agent 在性能优化上的擅长领域、短板与技术边界是什么？

| 小点 | 内容 |
|------|------|
| 3.1 | **高合并 × 低争议主题**：如缓存、懒加载、批处理等（来自 Topic 合并率 + RQ2 拒因交叉） |
| 3.2 | **低合并 × 高失败主题**：如需 benchmark 证明、底层 runtime/GPU、正确性-性能权衡等 |
| 3.3 | **边界框架**：技术栈边界 / 证据要求边界 / 协作流程边界；Agent 间差异（Codex vs Copilot 等） |

**方法**：RQ1 + RQ2 聚合 + 定性归纳；**不单独跑新模型**。

---

## RQ4：开发者对 AI 性能 PR 的评审与处置实践（导师指导，新增）

**研究问题**（对标既有性能工程实证文献）：维护者在审查 Agent 性能 PR 时，如何发现性能问题、证据是否可复现、合并后若出现退化如何处置？

| 小点 | 内容 | 可操作信号（数据集） |
|------|------|----------------------|
| 4.1 | **性能缺陷识别方式**：代码推理（静态读码）/ Profiler 观测 / 负载测试（benchmark、stress test）/ CI 自动化；何者为主 | review/comment 关键词：`benchmark`、`profile`、`perf`、`load test`、`JMeter`、`before/after`；timeline `deployed` |
| 4.2 | **PR 材料能否支撑复现**：是否附 benchmark 结果、profiling 截图/日志、复现步骤、最小用例；材料完整性评级 | PR body、comment、commit message；是否链 issue；CI comment |
| 4.3 | **性能退化处置方式**：不管 / 直接关闭或拒绝 / 回滚（revert timeline）/ 修复（follow-up commit、requested changes 后改码） | timeline：`reverted`、`merged` 后再 `closed`；多轮 `committed`；review 中的 revert/fix 表述 |
| 4.4 | **与 RQ2 反模式对照**：识别方式 × 低效类型 × 处置方式 交叉（如「仅代码推理却要求 benchmark」类冲突） | RQ2 反模式标签 + RQ4 标注联表 |

**方法**：Few-shot 标注（侧重 4.1–4.3）+ 关键词/heuristic 预筛 + 人工抽检验证。  
**与 RQ2 分工**：RQ2 问「PR 为何失败/低效」；RQ4 问「人如何发现、验证、处理性能问题」。

---

## 构建 Few-shot 时关注点

手动案例建议 **10–12 条**，覆盖：

- `merged` / `closed`；有/无 review；各 Agent；各 RQ 所需类型各 ≥2 条  
- RQ2：含 2–3 条**可明确标注反模式**的 PR  
- RQ4：含 2 条**有 benchmark/profiler**、2 条**仅叙述性声称**、1 条**revert/修复** timeline

### 代码特征指标（定量，脚本可算）

| 类别 | 指标 | 来源 |
|------|------|------|
| **变更规模** | 改动文件数；additions / deletions / changes；单文件最大改动 | `pr_commit_details` |
| **变更结构** | commit 数；跨目录数；新增/修改/删除文件数 | `pr_commits`, `pr_commit_details` |
| **变更集中度** | Top-1 文件占比；路径/语言分布 | `pr_commit_details` |
| **协作** | review 数；APPROVED / CHANGES_REQUESTED / COMMENTED；行内 review comment 数；PR comment 数 | `pr_reviews`, `pr_review_comments_v2`, `pr_comments` |
| **时间** | 存活天数；timeline 事件数；review 轮次；首评延迟 | 主表 + `pr_timeline` |
| **Issue** | 关联 issue 数 | `related_issue` |
| **元数据** | Agent；status；Topic；aidev_task_type；detection_source | 主表 |
| **Timeline** | committed / reviewed / reverted / merged / closed / copilot_work_* 计数 | `pr_timeline` |
| **证据材料（RQ4）** | body 是否含 benchmark 表格/数字；是否提及 profiler 工具名；是否含复现步骤 | 主表 body + comments |

### 分析结果内容（定性，Few-shot 人工标注 → LLM 学）

| 维度 | 标注项 | 适用 RQ |
|------|--------|---------|
| **性能聚焦** | 优化类型；改动层级；证据类型（benchmark / profiling / 叙述） | RQ2 |
| **低效反模式** | `nested_loop` / `repeated_io` / `frequent_gc` / `string_traversal` / `lock_misuse` / `none` / `unknown` | RQ2 |
| **合并/拒因** | outcome_reason；review_dimensions；blocking；confidence | RQ2 |
| **Topic/边界** | 主题难度；边界类型（技术栈/证据/流程） | RQ3 |
| **识别方式** | `code_reading` / `profiler` / `load_test` / `ci_auto` / `mixed` / `unknown` | RQ4 |
| **材料可复现性** | `sufficient` / `partial` / `insufficient` / `unknown` | RQ4 |
| **退化处置** | `ignore` / `reject_close` / `revert` / `fix_in_pr` / `fix_followup` / `not_applicable` | RQ4 |

### 单条 Few-shot 输出包（JSON 扩展）

```json
{
  "perf_focus": ["cache"],
  "inefficiency_antipattern": ["repeated_io"],
  "outcome_reason": "missing_benchmark",
  "review_dimensions": ["perf_evidence", "tests"],
  "boundary_tag": "evidence_required",
  "detection_method": ["code_reading", "load_test"],
  "reproducibility": "partial",
  "regression_handling": "fix_in_pr",
  "confidence": "high",
  "notes": "一句话依据"
}
```

---

## 实施顺序

1. **RQ1 脚本**（增量指标 only；合并率引用已有结果）  
2. **Few-shot 10–12 条**（覆盖 RQ2 反模式 + RQ4 识别/处置）  
3. **RQ2 批量标注** → RQ3 归纳  
4. **RQ4 批量标注**（可与 RQ2 同一 pass，扩展 JSON 字段）

---

## 数据覆盖率（写进论文）

| 信号 | 覆盖 |
|------|------|
| commit / 文件级变更 | ~99.9% |
| timeline | 100% |
| formal review | ~29% |
| 任意 comment/review | ~56% |
| revert 等处置信号 | 需从 timeline 事件筛选，覆盖待统计 |

RQ2/RQ4 结论必须分层：**有 review/comment 文本子集** vs **全量（含 unknown）**。
