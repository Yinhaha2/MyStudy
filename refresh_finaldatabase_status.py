#!/usr/bin/env python3
"""
Re-scan GitHub for open PR status changes and remove deleted (404) PRs
from MyStudy/finaldatabase/.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

MYSTUDY = Path(__file__).resolve().parent
OUT = MYSTUDY / "finaldatabase"
CACHE = OUT / "summary" / "github_status_cache.json"
TOKEN_FILE = MYSTUDY / ".github_token"

PAPER_BASE_EXCLUDE = {
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

AUX_KEY_MAP = {
    "pr_commits.parquet": "pr_id",
    "pr_commit_details.parquet": "pr_id",
    "pr_reviews.parquet": "pr_id",
    "pr_comments.parquet": "pr_id",
    "pr_timeline.parquet": "pr_id",
    "related_issue.parquet": "pr_id",
    "pr_review_comments_v2.parquet": "pull_request_review_id",
    "issues_linked.parquet": "id",
    "repository.parquet": "id",
}


def load_github_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token.strip()
    if TOKEN_FILE.exists():
        t = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if t:
            return t
    return None


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
    wait_s = max(int(reset) - int(time.time()) + 2, 5)
    print(f"Rate limited; sleeping {wait_s}s …")
    time.sleep(wait_s)


def fetch_github_status(session: requests.Session, html_url: str) -> dict[str, Any]:
    api = html_to_api_url(html_url)
    while True:
        resp = session.get(api, timeout=60)
        if resp.status_code == 403:
            wait_for_rate_limit(resp)
            continue
        if resp.status_code == 404:
            return {"deleted": True, "fetched_at": datetime.now(timezone.utc).isoformat()}
        if resp.status_code == 401:
            raise RuntimeError("GitHub token unauthorized (401). Update MyStudy/.github_token or GITHUB_TOKEN.")
        if resp.status_code >= 400:
            return {
                "deleted": False,
                "error": f"HTTP {resp.status_code}",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        data = resp.json()
        return {
            "deleted": False,
            "state": data.get("state"),
            "merged_at": data.get("merged_at"),
            "closed_at": data.get("closed_at"),
            "updated_at": data.get("updated_at"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }


def scan_prs(master: pd.DataFrame, session: requests.Session, token: str | None) -> dict[str, Any]:
    cache = load_cache()
    delay = 0.25 if token else 1.0

    open_df = master[master["state"] == "open"].copy()
    open_ids = set(open_df["id"].astype(int))

    status_changes: list[dict[str, Any]] = []
    deleted: list[dict[str, Any]] = []
    fetch_errors: dict[str, str] = {}

    # 1) Re-scan all currently open PRs for status changes / 404
    for n, (_, row) in enumerate(open_df.iterrows(), 1):
        pid = int(row["id"])
        pid_s = str(pid)
        html_url = str(row["html_url"])
        print(f"[open {n}/{len(open_df)}] {pid} …", flush=True)
        live = fetch_github_status(session, html_url)
        cache["fetched"][pid_s] = live
        save_cache(cache)
        time.sleep(delay)

        if live.get("deleted"):
            deleted.append({"id": pid, "html_url": html_url, "former_state": row["state"]})
            continue
        if live.get("error"):
            fetch_errors[pid_s] = live["error"]
            continue

        old_state = row["state"]
        new_state = live.get("state", old_state)
        new_merged = live.get("merged_at")
        new_closed = live.get("closed_at")
        if new_state != old_state or (pd.isna(row.get("merged_at")) and new_merged):
            status_changes.append(
                {
                    "id": pid,
                    "html_url": html_url,
                    "old_state": old_state,
                    "new_state": new_state,
                    "merged_at": new_merged,
                    "closed_at": new_closed,
                }
            )

    # 2) Verify known / cached-deleted PRs (404 cohort)
    extra_check_ids: set[int] = {3077259471, 3271610326}
    for pid_s, cached in cache.get("fetched", {}).items():
        if cached.get("deleted"):
            extra_check_ids.add(int(pid_s))
    prior_report = OUT / "summary" / "status_refresh_report.json"
    if prior_report.exists():
        prior = json.loads(prior_report.read_text(encoding="utf-8"))
        for pid_s in prior.get("cache_errors", {}):
            extra_check_ids.add(int(pid_s))
        for item in prior.get("deleted_prs_removed", []):
            extra_check_ids.add(int(item["id"]))

    already_handled = open_ids | {d["id"] for d in deleted}
    for pid in sorted(extra_check_ids - already_handled):
        row = master[master["id"] == pid]
        if row.empty:
            continue
        pid_s = str(pid)
        html_url = str(row.iloc[0]["html_url"])
        print(f"[404 check] {pid} …", flush=True)
        live = fetch_github_status(session, html_url)
        cache["fetched"][pid_s] = live
        save_cache(cache)
        time.sleep(delay)
        if live.get("deleted"):
            deleted.append(
                {"id": pid, "html_url": html_url, "former_state": row.iloc[0]["state"]}
            )
        elif live.get("error"):
            fetch_errors[pid_s] = live["error"]

    save_cache(cache)

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "open_rescanned_n": len(open_df),
        "new_status_changes": status_changes,
        "deleted_prs": deleted,
        "fetch_errors": fetch_errors,
    }


def apply_status_changes(master: pd.DataFrame, changes: list[dict[str, Any]]) -> pd.DataFrame:
    out = master.copy()
    for col in ("merged_at", "closed_at"):
        if col in out.columns:
            out[col] = out[col].astype(object)
    for ch in changes:
        idx = out["id"] == ch["id"]
        out.loc[idx, "state"] = ch["new_state"]
        if ch.get("merged_at"):
            out.loc[idx, "merged_at"] = ch["merged_at"]
        if ch.get("closed_at"):
            out.loc[idx, "closed_at"] = ch["closed_at"]
    return attach_status(out)


def remove_prs(master: pd.DataFrame, remove_ids: set[int]) -> pd.DataFrame:
    out = master[~master["id"].isin(remove_ids)].copy()
    out = out.reset_index(drop=True)
    if "row_1based" in out.columns:
        out["row_1based"] = np.arange(1, len(out) + 1)
    return attach_status(out)


def filter_auxiliary(remove_ids: set[int]) -> dict[str, int]:
    aux_dir = OUT / "auxiliary"
    stats: dict[str, int] = {}
    if not aux_dir.exists():
        return stats

    rev_by_pr: dict[int, set[int]] = {}
    rev_path = aux_dir / "pr_reviews.parquet"
    if rev_path.exists():
        rev = pd.read_parquet(rev_path)
        if not rev.empty:
            for pr_id, grp in rev.groupby("pr_id"):
                rev_by_pr[int(pr_id)] = set(grp["id"].astype(int))

    for fpath in sorted(aux_dir.glob("*.parquet")):
        df = pd.read_parquet(fpath)
        before = len(df)
        fname = fpath.name
        key = AUX_KEY_MAP.get(fname, "pr_id")
        if fname == "pr_review_comments_v2.parquet":
            removed_rids: set[int] = set()
            for pid in remove_ids:
                removed_rids |= rev_by_pr.get(pid, set())
            sub = df[~df["pull_request_review_id"].isin(removed_rids)]
        elif fname == "issues_linked.parquet":
            ri_path = aux_dir / "related_issue.parquet"
            if ri_path.exists():
                ri = pd.read_parquet(ri_path)
                keep_issues = set(ri.loc[~ri["pr_id"].isin(remove_ids), "issue_id"].astype(int))
                sub = df[df["id"].isin(keep_issues)] if "id" in df.columns else df
            else:
                sub = df
        elif key in df.columns:
            sub = df[~df[key].isin(remove_ids)]
        else:
            sub = df
        sub.to_parquet(fpath, index=False)
        stats[fname] = before - len(sub)

    return stats


def remove_per_pr_dirs(remove_ids: set[int]) -> int:
    per_pr = OUT / "per_pr"
    removed = 0
    if not per_pr.exists():
        return removed
    for pid in remove_ids:
        d = per_pr / str(pid)
        if d.exists():
            shutil.rmtree(d)
            removed += 1
    return removed


def merge_refresh_report(scan: dict[str, Any], master: pd.DataFrame) -> dict[str, Any]:
    prior_path = OUT / "summary" / "status_refresh_report.json"
    prior_changes: dict[int, dict[str, Any]] = {}
    formerly_open_n = int((master["state"] == "open").sum()) + len(
        [c for c in scan["new_status_changes"] if c["old_state"] == "open"]
    )
    if prior_path.exists():
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        formerly_open_n = prior.get("formerly_open_n", formerly_open_n)
        for c in prior.get("changes", []):
            prior_changes[int(c["id"])] = c

    for c in scan["new_status_changes"]:
        prior_changes[int(c["id"])] = c

    all_changes = list(prior_changes.values())
    still_open_n = int((master["state"] == "open").sum())

    return {
        "checked_at": scan["checked_at"],
        "formerly_open_n": formerly_open_n,
        "status_changed_n": len(all_changes),
        "still_open_n": still_open_n,
        "open_rescanned_n": scan["open_rescanned_n"],
        "new_status_changes_this_run": scan["new_status_changes"],
        "deleted_prs_removed": scan["deleted_prs"],
        "changes": all_changes,
        "cache_errors": load_cache().get("errors", {}),
    }


def write_outputs(master: pd.DataFrame, report: dict[str, Any], aux_removed: dict[str, int]) -> None:
    paper_cols = [c for c in master.columns if c not in PAPER_BASE_EXCLUDE]
    paper_df = master[paper_cols].copy()

    pr_master = OUT / "pr_master"
    pr_master.mkdir(parents=True, exist_ok=True)
    master.to_csv(pr_master / "perf_prs_expanded_final.csv", index=False)
    master.to_parquet(pr_master / "perf_prs_expanded_final.parquet", index=False)
    paper_df.to_csv(pr_master / "POP_PULL_Requests_LLM_filtered_final.csv", index=False)

    paper_copy = OUT / "paper_source_copy"
    paper_copy.mkdir(parents=True, exist_ok=True)
    paper_df.to_csv(paper_copy / "POP_PULL_Requests_LLM_filtered_final.csv", index=False)

    status_counts = master["status"].value_counts().to_dict()
    coverage = {
        "pr_count": len(master),
        "status_counts": status_counts,
        "status_refresh": report,
        "auxiliary_rows_removed": aux_removed,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if (OUT / "summary" / "coverage_stats.json").exists():
        old = json.loads((OUT / "summary" / "coverage_stats.json").read_text(encoding="utf-8"))
        if "auxiliary" in old:
            coverage["auxiliary"] = old["auxiliary"]

    summary_dir = OUT / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)
    (summary_dir / "coverage_stats.json").write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (summary_dir / "status_refresh_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    readme = f"""# finaldatabase

更新于 {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}

## 概要
- 性能 PR 主表：**{len(master)}** 条
- 状态分布：{status_counts}
- 原 open PR 复核：**{report['formerly_open_n']}** 条，其中 **{report['status_changed_n']}** 条状态已变更
- 本次 open 重扫：**{report['open_rescanned_n']}** 条，新变更 **{len(report['new_status_changes_this_run'])}** 条
- 已删除 PR 移出：**{len(report['deleted_prs_removed'])}** 条

## 目录
- `pr_master/`：更新后的主表 CSV/Parquet
- `auxiliary/`：PR 聚合附属表（parquet）
- `per_pr/{{pr_id}}/`：每条 PR 的独立 parquet 附属文件
- `summary/status_refresh_report.json`：GitHub 状态刷新明细
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    master_path = OUT / "pr_master" / "perf_prs_expanded_final.csv"
    if not master_path.exists():
        raise SystemExit(f"Missing master table: {master_path}")

    master = pd.read_csv(master_path)
    master = attach_status(master)
    print(f"Loaded {len(master)} PRs; {int((master['state'] == 'open').sum())} currently open.")

    session = requests.Session()
    session.headers.update(
        {"Accept": "application/vnd.github+json", "User-Agent": "MyStudy-finaldatabase-status-refresh"}
    )
    token = load_github_token()
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
        print("Using GitHub token.")
    else:
        print("No GitHub token — rate limits will be tight.")

    scan = scan_prs(master, session, token)

    remove_ids = {d["id"] for d in scan["deleted_prs"]}
    updated = apply_status_changes(master, scan["new_status_changes"])
    if remove_ids:
        print(f"Removing {len(remove_ids)} deleted PR(s): {sorted(remove_ids)}")
        updated = remove_prs(updated, remove_ids)
        aux_removed = filter_auxiliary(remove_ids)
        per_pr_removed = remove_per_pr_dirs(remove_ids)
        print(f"  per_pr dirs removed: {per_pr_removed}")
    else:
        aux_removed = {}
        per_pr_removed = 0

    report = merge_refresh_report(scan, updated)
    write_outputs(updated, report, aux_removed)

    print("\nDone.")
    print(f"  open rescanned:     {scan['open_rescanned_n']}")
    print(f"  new status changes: {len(scan['new_status_changes'])}")
    print(f"  still open:         {report['still_open_n']}")
    print(f"  deleted removed:    {len(remove_ids)}")
    print(f"  final pr count:     {len(updated)}")


if __name__ == "__main__":
    main()
