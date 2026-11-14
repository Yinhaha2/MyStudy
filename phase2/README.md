# Phase 2

仓库里能看到性能测试的 Agent PR，以及其中被判成「主要目的是性能优化」的子集。规模和仓库列表见 [docs/README.md](docs/README.md)，每个文件的角色见 [docs/FILES.md](docs/FILES.md)。

后续分析默认用规整集 [`data/curated/`](data/curated/README.md)：

- **4,146** 条性能目的 PR（`prs_master`）
- 其中 **950** 条有 AgentLogs 轨迹（`agentlogs/`）

| 目录 | 内容 |
| --- | --- |
| `data/curated/` | 规整主表 + AgentLogs 抽取（主入口） |
| `data/` | 51,141 / 4,146 原始名单、LLM 记录、关键词粗筛 |
| `scripts/` | 抽取、规整、关键词粗筛、LLM 判定、测试路径扫描 |
| `docs/` | 规模说明、文件说明；示例笔记在 `docs/examples/` |
| `report/` | 仓库–PR 分布结果与构建清单；图在 `report/figures/`；试编示例在 `report/examples/` |
| `Sampling Re-inspection/` | 人工/机器复检结论；样本在 `samples/`；机器输出在 `deepseek_recheck/` |
| `archive/test_pr_scan/` | 扫描中间名单和示例。其中 `_fetch_*.py`、`_peek_*.py`、`_count_repos.py` 不要再跑 |
| `scratch/` | 一次性探测（`agentlogs/`、`deepseek/`） |

重建规整集（需要根目录 `agentlogs/` 联接）：

```bash
python phase2/scripts/build_curated_dataset.py
```
