# 示例：facioquo/stock-indicators-python #439

第二阶段 4,146 条性能 PR 里，有 950 条能在 [AgentLogs](https://huggingface.co/datasets/risenlab/agentlogs)（发布版 `1.0-20261008`）的 `pull_requests` 表对上。这条是其中一条 Copilot，标题写的就是性能优化。

GitHub：<https://github.com/facioquo/stock-indicators-python/pull/439>

仓库里能看到的性能测试：`benchmarks/test_benchmark_indicators.py`、`benchmarks/test_decimal_conversion_performance.py`。

## 两边各记了什么

| | 第二阶段表 | AgentLogs `pull_requests` |
| --- | --- | --- |
| 身份 | `pr_id` = `3347093816`（AIDev 的 id，不是 GitHub PR id） | GitHub PR id = `2767784972` |
| 仓库 / 号 | `facioquo/stock-indicators-python` #439 | 同左 |
| 标题 | perf: Use 4x faster decimal conversion method across all indicators | 同左 |
| Agent | Copilot | 提交者 `copilot-swe-agent[bot]`，任务创建者 `daveskender` |
| 结局 | `open` | `closed`，已合并。合并者 `daveskender`，时间 2026-05-13 |
| 规模 | | +515 / −101，28 个文件 |
| 分支 | | `copilot/fix-392` → `main` |

第二阶段的 `open` 来自 AIDev 抽数时的状态。AgentLogs 里这条 PR 后来在 2026-05-13 合并了。DeepSeek 对标题和正文的判定是 `performance`（`deepseek-flash`，思考关掉）。

AgentLogs 正文是一份勾选清单：rebase 到 main、保留 `to_pydecimal_via_double`（大约 4 倍加速）、所有 indicator 的 getter 改用这个转换，并修了 lint 和测试。583 个测试通过。

## 文件

| 文件 | 内容 |
| --- | --- |
| `phase2_pr.json` | 第二阶段 `prs_performance_and_tests.csv` 的这一行，加上 `llm_labels.jsonl` 里最后一次成功判定 |
| `agentlogs_pull_request.json` | AgentLogs `pull_requests` 的整行 |
| `agentlogs_tasks.json` | 指向这条 PR 的 `agent_tasks` |
| `agentlogs_sessions.json` | 指向这条 PR 的 `agent_sessions` 整行 |
| `sessions_readable.json` | 上面 8 个会话抽出来的名字、模型、状态和报错 |

## AgentLogs 里的任务和会话

一条任务：`cb4388d7-fc41-40f7-81f7-80c5f782598b`，状态 `completed`，已归档。协作者 slug 是 `copilot-developer`。下面 8 个会话都有 `log_found = true`。会话上的 `prompt` 和多数 `model` 是空的；具体对话在 `agent_session_logs`（约 63GB），本地没有这张表，所以这里没有逐条消息。

| # | 时间 (UTC) | 会话名 | 状态 | 模型 | 触发 |
| ---: | --- | --- | --- | --- | --- |
| 0 | 2025-08-22 23:47 | Initial implementation | completed | | issue_assignment |
| 1 | 2025-08-28 23:29 | Review from @DaveSkender | completed | | pull_request_review |
| 2 | 2025-08-29 00:13 | Review from @DaveSkender | completed | | pull_request_comment |
| 3 | 2025-12-24 09:45 | Improving performance with new decimal conversion method | completed | claude-sonnet-4.5 | pull_request_comment |
| 4 | 2025-12-26 03:28 | Implementing faster decimal conversion method for indicators | failed | claude-sonnet-4.5 | pull_request_comment |
| 5 | 2025-12-26 04:21 | Enhancing performance of decimal conversion methods | failed | claude-sonnet-4.5 | pull_request_comment |
| 6 | 2025-12-27 10:07 | Enhancing decimal conversion performance across indicators | completed | claude-sonnet-4.5 | pull_request_review |
| 7 | 2026-05-13 03:20 | Improving decimal conversion performance across all indicators | completed | claude-sonnet-4.6 | pull_request_comment |

第 4、5 次失败的原因相同：Copilot 还在改的时候，分支上又被推了新提交，它没能把自己的改动和远端分支合上。
