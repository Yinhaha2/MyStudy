#!/usr/bin/env python3
"""
Refresh formerly-open PR status via GitHub API, update master tables,
extract AIDev auxiliary data, and write MyStudy/finaldatabase/.
"""
from __future__ import annotations

import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
MYSTUDY = Path(__file__).resolve().parent
AIDEV = ROOT / "AIDev"
PAPER = ROOT / "AIDevPerf" / "LLM-performance" / "Outputs"
HF = "hf://datasets/hao-li/AIDev"

SRC_DB = MYSTUDY / "databasephase1"
OUT = MYSTUDY / "finaldatabase"
CACHE = OUT / "summary" / "github_status_cache.json"

PAPER_PERF_FINAL = PAPER / "PerformancePRs" / "POP_PULL_Requests_LLM_filtered_final.csv"
MASTER_CSV = SRC_DB / "pr_master" / "perf_prs_expanded_final.csv"


def attach_status(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ("created_at", "closed_at", "merged_at"):
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], utc=True, errors="coerce", format="mixed")
    out["status"] = np.select(
        [out["state"] == "open", out["merged_at"].notna()],
        ["open", "merged"],
        default="closed",
    )
    return out


def html_to_api_url(html_url: str) -> str:
    return html_url.replace("https://github.com/", "https://api.github.com/repos/").replace(
        "/pull/", "/pulls/"
    )


def load_cache() -> dict[str, Any]:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {"fetched": {}, "errors": {}}


def save_cache(cache: dict[str, Any]) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def wait_for_rate_limit(resp: requests.Response) -> None:
    if resp.status_code != 403:
        return
    reset = resp.headers.get("X-RateLimit-Reset")
    if not reset:
        time.sleep(60)
        return
    reset_ts = int(reset)
    now = int(time.time())
    wait_s = max(reset_ts - now + 2, 5)
    print(f"Rate limited; sleeping {wait_s}s until reset …")
    time.sleep(wait_s)


def fetch_github_status(session: requests.Session, html_url: str) -> dict[str, Any]:
    api = html_to_api_url(html_url)
    while True:
        resp = session.get(api, timeout=60)
        if resp.status_code == 403:
            wait_for_rate_limit(resp)
            continue
        resp.raise_for_status()
        data = resp.json()
        return {
            "state": data.get("state"),
            "merged_at": data.get("merged_at"),
            "closed_at": data.get("closed_at"),
            "updated_at": data.get("updated_at"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }


def refresh_open_prs(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    open_mask = df["state"] == "open"
    open_df = df[open_mask].copy()
    cache = load_cache()
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "User-Agent": "MyStudy-finaldatabase-status-refresh",
        }
    )
    token = __import__("os").environ.get("GITHUB_TOKEN")
    if token:
        session.headers["Authorization"] = f"Bearer {token}"

    changes: list[dict[str, Any]] = []
    for _, row in open_df.iterrows():
        pid = str(int(row["id"]))
        if pid in cache["fetched"]:
            live = cache["fetched"][pid]
        else:
            try:
                live = fetch_github_status(session, str(row["html_url"]))
                cache["fetched"][pid] = live
                save_cache(cache)
                time.sleep(0.3 if token else 1.0)
            except Exception as exc:  # noqa: BLE001
                cache["errors"][pid] = str(exc)
                save_cache(cache)
                continue

        old_state = row["state"]
        new_state = live.get("state", old_state)
        new_merged = live.get("merged_at")
        new_closed = live.get("closed_at")
        if new_state != old_state or (pd.isna(row.get("merged_at")) and new_merged):
            changes.append(
                {
                    "id": int(pid),
                    "html_url": row["html_url"],
                    "old_state": old_state,
                    "new_state": new_state,
                    "merged_at": new_merged,
                    "closed_at": new_closed,
                }
            )

    updated = df.copy()
    for col in ("merged_at", "closed_at"):
        if col in updated.columns:
            updated[col] = updated[col].astype(object)
    for ch in changes:
        idx = updated["id"] == ch["id"]
        updated.loc[idx, "state"] = ch["new_state"]
        if ch.get("merged_at"):
            updated.loc[idx, "merged_at"] = ch["merged_at"]
        if ch.get("closed_at"):
            updated.loc[idx, "closed_at"] = ch["closed_at"]

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "formerly_open_n": int(open_mask.sum()),
        "status_changed_n": len(changes),
        "still_open_n": int((updated.loc[open_mask.index, "state"] == "open").sum()) if len(open_df) else 0,
        "changes": changes,
        "cache_errors": cache.get("errors", {}),
    }
    return updated, report


def filter_table(path: Path | str, pr_ids: set[int], *, key: str = "pr_id") -> pd.DataFrame:
    p = Path(path) if not str(path).startswith("hf://") else path
    df = pd.read_parquet(p)
    return df[df[key].isin(pr_ids)].copy()


def parquet_source(name: str) -> str:
    local = AIDEV / name
    if local.exists():
        return str(local)
    return f"{HF}/{name}"


def build_master() -> pd.DataFrame:
    if MASTER_CSV.exists():
        master = pd.read_csv(MASTER_CSV)
    else:
        master = pd.read_csv(PAPER_PERF_FINAL)

    perf_llm_path = SRC_DB / "paper_source_copy" / "POP_PULL_Requests_LLM_filtered.csv"
    if not perf_llm_path.exists():
        perf_llm_path = PAPER / "PerformancePRs" / "POP_PULL_Requests_LLM_filtered.csv"
    perf_llm = pd.read_csv(perf_llm_path) if perf_llm_path.exists() else None

    pr_ids = set(master["id"].astype(int))
    only_in_final = set(master["id"]) - set(perf_llm["id"]) if perf_llm is not None else set()

    if "detection_source" not in master.columns:
        master["detection_source"] = np.where(
            master["id"].isin(only_in_final),
            "aidev_pr_task_type_perf_only",
            "llm_title_body_classifier",
        )

    return master


def write_per_pr_auxiliary(pr_ids: set[int], tables: dict[str, pd.DataFrame]) -> None:
    per_pr = OUT / "per_pr"
    per_pr.mkdir(parents=True, exist_ok=True)
    key_map = {
        "pr_commits.parquet": "pr_id",
        "pr_commit_details.parquet": "pr_id",
        "pr_reviews.parquet": "pr_id",
        "pr_comments.parquet": "pr_id",
        "pr_timeline.parquet": "pr_id",
        "related_issue.parquet": "pr_id",
        "pr_review_comments_v2.parquet": "pull_request_review_id",
    }
    short = {
        "pr_commits.parquet": "commits.parquet",
        "pr_commit_details.parquet": "commit_details.parquet",
        "pr_reviews.parquet": "reviews.parquet",
        "pr_comments.parquet": "comments.parquet",
        "pr_timeline.parquet": "timeline.parquet",
        "related_issue.parquet": "related_issue.parquet",
        "pr_review_comments_v2.parquet": "review_comments.parquet",
    }

    rev = tables.get("pr_reviews.parquet", pd.DataFrame())
    rev_ids_by_pr: dict[int, set[int]] = {}
    if not rev.empty:
        for pr_id, grp in rev.groupby("pr_id"):
            rev_ids_by_pr[int(pr_id)] = set(grp["id"].astype(int))

    for pr_id in sorted(pr_ids):
        d = per_pr / str(pr_id)
        d.mkdir(parents=True, exist_ok=True)
        for fname, df in tables.items():
            if df.empty:
                continue
            key = key_map.get(fname, "pr_id")
            if fname == "pr_review_comments_v2.parquet":
                rids = rev_ids_by_pr.get(pr_id, set())
                sub = df[df["pull_request_review_id"].isin(rids)]
            elif key in df.columns:
                sub = df[df[key] == pr_id]
            else:
                continue
            if not sub.empty:
                sub.to_parquet(d / short[fname], index=False)


def extract_auxiliary(pr_ids: set[int], repo_ids: pd.Series) -> dict[str, Any]:
    aux_dir = OUT / "auxiliary"
    aux_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        "pr_commits.parquet",
        "pr_commit_details.parquet",
        "pr_reviews.parquet",
        "pr_comments.parquet",
        "pr_timeline.parquet",
        "related_issue.parquet",
    ]
    tables: dict[str, pd.DataFrame] = {}
    coverage: dict[str, Any] = {"tables": {}}

    for fname in specs:
        sub = filter_table(parquet_source(fname), pr_ids)
        tables[fname] = sub
        if not sub.empty:
            sub.to_parquet(aux_dir / fname, index=False)
        key = "pr_id"
        coverage["tables"][fname] = {
            "rows": int(len(sub)),
            "prs_with_any_row": int(sub[key].nunique()) if len(sub) else 0,
        }

    rev = tables["pr_reviews.parquet"]
    if not rev.empty:
        cm = pd.read_parquet(parquet_source("pr_review_comments_v2.parquet"))
        cm_sub = cm[cm["pull_request_review_id"].isin(rev["id"])].copy()
        tables["pr_review_comments_v2.parquet"] = cm_sub
        cm_sub.to_parquet(aux_dir / "pr_review_comments_v2.parquet", index=False)
        coverage["tables"]["pr_review_comments_v2.parquet"] = {"rows": int(len(cm_sub))}
    else:
        tables["pr_review_comments_v2.parquet"] = pd.DataFrame()

    ri = tables["related_issue.parquet"]
    if not ri.empty:
        issues = pd.read_parquet(parquet_source("issue.parquet"))
        linked = issues[issues["id"].isin(ri["issue_id"])].copy()
        linked.to_parquet(aux_dir / "issues_linked.parquet", index=False)
        coverage["tables"]["issues_linked.parquet"] = {"rows": int(len(linked))}

    repo = pd.read_parquet(parquet_source("repository.parquet"))
    repo_sub = repo[repo["id"].isin(repo_ids.dropna().unique())]
    repo_sub.to_parquet(aux_dir / "repository.parquet", index=False)
    coverage["tables"]["repository.parquet"] = {"rows": int(len(repo_sub))}

    write_per_pr_auxiliary(pr_ids, tables)
    return coverage


def update_summary_docs(master: pd.DataFrame, refresh_report: dict[str, Any]) -> None:
    status_counts = master["status"].value_counts().to_dict()
    merged_pct = 100.0 * (master["status"] == "merged").mean()

    teacher_path = SRC_DB / "summary" / "report_stats_for_teacher.json"
    if teacher_path.exists():
        teacher = json.loads(teacher_path.read_text(encoding="utf-8"))
        teacher["status_counts"] = status_counts
        teacher["merged_pct_all_states"] = merged_pct
        teacher["status_refresh"] = {
            k: refresh_report[k]
            for k in ("checked_at", "formerly_open_n", "status_changed_n", "still_open_n", "cache_errors")
        }
        teacher_path.write_text(json.dumps(teacher, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_zh = MYSTUDY / "output" / "SUMMARY_zh.md"
    if summary_zh.exists():
        block = f"""
## 论文扩容集（1221 条）GitHub 状态复核

- 复核时间：{refresh_report['checked_at']}
- 原 open（未终态）：**{refresh_report['formerly_open_n']}** 条
- 状态已变更：**{refresh_report['status_changed_n']}** 条（其中新合并 {sum(1 for c in refresh_report.get('changes', []) if c.get('merged_at'))} 条，关闭未合并 {sum(1 for c in refresh_report.get('changes', []) if c['new_state'] == 'closed' and not c.get('merged_at'))} 条）
- 仍为 open：**{refresh_report['still_open_n']}** 条
- 更新后主表状态：merged **{status_counts.get('merged', 0)}** / closed **{status_counts.get('closed', 0)}** / open **{status_counts.get('open', 0)}**
- 合并率（含 open，`productivity.ipynb` 口径）：**{merged_pct:.2f}%**
- 明细：`MyStudy/finaldatabase/summary/status_refresh_report.json`
"""
        text = summary_zh.read_text(encoding="utf-8")
        marker = "## 论文扩容集（1221 条）GitHub 状态复核"
        if marker in text:
            text = text.split(marker)[0].rstrip() + block
        else:
            text = text.rstrip() + block
        summary_zh.write_text(text + "\n", encoding="utf-8")


def sync_databasephase1_auxiliary() -> None:
    src = OUT / "auxiliary"
    dst = SRC_DB / "auxiliary"
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.glob("*.parquet"):
        shutil.copy2(f, dst / f.name)


def update_output_files(changed_ids: set[int], refresh_report: dict[str, Any]) -> None:
    out_dir = MYSTUDY / "output"
    json_path = out_dir / "all_perfPR.json"
    if not json_path.exists():
        return

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    change_by_id = {c["id"]: c for c in refresh_report.get("changes", [])}
    updated_n = 0
    for row in payload.get("pull_requests", []):
        pid = row.get("id")
        if pid not in changed_ids:
            continue
        ch = change_by_id[pid]
        row["state"] = ch["new_state"]
        row["merged_at"] = ch["merged_at"]
        row["closed_at"] = ch["closed_at"]
        row["merged_flag"] = ch["merged_at"] is not None
        if ch["new_state"] == "open":
            row["status"] = "open"
        elif ch["merged_at"]:
            row["status"] = "merged"
        else:
            row["status"] = "closed"
        updated_n += 1

    payload.setdefault("meta", {})["status_refresh_at"] = refresh_report["checked_at"]
    payload["meta"]["status_refresh_changed_in_output"] = updated_n
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    metrics_path = out_dir / "summary_metrics.json"
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        metrics["paper_1221_status_refresh"] = {
            "checked_at": refresh_report["checked_at"],
            "formerly_open_n": refresh_report["formerly_open_n"],
            "status_changed_n": refresh_report["status_changed_n"],
            "still_open_n": refresh_report["still_open_n"],
            "output_all_perfPR_updated_n": updated_n,
        }
        metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")


def write_final_summary(master: pd.DataFrame, refresh_report: dict[str, Any], coverage: dict[str, Any]) -> None:
    status_counts = master["status"].value_counts().to_dict()
    summary = {
        "pr_count": len(master),
        "status_counts": status_counts,
        "status_refresh": refresh_report,
        "auxiliary": coverage,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (OUT / "summary" / "coverage_stats.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "summary" / "status_refresh_report.json").write_text(
        json.dumps(refresh_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def repair_status_from_report(master: pd.DataFrame, refresh_report: dict[str, Any]) -> pd.DataFrame:
    """Re-apply GitHub refresh fields (handles float merged_at column edge cases)."""
    out = master.copy()
    for col in ("merged_at", "closed_at"):
        if col in out.columns:
            out[col] = out[col].astype(object)
    for ch in refresh_report.get("changes", []):
        idx = out["id"] == ch["id"]
        out.loc[idx, "state"] = ch["new_state"]
        if ch.get("merged_at"):
            out.loc[idx, "merged_at"] = ch["merged_at"]
        if ch.get("closed_at"):
            out.loc[idx, "closed_at"] = ch["closed_at"]
    return attach_status(out)


def sync_databasephase1(master: pd.DataFrame, paper_cols: pd.DataFrame) -> None:
    """Update databasephase1 copies after refresh."""
    db = SRC_DB
    master.to_csv(db / "pr_master" / "perf_prs_expanded_final.csv", index=False)
    master.to_parquet(db / "pr_master" / "perf_prs_expanded_final.parquet", index=False)

    paper_out = paper_cols.copy()
    paper_out.to_csv(db / "paper_source_copy" / "POP_PULL_Requests_LLM_filtered_final.csv", index=False)

    if PAPER_PERF_FINAL.exists():
        paper_out.to_csv(PAPER_PERF_FINAL, index=False)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for sub in ("pr_master", "auxiliary", "per_pr", "classification", "summary", "paper_source_copy"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)

    master = build_master()
    paper_base_cols = [
        c
        for c in master.columns
        if c
        not in {
            "row_1based",
            "status",
            "detection_source",
            "aidev_task_type",
            "aidev_task_reason",
            "aidev_task_confidence",
            "Topic",
            "Probability",
            "Representative_document",
            "llm_output",
        }
    ]

    print(f"Refreshing GitHub status for formerly-open PRs …")
    refreshed, refresh_report = refresh_open_prs(master)
    report_path = OUT / "summary" / "status_refresh_report.json"
    if report_path.exists():
        prior = json.loads(report_path.read_text(encoding="utf-8"))
        merged_changes = {c["id"]: c for c in prior.get("changes", [])}
        merged_changes.update({c["id"]: c for c in refresh_report.get("changes", [])})
        refresh_report["changes"] = list(merged_changes.values())
        refresh_report["status_changed_n"] = len(refresh_report["changes"])
        refresh_report.setdefault("formerly_open_n", prior.get("formerly_open_n", refresh_report["formerly_open_n"]))
    refreshed = repair_status_from_report(master, refresh_report)
    refresh_report["still_open_n"] = int((refreshed["state"] == "open").sum())

    if "row_1based" not in refreshed.columns:
        refreshed.insert(0, "row_1based", np.arange(1, len(refreshed) + 1))

    # Save master
    refreshed.to_csv(OUT / "pr_master" / "perf_prs_expanded_final.csv", index=False)
    refreshed.to_parquet(OUT / "pr_master" / "perf_prs_expanded_final.parquet", index=False)

    paper_df = refreshed[paper_base_cols].copy()
    paper_df.to_csv(OUT / "paper_source_copy" / "POP_PULL_Requests_LLM_filtered_final.csv", index=False)
    paper_df.to_csv(OUT / "pr_master" / "POP_PULL_Requests_LLM_filtered_final.csv", index=False)

    # classification copies
    cls_src = SRC_DB / "classification"
    if cls_src.exists():
        for f in cls_src.glob("*"):
            if f.is_file():
                shutil.copy2(f, OUT / "classification" / f.name)

    pr_ids = set(refreshed["id"].astype(int))
    print("Extracting auxiliary tables …")
    coverage = extract_auxiliary(pr_ids, refreshed["repo_id"])
    coverage["pr_count"] = len(pr_ids)

    write_final_summary(refreshed, refresh_report, coverage)
    sync_databasephase1(refreshed, paper_df)

    changed_ids = {c["id"] for c in refresh_report.get("changes", [])}
    update_output_files(changed_ids, refresh_report)
    update_summary_docs(refreshed, refresh_report)
    sync_databasephase1_auxiliary()

    readme = f"""# finaldatabase

更新于 {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}

## 概要
- 性能 PR 主表：**{len(refreshed)}** 条
- 状态分布：{refreshed['status'].value_counts().to_dict()}
- 原 open PR 复核：**{refresh_report['formerly_open_n']}** 条，其中 **{refresh_report['status_changed_n']}** 条状态已变更

## 目录
- `pr_master/`：更新后的主表 CSV/Parquet
- `auxiliary/`：1221 PR 聚合附属表（parquet）
- `per_pr/{{pr_id}}/`：每条 PR 的独立 parquet 附属文件
- `summary/status_refresh_report.json`：GitHub 状态刷新明细
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    print("Done.")
    print(f"  formerly open: {refresh_report['formerly_open_n']}")
    print(f"  changed:       {refresh_report['status_changed_n']}")
    print(f"  still open:    {refresh_report['still_open_n']}")
    print(f"  wrote:         {OUT}")


if __name__ == "__main__":
    main()
