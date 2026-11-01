"""Extract remaining AgentLogs tables for stock-indicators-python #439."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
AGENTLOGS = ROOT / "agentlogs"
OUT = Path(__file__).resolve().parent

PR_ID = 2767784972
REPO = "facioquo/stock-indicators-python"
TASK_ID = "cb4388d7-fc41-40f7-81f7-80c5f782598b"

SESSION_IDS = [
    "935c7929-33ca-47f6-a8a3-db1f391c9892",
    "e6a72104-d8d8-4165-a949-1dc12eef979a",
    "70695499-3347-437b-84dc-1cad53d888c4",
    "1218f488-380f-4cbc-8cd9-d80f350f03d2",
    "6504ad00-ede9-4481-8d8c-0d28da0d6e99",
    "beed28c1-efff-41f2-8142-b14deb2c9fd2",
    "4561d5e8-a704-48ab-af36-74176ade88ae",
    "6e906527-fd07-4d0b-9be6-0e0bcfa6aa1e",
]

WORKFLOW_RUN_IDS = [
    17168336377,
    17310379260,
    17310988719,
    20483405742,
    20515218686,
    20515863022,
    20537656523,
    25776208199,
]

USER_IDS = {
    8432125,  # daveskender
    198982749,  # copilot-swe-agent[bot]
}


def to_jsonable(obj):
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if hasattr(obj, "as_py"):
        return to_jsonable(obj.as_py())
    return str(obj)


def table_to_records(table: pa.Table) -> list:
    return to_jsonable(table.to_pylist())


def write_json(name: str, payload) -> Path:
    path = OUT / name
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {path.name}: type={type(payload).__name__}", end="")
    if isinstance(payload, list):
        print(f" n={len(payload)} bytes={path.stat().st_size}")
    elif isinstance(payload, dict):
        print(f" keys={len(payload)} bytes={path.stat().st_size}")
    else:
        print(f" bytes={path.stat().st_size}")
    return path


def extract_workflow_runs() -> None:
    table = pq.read_table(AGENTLOGS / "workflow_runs")
    mask = pc.is_in(table["id"], value_set=pa.array(WORKFLOW_RUN_IDS, type=pa.int64()))
    filtered = table.filter(mask).sort_by("created_at")
    write_json("agentlogs_workflow_runs.json", table_to_records(filtered))


def extract_timelines() -> None:
    dataset = ds.dataset(AGENTLOGS / "pull_request_timelines", format="parquet")
    filt = pc.field("pull_request", "id") == PR_ID
    table = dataset.to_table(filter=filt).sort_by("event_index")
    write_json("agentlogs_pull_request_timeline.json", table_to_records(table))


def extract_repository() -> None:
    dataset = ds.dataset(AGENTLOGS / "repositories", format="parquet")
    table = dataset.to_table(filter=pc.field("full_name") == REPO)
    records = table_to_records(table)
    write_json("agentlogs_repository.json", records[0] if records else {})


def extract_users() -> None:
    """Keep identity; truncate huge reverse-index lists to this PR only."""
    dataset = ds.dataset(AGENTLOGS / "users", format="parquet")
    table = dataset.to_table(
        filter=pc.is_in(pc.field("id"), value_set=pa.array(sorted(USER_IDS), type=pa.int64()))
    )
    records = table_to_records(table)
    trimmed = []
    for row in records:
        keep = {
            "id": row.get("id"),
            "login": row.get("login"),
            "graphql_id": row.get("graphql_id"),
            "type": row.get("type"),
            "found_using": row.get("found_using"),
            "created_at": row.get("created_at"),
        }
        # Keep only references that touch this example PR / task / sessions.
        def touches_pr(item: dict) -> bool:
            if not isinstance(item, dict):
                return False
            if item.get("id") == PR_ID:
                return True
            pr = item.get("pull_request") or {}
            return pr.get("id") == PR_ID

        def touches_session(item: dict) -> bool:
            return isinstance(item, dict) and item.get("id") in SESSION_IDS

        def touches_task(item: dict) -> bool:
            return isinstance(item, dict) and item.get("id") == TASK_ID

        def touches_workflow(item: dict) -> bool:
            return isinstance(item, dict) and item.get("id") in WORKFLOW_RUN_IDS

        keep["tasks_for_this_example"] = [
            x for x in (row.get("tasks") or []) if touches_task(x)
        ]
        keep["sessions_for_this_example"] = [
            x for x in (row.get("sessions") or []) if touches_session(x)
        ]
        keep["pull_requests_for_this_example"] = [
            x for x in (row.get("pull_requests") or []) if touches_pr(x)
        ]
        keep["assigned_pull_requests_for_this_example"] = [
            x for x in (row.get("assigned_pull_requests") or []) if touches_pr(x)
        ]
        keep["merged_pull_requests_for_this_example"] = [
            x for x in (row.get("merged_pull_requests") or []) if touches_pr(x)
        ]
        keep["timeline_events_for_this_example"] = [
            x for x in (row.get("timeline_events") or []) if touches_pr(x)
        ]
        keep["workflow_runs_for_this_example"] = [
            x for x in (row.get("workflow_runs") or []) if touches_workflow(x)
        ]
        keep["triggered_workflow_runs_for_this_example"] = [
            x for x in (row.get("triggered_workflow_runs") or []) if touches_workflow(x)
        ]
        keep["note"] = (
            "Full AgentLogs user rows contain reverse indexes over the whole dataset; "
            "this export keeps identity fields plus only links that touch PR #439."
        )
        trimmed.append(keep)
    write_json("agentlogs_users.json", trimmed)


def extract_session_logs() -> None:
    wanted = set(SESSION_IDS)
    dataset = ds.dataset(AGENTLOGS / "agent_session_logs", format="parquet")
    # Nested filter: session.id IN (...)
    filt = pc.is_in(pc.field("session", "id"), value_set=pa.array(SESSION_IDS))
    print("scanning agent_session_logs ...")
    table = dataset.to_table(filter=filt)
    print(f"matched log rows: {table.num_rows}")
    records = table_to_records(table)
    # Sort by session order then entry_index
    order = {sid: i for i, sid in enumerate(SESSION_IDS)}
    records.sort(
        key=lambda r: (
            order.get((r.get("session") or {}).get("id"), 999),
            r.get("entry_index") or 0,
        )
    )
    write_json("agentlogs_session_logs.json", records)

    # Compact readable summary for browsing without opening the huge file.
    summary = []
    for r in records:
        data = r.get("data") or {}
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
        content_bits = []
        for c in data.get("content") or []:
            if isinstance(c, dict) and c.get("text"):
                content_bits.append(c["text"][:200])
        telem = data.get("toolTelemetry") or {}
        props = telem.get("properties") or {}
        restricted = telem.get("restrictedProperties") or {}
        summary.append(
            {
                "session_id": (r.get("session") or {}).get("id"),
                "entry_index": r.get("entry_index"),
                "parsed": r.get("parsed"),
                "kind": data.get("kind"),
                "role": data.get("role"),
                "turn": data.get("turn"),
                "model": data.get("model"),
                "source": data.get("source"),
                "performedBy": data.get("performedBy"),
                "tool_call_id": data.get("tool_call_id"),
                "tool_names": tool_names,
                "tool_event": telem.get("event"),
                "command": props.get("command"),
                "path": restricted.get("path") or props.get("path"),
                "status": props.get("status") or props.get("shell_status"),
                "error": (data.get("error") or {}).get("message")
                if isinstance(data.get("error"), dict)
                else data.get("modelCall_error"),
                "content_preview": " | ".join(content_bits)[:300] if content_bits else None,
                "created": data.get("created"),
            }
        )
    write_json("agentlogs_session_logs_readable.json", summary)


def main() -> None:
    assert AGENTLOGS.exists(), f"missing {AGENTLOGS}"
    extract_workflow_runs()
    extract_timelines()
    extract_repository()
    extract_users()
    extract_session_logs()
    print("done")


if __name__ == "__main__":
    main()
