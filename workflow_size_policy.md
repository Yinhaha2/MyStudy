# Workflow 体量判定策略（DeepSeek API）

> 目的：在「每次 workflow 只分析 1 个 PR」的前提下，预估 DeepSeek 上下文是否装得下，并据此做人力/资源调度。

## 1. 单次 Workflow 上下文构成

```
总输入 ≈ prompt + 待分析 PR 载荷 + 6 × few-shot PR 载荷 + 输出预留
```

| 组成部分 | 说明 | 是否固定 |
|----------|------|----------|
| **prompt** | 系统指令 + `RQ_fewshot_guide.md` 摘要 + `schema.json` 字段说明 | 固定 (~8–12K tokens) |
| **6 × few-shot** | A+C 组 PR（`candidate.md` #1–4, #7–8）的原始材料 + 已完成 `*_analysis.json` | 固定 (~75–85K tokens，`standard_no_patch` 模式) |
| **待分析 PR** | 主表 body/title + reviews + comments + review diff_hunk + commits + 文件级统计 | **随 PR 变化** |
| **输出预留** | JSON 分析结果 + 少量 reasoning | 从总窗口扣除（默认 16K） |

### Few-shot 固定集合（A+C，共 6 条）

```
3228424652, 3074351366, 3194284966, 3145702280, 3125029980, 3022909076
```

B 组（#5–6）仅作论文案例，**不计入 workflow 固定开销**。

## 2. DeepSeek 上下文窗口参考

| 模型 profile | 总上下文 | 建议输出预留 | 可用输入预算 | 备注 |
|--------------|----------|--------------|--------------|------|
| `deepseek-v4-flash` | 1,000,000 | 16,000 | 984,000 | **推荐默认**；`deepseek-chat` 别名至 2026-07-24 |
| `deepseek-v4-pro` | 1,000,000 | 32,000 | 968,000 | 高能力档，预留更多输出 |
| `deepseek-chat-64k` | 64,000 | 8,000 | 56,000 | 保守/对照用 |
| `deepseek-chat-128k` | 128,000 | 12,000 | 116,000 | 扩展窗口对照 |

> Token 估算采用 **chars ÷ 3.5**（代码/英文混合文本的保守值）。正式上线前可用 DeepSeek tokenizer 校准。

## 3. 载荷模式（决定「上传什么」）

| 模式 | 包含内容 | 适用场景 |
|------|----------|----------|
| `standard_no_patch` | body、review、comment、diff_hunk、commit message、文件级统计；**不含**完整 patch | **推荐默认**；平衡准确率与体量 |
| `with_patch` | 上述 + `pr_commit_details.patch` 全文 | 上界估计；固定开销 alone 即可超 64K/128K |
| `compact` | 对 review/comment/diff_hunk 设字符上限，文件明细最多 50 行 | 兜底截断策略 |

**关键结论**：若 workflow 上传完整 patch，6 个 few-shot 的固定开销约 **~83K tokens**，64K 窗口**物理上不可能**一次装下。推荐 workflow 使用 `standard_no_patch`，patch 信息通过 review `diff_hunk` 与文件统计间接获取。

## 4. 路由分层

以「总输入 tokens / 可用输入预算」为主，辅以硬规则：

| 层级 | 阈值 | 建议处置 |
|------|------|----------|
| `workflow_auto` | ≤ 70% 预算 | 全自动 batch；优先调度 |
| `workflow_risky` | 70%–90% | 可自动，记录 token 用量；关注截断 |
| `workflow_overflow` | 90%–100% | 启用 `compact` 或拆分 review 轮次 |
| `manual_xlarge` | > 100% **或** changes ≥ 100K **或** patch ≥ 2M chars | 人工分析 / 专项 pipeline |

## 5. 扫描脚本用法

```bash
# 推荐：V4-Flash + 标准载荷（不含 patch）
python workflow_size_policy.py --model deepseek-v4-flash --payload standard_no_patch

# 多模型对照（仅 standard_no_patch）
python workflow_size_policy.py --model deepseek-v4-flash --compare-models

# 上界估计（含完整 patch）
python workflow_size_policy.py --model deepseek-v4-flash --payload with_patch

# 保守对照（64K 遗留窗口）
python workflow_size_policy.py --model deepseek-chat-64k --payload standard_no_patch
```

输出目录 `output_workflow_size/`（gitignore，运行时生成）：

- `pr_tiers_{model}_{payload}.csv` — 每条 PR 的 tier、token 估计、协作指标
- `summary_{model}_{payload}.json` — 汇总统计
- `SUMMARY_{model}_{payload}.md` — 中文可读摘要

## 6. 资源调度建议（2026-07-21 扫描结果）

基于 `finaldatabase/` **1219** 条 PR（状态刷新后略少于 1221）的实测扫描：

### 推荐配置：`deepseek-v4-flash` + `standard_no_patch`

| 指标 | 数值 |
|------|------|
| 固定开销 | ~36,894 tokens |
| 可一次 workflow 装下 | **1219 / 1219（100%）** |
| `workflow_auto`（≤70% 预算） | **1216（99.8%）** |
| `manual_xlarge`（硬规则触发） | **3（0.2%）** |

3 条 `manual_xlarge` 因 **changes ≥ 100K** 触发硬规则（token 上其实能装下，但分析质量/成本风险高，建议人工）：

| PR ID | Agent | changes | 说明 |
|-------|-------|---------|------|
| 3226043406 | Claude_Code | 158,472 | B 组极端案例，lazy-load 大范围改动 |
| 3119512382 | Copilot | 98,479 | B 组极端案例，Maven 插件大规模清理 |
| 3219880512 | Claude_Code | 121,251 | GCS 文件存储集成，超 12 万行变更 |

### 若使用 `with_patch`（含完整 diff）

| 指标 | 数值 |
|------|------|
| 固定开销 | ~92,662 tokens |
| 装不下（token 溢出） | **1 条**（3119512382，~1.7M tokens） |
| 建议 | workflow **不要上传完整 patch**；diff 信息靠 review `diff_hunk` + 文件统计 |

### 若误用 64K 遗留窗口（对照）

| 指标 | 数值 |
|------|------|
| 装不下 | **53 条（4.35%）** |
| `workflow_risky` | 384 条 |
| 结论 | 64K 窗口下固定 few-shot 开销已占 ~66% 预算，**不推荐** |

### 调度分配

1. **workflow_auto（1216）** → 批量 API 队列，无需人工预审
2. **manual_xlarge（3）** → 直接人工深度分析（恰好覆盖 B 组 2 条 + 1 条超大变更）
3. 若未来切换到 64K 或上传完整 patch，需重新扫描并扩大人工比例

## 7. 限制与后续

- 当前为**字符启发式**估计，未调用真实 tokenizer；误差约 ±15%。
- 未计入 DeepSeek **context cache** 对固定 few-shot 的计费优化（不影响 fit 判定）。
- 若启用 thinking/reasoning 模式，应增大 `output_reserve_tokens` 并重新扫描。
