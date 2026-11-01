# Phase 2 规整数据集

后续工作围绕这里展开：

1. **4,146** 条「仓库有性能测试，且主要目的是性能优化」的 PR（`prs_master`）
2. 其中 **950** 条能在 AgentLogs 对上，轨迹已抽到 `agentlogs/`

匹配键是 `(repo, number)`，不是 AIDev 的 `pr_id`。

## 文件

| 文件 | 内容 |
| --- | --- |
| `prs_master.csv` / `.parquet` | 4,146 条主表，带 `has_agentlogs`、`agentlogs_pr_id`、任务/会话数 |
| `agentlogs_index.csv` / `.parquet` | 上述 950 条子集 |
| `agentlogs_pr_refs.jsonl` | 每条 PR 对应的 task id、session id 列表 |
| `summary.json` | 规模与抽取统计 |
| `agentlogs/pull_requests.parquet` | 950 条 AgentLogs PR 行 |
| `agentlogs/agent_tasks.parquet` | 965 条任务 |
| `agentlogs/agent_sessions.parquet` | 2,818 次会话 |
| `agentlogs/workflow_runs.parquet` | 2,260 次 Actions run |
| `agentlogs/pull_request_timelines.parquet` | 41,202 个时间线事件 |
| `agentlogs/agent_session_logs.parquet` | 352,133 条会话日志（完整字段；约 135MB，**不入库**，需本地重建） |
| `agentlogs/agent_session_logs_readable.jsonl` | 同一批日志的精简行（约 99MB，**不入库**，需本地重建） |

重建：

```bash
python phase2/scripts/build_curated_dataset.py
```

依赖仓库根目录的 `agentlogs/`（指向本机全量 AgentLogs 的联接）。会话日志两份大文件已写入 `.gitignore`，GitHub 推不上去；其它 AgentLogs 元数据表会入库。
