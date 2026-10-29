# Phase 2 文件

## 数据（`../data/`）

| 文件 | 是什么 |
| --- | --- |
| `prs_with_perf_tests.csv` | 仓库里能看到性能测试的 51,141 条 PR |
| `prs_performance_and_tests.csv` | 上面再按论文方法判成「主要目的是性能」的 4,146 条 |
| `llm_labels.jsonl` | DeepSeek 对 51,141 条的判定。同一条 PR 可能有多行，以最后一次成功判定为准 |
| `llm_summary.json` | 51,141 条全部判完后的计数：性能 4,146，非性能 46,995 |
| `keyword_candidates.csv` | 关键词粗筛，27,019 条，不是论文用的判定 |
| `summary.json` | 51,141 这一层的规模 |

## 接着扩

51,141 条已经全部判完。4,146 条里 Codex 1,484、Copilot 1,875、Claude Code 294、Devin 187、Jules 158、Cursor 148。

半价窗口里跑的是 `run_offpeak_classify.py`，读写 `../data/`。`classify_performance_purpose.py` 直接跑会退出：旧模型 `deepseek-chat` 已停用，思考模式默认打开，而且它不管半价时段。

```bash
python phase2/scripts/run_offpeak_classify.py
```

密钥是仓库根目录的 `.deepseekToken`。北京时间周一到周五 9:00–12:00、14:00–18:00 不调用。模型是 `deepseek-flash`，思考模式关掉。

## 脚本（`../scripts/`）

| 脚本 | 作用 |
| --- | --- |
| `run_offpeak_classify.py` | 半价时段做 LLM 判定，读写 `../data/` |
| `classify_performance_purpose.py` | 旧入口。直接跑会退出，避免在高峰或思考模式下扣费 |
| `keyword_screen.py` | 用论文附录里的关键词再扫一遍 51,141 条，写出 `../data/keyword_candidates.csv` |
| `extract_prs_with_perf_tests.py` | 重新从 AIDev 抽出「仓库有性能测试」的 PR，写回 `../data/prs_with_perf_tests.csv`，并重写本目录的 `README.md` |
| `scan_test_prs.py` | 按严格测试文件名扫 commit |
| `scan_repo_test_suites.py` | 判断仓库里是不是本来就有测试 |
| `scan_perf_tests.py` | 判断路径是不是性能测试。上面三个脚本的输出都写到 `../archive/test_pr_scan/` |

## 中间结果

`../archive/test_pr_scan/` 保存扫描中间文件：diff 里有测试文件的名单、仓库本来就有测试的名单，以及按「diff 碰到性能测试」收下来的名单。`examples/` 是抽出来的测试文件。`_peek_*.py`、`_fetch_*.py`、`_count_repos.py` 把路径写死在作者本机目录上，不要再跑。

`../scratch/` 里是查 DeepSeek 余额和抽查 GitHub 文件的小脚本。
