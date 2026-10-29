# MyStudy

Agent 性能 Pull Request 研究。分两个阶段：Phase 1 做实证研究，Phase 2 准备用来提高合并率的语料。论文和数据集链接见 [REFERENCES.md](REFERENCES.md)。

## 目录

```
/
├── README.md
├── REFERENCES.md          # 论文与数据集链接
├── requirements.txt
├── AGENTS.md
├── phase1/                # 实证研究
│   ├── scripts/
│   ├── data/
│   └── docs/
└── phase2/                # 性能测试仓库上的性能 PR
    ├── scripts/
    ├── data/
    ├── docs/
    ├── archive/
    └── scratch/
```

本地密钥放在仓库根目录（`.github_token`、`.deepseekToken`、`DeepSeekAPI`），已写入 `.gitignore`。

## Phase 1：Agent 性能 PR 实证研究

语料在 `phase1/data/finaldatabase/`。主表 1219 条（merged 670、closed 513、open 36，状态见 `summary/coverage_stats.json`）。研究问题在 `phase1/docs/RQ_README.md`，报告在 `phase1/docs/RQ_Analysis.md` 与 `phase1/docs/FullAnalysis.md`。

| 路径 | 作用 |
| --- | --- |
| `phase1/data/finaldatabase/pr_master/` | 主表 `perf_prs_expanded_final`（CSV / Parquet）和论文 CSV 副本 |
| `phase1/data/finaldatabase/auxiliary/` | commit、review、comment、timeline、issue、仓库等关联表，用 `pr_id` 连接主表 |
| `phase1/data/finaldatabase/per_pr/{id}/` | 单条 PR 的附属表和分析 JSON |
| `phase1/data/finaldatabase/classification/` | BERTopic 主题与 AIDev `pr_task_type` |
| `phase1/data/finaldatabase/paper_source_copy/` | 论文原始 CSV |
| `phase1/data/finaldatabase/summary/` | 覆盖统计、GitHub 状态与附属数据刷新报告 |
| `phase1/data/fewshot/` | 6 条 few-shot 金标 `{pr_id}_analysis.json` |
| `phase1/data/full_analysis_distilled.csv` | 全库分析宽表 |
| `phase1/data/rq_analysis_metrics.json` | RQ 报告的机器可读摘要 |
| `phase1/data/rq_analysis_figures/` | RQ 图 |
| `phase1/docs/RQ_README.md` | RQ1–RQ4 定稿 |
| `phase1/docs/RQ_Analysis.md` | 按定稿写的分析报告 |
| `phase1/docs/FullAnalysis.md` | 全库聚合报告 |
| `phase1/docs/RQ_fewshot_guide.md` | few-shot 字段与标注顺序 |
| `phase1/docs/candidate.md` | few-shot 候选 PR |
| `phase1/docs/prompt.md` | 分析用系统提示 |
| `phase1/docs/schema.json` | 分析 JSON 字段说明 |
| `phase1/docs/PR_workflow_dataflow.md` | 单次分析调用的读写顺序 |
| `phase1/docs/PR_workflow_preflight_report.md` | 预检报告 |
| `phase1/docs/workflow_size_policy.md` | DeepSeek 上下文体量与分流 |
| `phase1/scripts/performance_pr_analysis.py` | 读 Hugging Face `hao-li/AIDev` 的官方 `type=perf`，算合并率，写入 `phase1/output/` |
| `phase1/scripts/performance_pr_analysis_all.py` | 同一口径扫 `all_pull_request.parquet`，写入 `phase1/output_all/` |
| `phase1/scripts/generate_full_analysis.py` | 聚合分析 JSON，重写 `FullAnalysis.md` 和宽表 |
| `phase1/scripts/generate_rq_analysis.py` | 重写 `RQ_Analysis.md`、指标 JSON 和 RQ 图 |
| `phase1/scripts/run_pr_analysis.py` | 组装 prompt，调用 DeepSeek，把 `{id}_analysis.json` 写进 `per_pr/` |
| `phase1/scripts/preflight_pr_workflow.py` | 检查密钥、schema 和 6 条金标 |
| `phase1/scripts/workflow_size_policy.py` | 按上下文窗口给 PR 分流，默认写到 `phase1/output_workflow_size/` |
| `phase1/scripts/refresh_finaldatabase_status.py` | 用 GitHub API 复核 PR 状态并更新主表 |
| `phase1/scripts/sync_github_auxiliary_incremental.py` | 把新增的 GitHub 活动并进附属表 |
| `phase1/scripts/build_finaldatabase.py` | 从外部论文输出和 AIDev 表重建 `finaldatabase/`（依赖仓库外的 `AIDev/`、`AIDevPerf/`） |
| `phase1/scripts/extract_databasephase1.py` | 从同一外部来源抽出扩容集，写到 `phase1/data/databasephase1/` |
| `phase1/scripts/analysis_viz/` | 基于宽表的 Jupyter 图 |

在仓库根目录：

```bash
pip install -r requirements.txt
python phase1/scripts/performance_pr_analysis.py
python phase1/scripts/generate_rq_analysis.py
```

`performance_pr_analysis.py` 默认从 Hugging Face 流式读取。`--local` 改为读本仓库**上一级**目录里的 `AIDev/*.parquet`。`build_finaldatabase.py` 和 `extract_databasephase1.py` 还需要上一级的 `AIDevPerf/LLM-performance/Outputs/`。

## Phase 2：有性能测试的 PR

从 [AIDev-7.6M](https://huggingface.co/datasets/hao-li/AIDev-7.6M) 的 pop 子集抽出仓库里能看到性能测试的 PR，共 51,141 条、358 个仓库。再用论文里的「主要目的是不是提升性能」判定，51,141 条已全部判完，其中 4,146 条是性能优化。说明见 `phase2/docs/README.md`，文件角色见 `phase2/docs/FILES.md`。

| 路径 | 作用 |
| --- | --- |
| `phase2/data/prs_with_perf_tests.csv` | 51,141 条：仓库含性能测试，PR 自己不必改到该文件 |
| `phase2/data/prs_performance_and_tests.csv` | 其中被判成性能优化的 4,146 条 |
| `phase2/data/llm_labels.jsonl` | 已完成的 LLM 判定；同一 PR 多行时以最后一次成功结果为准 |
| `phase2/data/llm_summary.json` | 判定计数 |
| `phase2/data/keyword_candidates.csv` | 关键词粗筛，不是论文判定 |
| `phase2/data/summary.json` | 51,141 这一层的规模 |
| `phase2/docs/sample6_repro.md` | 从 992 条里抽 6 条，看仓库里的性能测试能不能复现 |
| `phase2/scripts/extract_prs_with_perf_tests.py` | 重抽 51,141 条名单 |
| `phase2/scripts/run_offpeak_classify.py` | 半价时段继续 LLM 判定，读 `.deepseekToken` |
| `phase2/scripts/classify_performance_purpose.py` | 旧判定入口。直接跑会退出 |
| `phase2/scripts/keyword_screen.py` | 重跑关键词粗筛 |
| `phase2/scripts/scan_test_prs.py` | 按测试文件名扫 commit |
| `phase2/scripts/scan_repo_test_suites.py` | 判断仓库是否已有测试 |
| `phase2/scripts/scan_perf_tests.py` | 判断路径是不是性能测试；三个 scan 脚本的输出在 `phase2/archive/test_pr_scan/` |
| `phase2/archive/test_pr_scan/` | 扫描中间名单和示例 |
| `phase2/scratch/` | 余额探测和抽样检查脚本 |

继续判定：

```bash
python phase2/scripts/run_offpeak_classify.py
```

## 运行产物

这些目录由脚本生成，不入库：`output/`、`output_all/`、`output_pr_analysis/`、`output_workflow_size/`、`analysis_viz/figures/`、`__pycache__/`。Phase 1 脚本把前四类写在 `phase1/` 下。
