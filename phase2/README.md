# Phase 2

仓库里能看到性能测试的 Agent PR，以及其中被判成「主要目的是性能优化」的子集。规模和仓库列表见 [docs/README.md](docs/README.md)，每个文件的角色见 [docs/FILES.md](docs/FILES.md)。

| 目录 | 内容 |
| --- | --- |
| `data/` | 51,141 条名单、992 条性能判定、LLM 记录、关键词粗筛 |
| `scripts/` | 抽取、关键词粗筛、LLM 判定、测试路径扫描 |
| `docs/` | 规模说明、文件说明、6 条复现笔记 |
| `archive/test_pr_scan/` | 扫描中间名单和示例。其中 `_fetch_*.py`、`_peek_*.py`、`_count_repos.py` 不要再跑 |
| `scratch/` | 余额探测和抽样检查 |

在仓库根目录继续判定：

```bash
python phase2/scripts/classify_performance_purpose.py
```
