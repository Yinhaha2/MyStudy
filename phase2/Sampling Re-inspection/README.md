# Sampling Re-inspection（第二阶段复检抽样）

从 `phase2/data/prs_performance_and_tests.csv`（**4,146** 条「主要目的为性能」的 PR）中**无放回随机抽**两份名单，互不重叠。

| 样本 | 用途 | 路径 |
| --- | --- | --- |
| 100 条 | 人工复检 | `samples/sample_human_100.*`；结论见根目录 `human_reinspection_report.md` |
| 100 条 | DeepSeek 机器复检 | `samples/sample_deepseek_100.csv`；结果见 `deepseek_recheck/` |

## 目录

| 路径 | 内容 |
| --- | --- |
| `human_reinspection_report.md` / `human_reinspection_summary.json` | 人工复检结论（本目录结果） |
| `samples/` | 两份抽样名单与 ID（`sample_ids.json`） |
| `scripts/run_deepseek_recheck.py` | 机器复检脚本 |
| `deepseek_recheck/` | 机器复检输出（labels / results / summary / log） |

## 抽样协议

| 项 | 值 |
| --- | --- |
| 总体 | `prs_performance_and_tests.csv`（Phase 2 性能目的 PR） |
| 种子 | `20261114`（可复现） |
| 方式 | `random.Random(seed).shuffle` 后切前 100 / 后 100 |
| 两份关系 | **disjoint**（无交集） |
| ID 清单 | `samples/sample_ids.json` |

## 表头说明

CSV 已带原判定与复检空列：

- `original_verdict` / `original_model`：来自 `llm_labels.jsonl` 最后一次成功判定（这 200 条在总体里本就是 `performance`）
- `body_preview`：来自 `pr_texts_cache.jsonl` 的正文预览（最长约 1500 字）
- `recheck_verdict` / `recheck_notes` / `recheck_by` / `recheck_at`：留给人工或机器复检填写（建议仍用 `performance` / `non-performance`）

人工可先看 `samples/sample_human_100.md` 里的链接表，细看时打开对应 CSV 行的 `body_preview`。

## 复检时建议口径（与初筛一致）

与 `run_offpeak_classify.py` / 论文 filter 相同：**标题+正文的主要目的是否为提升 performance**。  
边界例子（CI 加速、flaky 测试、带 `perf:` 但主业是功能）请在 `recheck_notes` 里写一句理由，便于后面估假阳性。

## DeepSeek 机器复检（先写好，高峰勿跑）

脚本：`scripts/run_deepseek_recheck.py`

- 读 `samples/sample_deepseek_100.csv`，优先用 `phase2/data/pr_texts_cache.jsonl` 组装标题+正文，否则退回 CSV 的 `body_preview`
- 模型 `deepseek-flash`，`thinking` 关闭；**只允许回答 `0` 或 `1`**
  - `1` = 以性能为主
  - `0` = 不是性能相关 / 不以性能为主
- Token：仓库根目录 `.deepseekToken`
- **默认高峰拒跑**（北京时间工作日 09:00–12:00、14:00–18:00）；周末/节假日可跑。确要高峰调用才加 `--force`

```bash
python "phase2/Sampling Re-inspection/scripts/run_deepseek_recheck.py" --status
python "phase2/Sampling Re-inspection/scripts/run_deepseek_recheck.py" --dry-run
python "phase2/Sampling Re-inspection/scripts/run_deepseek_recheck.py"
```

跑完写入 `deepseek_recheck/`（可断点续跑）：

| 文件 | 内容 |
| --- | --- |
| `deepseek_recheck_labels.jsonl` | 逐条原始结果（`label` 0/1、`raw`、usage） |
| `deepseek_recheck_results.csv` | 样本表 + `recheck_label` / 与原判定是否一致 |
| `deepseek_recheck_summary.json` | 计数与一致率摘要 |
| `deepseek_recheck.log` | 运行日志 |
