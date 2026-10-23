# Phase 2 文件

## 数据（`../data/`）

| 文件 | 是什么 |
| --- | --- |
| `prs_with_perf_tests.csv` | 仓库里能看到性能测试的 51,141 条 PR |
| `prs_performance_and_tests.csv` | 上面再按论文方法判成「主要目的是性能」的 992 条 |
| `llm_labels.jsonl` | DeepSeek 已经判过的记录。同一条 PR 可能有多行，以最后一次成功判定为准 |
| `llm_summary.json` | 上次跑到余额用完时的计数 |
| `keyword_candidates.csv` | 关键词粗筛，27,019 条，不是论文用的判定 |
| `summary.json` | 51,141 这一层的规模 |

## 接着扩

在仓库根目录运行：

```bash
python phase2/scripts/classify_performance_purpose.py
```

脚本读 `phase2/data/llm_labels.jsonl`，已经判成 `performance` 或 `non-performance` 的 PR 会跳过。出错的会重试。凑满 1000 条「主要目的是性能」就停；现在是 992，还差 8 条就会停。如果要超过 1000，先改脚本里的 `TARGET_PERFORMANCE`。

密钥是仓库根目录的 `.deepseekToken`。遇到 HTTP 402 会马上停，不会继续打。

这 992 条目前全是 Codex，因为数据表里 Codex 排在前面。接着跑会先把 Codex 里还没判的走完，然后才到 Copilot、Devin、Cursor、Claude Code、Jules。

## 脚本（`../scripts/`）

| 脚本 | 作用 |
| --- | --- |
| `classify_performance_purpose.py` | 接着做上面的 LLM 判定，读写 `../data/` |
| `keyword_screen.py` | 用论文附录里的关键词再扫一遍 51,141 条，写出 `../data/keyword_candidates.csv` |
| `extract_prs_with_perf_tests.py` | 重新从 AIDev 抽出「仓库有性能测试」的 PR，写回 `../data/prs_with_perf_tests.csv`，并重写本目录的 `README.md` |
| `scan_test_prs.py` | 按严格测试文件名扫 commit |
| `scan_repo_test_suites.py` | 判断仓库里是不是本来就有测试 |
| `scan_perf_tests.py` | 判断路径是不是性能测试。上面三个脚本的输出都写到 `../archive/test_pr_scan/` |

## 中间结果

`../archive/test_pr_scan/` 保存扫描中间文件：diff 里有测试文件的名单、仓库本来就有测试的名单，以及按「diff 碰到性能测试」收下来的名单。`examples/` 是抽出来的测试文件。`_peek_*.py`、`_fetch_*.py`、`_count_repos.py` 把路径写死在作者本机目录上，不要再跑。

`../scratch/` 里是查 DeepSeek 余额和抽查 GitHub 文件的小脚本。
