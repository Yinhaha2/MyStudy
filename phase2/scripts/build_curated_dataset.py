"""Build the curated Phase 2 dataset.

Outputs under phase2/data/curated/:
  - prs_master.csv / .parquet          4,146 performance-purpose PRs
  - agentlogs_index.csv                the 950 that match AgentLogs
  - summary.json
  - agentlogs/                         extracted AgentLogs tables for those 950
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
PHASE2_DATA = ROOT / "phase2" / "data"
AGENTLOGS = ROOT / "agentlogs"
OUT = PHASE2_DATA / "curated"
AL_OUT = OUT / "agentlogs"

PERF_CSV = PHASE2_DATA / "prs_performance_and_tests.csv"


def as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, float) and np.isnan(value):
        return []
    if isinstance(value, np.ndarray):
        return list(value.tolist())
    if isinstance(value, list):
        return value
    try:
        return list(value)
    except TypeError:
        return []


def ids_from_refs(series) -> set[str]:
    out: set[str] = set()
    for value in series:
        for item in as_list(value):
            if isinstance(item, dict) and item.get("id"):
                out.add(str(item["id"]))
    return out


def to_jsonable(obj):
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, np.ndarray)):
        return [to_jsonable(v) for v in (obj.tolist() if isinstance(obj, np.ndarray) else obj)]
    if hasattr(obj, "as_py"):
        return to_jsonable(obj.as_py())
    return str(obj)


def write_parquet(table: pa.Table, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, compression="zstd")
    print(f"  wrote {path.relative_to(ROOT)} rows={table.num_rows} bytes={path.stat().st_size}")


def load_agentlogs_prs() -> pd.DataFrame:
    table = ds.dataset(AGENTLOGS / "pull_requests", format="parquet").to_table(
        columns=[
            "id",
            "number",
            "repository",
            "created_by_tasks",
            "created_by_sessions",
            "title",
            "state",
            "merged",
            "user",
        ]
    )
    df = table.to_pandas()
    df["repo"] = df["repository"].map(
        lambda x: x["full_name"] if isinstance(x, dict) else None
    )
    df["agentlogs_pr_id"] = df["id"].astype("Int64")
    df["number"] = df["number"].astype("int64")
    return df


def build_master(ours: pd.DataFrame, al_prs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    merge_cols = [
        "repo",
        "number",
        "agentlogs_pr_id",
        "created_by_tasks",
        "created_by_sessions",
        "state",
        "merged",
    ]
    matched = ours.merge(
        al_prs[merge_cols],
        on=["repo", "number"],
        how="left",
        validate="one_to_one",
    )
    matched["has_agentlogs"] = matched["agentlogs_pr_id"].notna()
    matched["n_agentlogs_tasks"] = matched["created_by_tasks"].map(
        lambda x: len(as_list(x))
    )
    matched["n_agentlogs_sessions"] = matched["created_by_sessions"].map(
        lambda x: len(as_list(x))
    )

    master = matched[
        [
            "pr_id",
            "number",
            "outcome",
            "agent",
            "repo",
            "html_url",
            "title",
            "perf_files",
            "has_agentlogs",
            "agentlogs_pr_id",
            "n_agentlogs_tasks",
            "n_agentlogs_sessions",
        ]
    ].copy()
    master["agentlogs_pr_id"] = master["agentlogs_pr_id"].astype("Int64")

    index = master[master["has_agentlogs"]].copy()
    index = index.merge(
        matched[["pr_id", "created_by_tasks", "created_by_sessions"]],
        on="pr_id",
        how="left",
    )
    return master, index


def extract_by_ids(
    table_name: str,
    id_field: str,
    ids: set,
    id_type,
) -> pa.Table:
    if not ids:
        return pa.table({})
    dataset = ds.dataset(AGENTLOGS / table_name, format="parquet")
    value_set = pa.array(sorted(ids), type=id_type)
    filt = pc.is_in(pc.field(id_field), value_set=value_set)
    return dataset.to_table(filter=filt)


def extract_nested_id(
    table_name: str,
    nested_field: str,
    child_field: str,
    ids: set,
    id_type,
) -> pa.Table:
    if not ids:
        return pa.table({})
    dataset = ds.dataset(AGENTLOGS / table_name, format="parquet")
    value_set = pa.array(sorted(ids), type=id_type)
    filt = pc.is_in(pc.field(nested_field, child_field), value_set=value_set)
    return dataset.to_table(filter=filt)


def extract_agentlogs(index: pd.DataFrame) -> dict:
    AL_OUT.mkdir(parents=True, exist_ok=True)
    stats: dict = {}

    pr_ids = set(int(x) for x in index["agentlogs_pr_id"].dropna().tolist())
    task_ids = ids_from_refs(index["created_by_tasks"])
    session_ids = ids_from_refs(index["created_by_sessions"])
    print(
        f"extracting for prs={len(pr_ids)} tasks={len(task_ids)} sessions={len(session_ids)}"
    )

    # Full pull_request rows for the 950
    pr_table = extract_by_ids("pull_requests", "id", pr_ids, pa.int64())
    write_parquet(pr_table, AL_OUT / "pull_requests.parquet")
    stats["pull_requests"] = pr_table.num_rows

    # Tasks / sessions referenced on those PR rows, plus any sessions pointing at the PRs
    task_table = extract_by_ids("agent_tasks", "id", task_ids, pa.string())
    write_parquet(task_table, AL_OUT / "agent_tasks.parquet")
    stats["agent_tasks"] = task_table.num_rows

    session_table = extract_by_ids("agent_sessions", "id", session_ids, pa.string())
    # Also catch sessions that only link via pull_request_artifact.id
    session_by_pr = extract_nested_id(
        "agent_sessions", "pull_request_artifact", "id", pr_ids, pa.int64()
    )
    if session_by_pr.num_rows:
        # Union by id
        both = pa.concat_tables([session_table, session_by_pr]).combine_chunks()
        # Deduplicate on id
        pdf = both.to_pandas()
        pdf = pdf.drop_duplicates(subset=["id"], keep="first")
        session_table = pa.Table.from_pandas(pdf, preserve_index=False)
    write_parquet(session_table, AL_OUT / "agent_sessions.parquet")
    stats["agent_sessions"] = session_table.num_rows

    # Refresh session id set from extracted sessions
    session_ids = set(session_table.column("id").to_pylist())

    workflow_ids = set()
    if "workflow_run" in session_table.column_names:
        for item in session_table.column("workflow_run").to_pylist():
            if isinstance(item, dict) and item.get("id") is not None:
                workflow_ids.add(int(item["id"]))
    workflow_table = extract_by_ids("workflow_runs", "id", workflow_ids, pa.int64())
    write_parquet(workflow_table, AL_OUT / "workflow_runs.parquet")
    stats["workflow_runs"] = workflow_table.num_rows

    timeline_table = extract_nested_id(
        "pull_request_timelines", "pull_request", "id", pr_ids, pa.int64()
    )
    if timeline_table.num_rows and "event_index" in timeline_table.column_names:
        timeline_table = timeline_table.sort_by(
            [("pull_request", "ascending"), ("event_index", "ascending")]
        )
    write_parquet(timeline_table, AL_OUT / "pull_request_timelines.parquet")
    stats["pull_request_timelines"] = timeline_table.num_rows

    # Session logs: one filtered scan over the 63GB table
    print("scanning agent_session_logs (this can take several minutes) ...")
    logs = extract_nested_id(
        "agent_session_logs", "session", "id", session_ids, pa.string()
    )
    # Write as a single parquet; optionally also shard later if needed
    write_parquet(logs, AL_OUT / "agent_session_logs.parquet")
    stats["agent_session_logs"] = logs.num_rows

    # Compact readable JSONL index of log entries (not full payloads)
    readable_path = AL_OUT / "agent_session_logs_readable.jsonl"
    n_readable = 0
    with readable_path.open("w", encoding="utf-8") as fh:
        for row in logs.to_pylist():
            data = row.get("data") or {}
            choices = data.get("choices") or []
            tool_names = []
            for ch in choices:
                delta = (ch or {}).get("delta") or {}
                for tc in delta.get("tool_calls") or []:
                    name = tc.get("function_name") or tc.get("custom_name")
                    if name:
                        tool_names.append(name)
                msg = (ch or {}).get("message") or {}
                for tc in msg.get("tool_calls") or []:
                    name = tc.get("function_name") or tc.get("custom_name")
                    if name:
                        tool_names.append(name)
            telem = data.get("toolTelemetry") or {}
            props = telem.get("properties") or {}
            restricted = telem.get("restrictedProperties") or {}
            rec = {
                "session_id": (row.get("session") or {}).get("id"),
                "entry_index": row.get("entry_index"),
                "parsed": row.get("parsed"),
                "kind": data.get("kind"),
                "role": data.get("role"),
                "turn": data.get("turn"),
                "model": data.get("model"),
                "tool_names": tool_names,
                "tool_event": telem.get("event"),
                "command": props.get("command"),
                "path": restricted.get("path") or props.get("path"),
                "status": props.get("status") or props.get("shell_status"),
                "error": (data.get("error") or {}).get("message")
                if isinstance(data.get("error"), dict)
                else data.get("modelCall_error"),
                "created": data.get("created"),
            }
            fh.write(json.dumps(to_jsonable(rec), ensure_ascii=False) + "\n")
            n_readable += 1
    print(
        f"  wrote {readable_path.relative_to(ROOT)} lines={n_readable} "
        f"bytes={readable_path.stat().st_size}"
    )
    stats["agent_session_logs_readable"] = n_readable
    stats["task_ids"] = len(task_ids)
    stats["session_ids"] = len(session_ids)
    stats["workflow_ids"] = len(workflow_ids)
    return stats


def main() -> None:
    assert AGENTLOGS.exists(), f"missing local AgentLogs at {AGENTLOGS}"
    assert PERF_CSV.exists(), f"missing {PERF_CSV}"
    OUT.mkdir(parents=True, exist_ok=True)

    ours = pd.read_csv(PERF_CSV)
    print(f"loaded performance PRs: {len(ours)}")
    al_prs = load_agentlogs_prs()
    print(f"loaded AgentLogs pull_requests: {len(al_prs)}")

    master, index = build_master(ours, al_prs)
    master_path = OUT / "prs_master.csv"
    master.to_csv(master_path, index=False)
    master.to_parquet(OUT / "prs_master.parquet", index=False)
    print(f"wrote {master_path} n={len(master)} has_agentlogs={int(master.has_agentlogs.sum())}")

    index_out = index.drop(columns=["created_by_tasks", "created_by_sessions"]).copy()
    index_path = OUT / "agentlogs_index.csv"
    index_out.to_csv(index_path, index=False)
    index_out.to_parquet(OUT / "agentlogs_index.parquet", index=False)
    print(f"wrote {index_path} n={len(index_out)}")

    # Keep session/task id lists for provenance
    refs = []
    for _, row in index.iterrows():
        refs.append(
            {
                "pr_id": int(row["pr_id"]),
                "agentlogs_pr_id": int(row["agentlogs_pr_id"]),
                "repo": row["repo"],
                "number": int(row["number"]),
                "task_ids": [
                    x.get("id")
                    for x in as_list(row["created_by_tasks"])
                    if isinstance(x, dict)
                ],
                "session_ids": [
                    x.get("id")
                    for x in as_list(row["created_by_sessions"])
                    if isinstance(x, dict)
                ],
            }
        )
    refs_path = OUT / "agentlogs_pr_refs.jsonl"
    with refs_path.open("w", encoding="utf-8") as fh:
        for rec in refs:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"wrote {refs_path} n={len(refs)}")

    al_stats = extract_agentlogs(index)

    summary = {
        "performance_purpose_prs": int(len(master)),
        "repos": int(master["repo"].nunique()),
        "outcomes": master["outcome"].value_counts().to_dict(),
        "agents": master["agent"].value_counts().to_dict(),
        "with_agentlogs": int(master["has_agentlogs"].sum()),
        "without_agentlogs": int((~master["has_agentlogs"]).sum()),
        "agentlogs_match_key": "(repo, number)",
        "agentlogs_agents": index_out["agent"].value_counts().to_dict(),
        "agentlogs_outcomes": index_out["outcome"].value_counts().to_dict(),
        "agentlogs_extract": al_stats,
        "paths": {
            "prs_master": "phase2/data/curated/prs_master.csv",
            "agentlogs_index": "phase2/data/curated/agentlogs_index.csv",
            "agentlogs_dir": "phase2/data/curated/agentlogs/",
            "source_performance_csv": "phase2/data/prs_performance_and_tests.csv",
            "source_agentlogs": "agentlogs/ (junction to local full dataset)",
        },
    }
    summary_path = OUT / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {summary_path}")
    print("done")


if __name__ == "__main__":
    main()
