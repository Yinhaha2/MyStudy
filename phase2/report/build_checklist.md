# 仓库构建清单（人工检查用）

数据源：`repo_pr_distribution.csv`（性能目的 PR **4,146** 条，**289** 仓）。  
主表：[`build_checklist.csv`](build_checklist.csv)。

用途：后续挑约 **100 个 PR** 对应的仓库做本地/服务器试编时，在本表填 `human_buildable`，再按「有希望」的仓汇总能覆盖多少 PR。

## 列说明

| 列 | 含义 |
| --- | --- |
| `rank` | 按 PR 数降序排名（与分布报告一致） |
| `repo` | `owner/name` |
| `n_prs` | 该仓在 4,146 中的性能目的 PR 数 |
| `tier` | 原启发式分层：`heavy` / `mid` / `light_py` / `light_go` |
| `primary_perf_ext` | 性能测试文件主扩展名 |
| `language` / `stars` / `forks` | AIDev 仓库元数据（可能空） |
| `merged` / `closed_unmerged` / `open` | PR 结局拆分 |
| `n_prs_with_agentlogs` | 带 AgentLogs 的 PR 数 |
| `human_buildable` | **人工检查**：`1` = 有希望编出来（或已编通）；`0` = 编译难度偏大；空 = 未查 |
| `human_notes` | 可选备注（试编环境、失败原因等） |

## 已填

| 仓库 | tier | n_prs | human_buildable | 备注 |
| --- | --- | ---: | --- | --- |
| meteostat/meteostat | light_py | 2 | 1 | 3090 试编：`pip install -e .` 成功，unit 306 passed |

## 分层速览（原口径，未改）

| tier | 仓数 | PR 数 |
| --- | ---: | ---: |
| heavy | 105 | 3,437 |
| mid | 106 | 471 |
| light_py | 43 | 113 |
| light_go | 35 | 125 |
| **合计** | **289** | **4,146** |

`light_py` + `light_go` ≈ 78 仓 / 238 PR，是先填 `human_buildable` 的优先区；目标若是凑满约 100 个 PR，多半还要往 `mid` 里挑。
