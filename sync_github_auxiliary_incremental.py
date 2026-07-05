#!/usr/bin/env python3
"""
Fetch incremental GitHub PR activity for formerly-open cohort (98 changed + 49 still open)
and merge into MyStudy/finaldatabase/auxiliary/ (+ per_pr/).
Skips PRs that return 404 on GitHub API.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd
import requests

MYSTUDY = Path(__file__).resolve().parent
OUT = MYSTUDY / "finaldatabase"
AUX = OUT / "auxiliary"
CACHE_PATH = OUT / "summary" / "github_auxiliary_cache.json"
REPORT_PATH = OUT / "summary" / "auxiliary_incremental_report.json"
TOKEN_FILE = MYSTUDY / ".github_token"

SKIP_IDS = {3077259471, 3271610326}


def load_github_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token.strip()
    if TOKEN_FILE.exists():
        t = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if t:
            return t
    return None


def parse_pr_url(html_url: str) -> tuple[str, str, int]:
    parts = urlparse(html_url).path.strip("/").split("/")
    return parts[0], parts[1], int(parts[3])


def load_cache() -> dict[str, Any]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {"fetched": {}, "errors": {}}


def save_cache(cache: dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def wait_for_rate_limit(resp: requests.Response) -> None:
    if resp.status_code != 403:
        return
    remaining = resp.headers.get("X-RateLimit-Remaining")
    reset = resp.headers.get("X-RateLimit-Reset")
    try:
        msg = resp.json().get("message", "")
    except Exception:  # noqa: BLE001
        msg = resp.text[:200]
    if remaining != "0" and "rate limit" not in msg.lower():
        return
    wait_s = max(int(reset) - int(time.time()) + 2, 5) if reset else 60
    print(f"Rate limited (remaining={remaining}); sleeping {wait_s}s …")
    print("Tip: set GITHUB_TOKEN or create MyStudy/.github_token with a PAT (not SSH key).")
    time.sleep(wait_s)


def gh_get(session: requests.Session, url: str) -> Any:
    while True:
        resp = session.get(url, timeout=90)
        if resp.status_code == 403:
            wait_for_rate_limit(resp)
            continue
        resp.raise_for_status()
        return resp.json()


def gh_paginate(session: requests.Session, url: str) -> list[Any]:
    items: list[Any] = []
    while url:
        while True:
            resp = session.get(url, timeout=90)
            if resp.status_code == 403:
                wait_for_rate_limit(resp)
                continue
            resp.raise_for_status()
            break
        items.extend(resp.json())
        url = resp.links.get("next", {}).get("url")
    return items


def actor_login(obj: dict | None) -> str | None:
    if not obj:
        return None
    return obj.get("login") or obj.get("name")


def map_timeline_row(pr_id: int, ev: dict[str, Any]) -> dict[str, Any]:
    event = ev.get("event")
    row: dict[str, Any] = {
        "pr_id": pr_id,
        "event": event,
        "commit_id": None,
        "created_at": None,
        "actor": None,
        "assignee": None,
        "label": None,
        "message": None,
    }
    if event == "committed":
        row["commit_id"] = ev.get("sha")
        row["message"] = ev.get("message")
        row["actor"] = (ev.get("author") or {}).get("name")
    elif event == "commented":
        row["created_at"] = ev.get("created_at")
        row["actor"] = actor_login(ev.get("user") or ev.get("actor"))
        row["message"] = ev.get("body")
    elif event == "reviewed":
        row["commit_id"] = ev.get("commit_id")
    elif event == "labeled":
        label = ev.get("label")
        row["label"] = label.get("name") if isinstance(label, dict) else label
        row["created_at"] = ev.get("created_at")
        row["actor"] = actor_login(ev.get("actor"))
    elif event == "review_requested":
        row["created_at"] = ev.get("created_at")
        row["actor"] = actor_login(ev.get("review_requester") or ev.get("actor"))
        row["assignee"] = actor_login(ev.get("requested_reviewer"))
    else:
        row["created_at"] = ev.get("created_at")
        row["actor"] = actor_login(ev.get("actor"))
        assignee = ev.get("assignee")
        if assignee:
            row["assignee"] = actor_login(assignee) if isinstance(assignee, dict) else assignee
        label = ev.get("label")
        if label:
            row["label"] = label.get("name") if isinstance(label, dict) else label
    return row


def map_comment_row(pr_id: int, c: dict[str, Any]) -> dict[str, Any]:
    user = c.get("user") or {}
    return {
        "id": int(c["id"]),
        "pr_id": pr_id,
        "user": user.get("login"),
        "user_id": int(user["id"]) if user.get("id") is not None else None,
        "user_type": user.get("type"),
        "created_at": c.get("created_at"),
        "body": c.get("body"),
    }


def map_review_row(pr_id: int, r: dict[str, Any]) -> dict[str, Any]:
    user = r.get("user") or {}
    state = r.get("state") or ""
    return {
        "id": int(r["id"]),
        "pr_id": pr_id,
        "user": user.get("login"),
        "user_type": user.get("type"),
        "state": state.upper() if state else state,
        "submitted_at": r.get("submitted_at"),
        "body": r.get("body"),
    }


def map_review_comment_row(c: dict[str, Any]) -> dict[str, Any]:
    user = c.get("user") or {}
    return {
        "id": int(c["id"]),
        "pull_request_review_id": int(c["pull_request_review_id"])
        if c.get("pull_request_review_id") is not None
        else None,
        "user": user.get("login"),
        "user_type": user.get("type"),
        "diff_hunk": c.get("diff_hunk"),
        "path": c.get("path"),
        "position": c.get("position"),
        "original_position": c.get("original_position"),
        "commit_id": c.get("commit_id"),
        "original_commit_id": c.get("original_commit_id"),
        "body": c.get("body"),
        "pull_request_url": c.get("pull_request_url"),
        "created_at": c.get("created_at"),
        "updated_at": c.get("updated_at"),
        "in_reply_to_id": c.get("in_reply_to_id"),
    }


def map_commit_row(pr_id: int, c: dict[str, Any]) -> dict[str, Any]:
    commit = c.get("commit") or {}
    author = c.get("author") or commit.get("author") or {}
    committer = c.get("committer") or commit.get("committer") or {}
    return {
        "sha": c["sha"],
        "pr_id": pr_id,
        "author": author.get("login") or author.get("name"),
        "committer": committer.get("login") or committer.get("name"),
        "message": commit.get("message"),
    }


def tl_fingerprint(row: dict[str, Any]) -> tuple[Any, ...]:
    msg = row.get("message")
    msg_key = (str(msg)[:200] if msg is not None and not (isinstance(msg, float) and pd.isna(msg)) else "")
    return (
        int(row["pr_id"]),
        str(row.get("event") or ""),
        str(row.get("commit_id") or ""),
        str(row.get("created_at") or ""),
        str(row.get("actor") or ""),
        str(row.get("label") or ""),
        msg_key,
    )


def fetch_pr_bundle(session: requests.Session, pr_id: int, html_url: str) -> dict[str, Any]:
    owner, repo, number = parse_pr_url(html_url)
    base = f"https://api.github.com/repos/{owner}/{repo}"
    timeline = gh_get(session, f"{base}/issues/{number}/timeline")
    comments = gh_paginate(session, f"{base}/issues/{number}/comments?per_page=100")
    reviews = gh_paginate(session, f"{base}/pulls/{number}/reviews?per_page=100")
    review_comments = gh_paginate(session, f"{base}/pulls/{number}/comments?per_page=100")
    commits = gh_paginate(session, f"{base}/pulls/{number}/commits?per_page=100")
    return {
        "pr_id": pr_id,
        "html_url": html_url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "timeline": timeline,
        "comments": comments,
        "reviews": reviews,
        "review_comments": review_comments,
        "commits": commits,
    }


def convert_bundle(bundle: dict[str, Any]) -> dict[str, pd.DataFrame]:
    pr_id = int(bundle["pr_id"])
    timeline = pd.DataFrame([map_timeline_row(pr_id, ev) for ev in bundle.get("timeline", [])])
    comments = pd.DataFrame([map_comment_row(pr_id, c) for c in bundle.get("comments", [])])
    reviews = pd.DataFrame([map_review_row(pr_id, r) for r in bundle.get("reviews", [])])
    review_comments = pd.DataFrame([map_review_comment_row(c) for c in bundle.get("review_comments", [])])
    commits = pd.DataFrame([map_commit_row(pr_id, c) for c in bundle.get("commits", [])])
    return {
        "pr_timeline.parquet": timeline,
        "pr_comments.parquet": comments,
        "pr_reviews.parquet": reviews,
        "pr_review_comments_v2.parquet": review_comments,
        "pr_commits.parquet": commits,
    }


def merge_table(
    existing: pd.DataFrame,
    new_rows: pd.DataFrame,
    pr_id: int,
    *,
    table: str,
    reviews: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, int]:
    if table == "pr_review_comments_v2.parquet":
        rev_ids = set()
        if reviews is not None and not reviews.empty:
            rev_ids = set(reviews.loc[reviews["pr_id"] == pr_id, "id"].astype(int))
        if existing.empty:
            old_sub = pd.DataFrame()
            keep = pd.DataFrame()
        else:
            old_sub = existing[existing["pull_request_review_id"].isin(rev_ids)].copy()
            keep = existing[~existing["pull_request_review_id"].isin(rev_ids)].copy()
        new_sub = new_rows.copy()
    elif existing.empty and new_rows.empty:
        return existing, 0
    else:
        keep = existing[existing["pr_id"] != pr_id].copy() if not existing.empty and "pr_id" in existing.columns else existing.copy()
        old_sub = existing[existing["pr_id"] == pr_id].copy() if not existing.empty and "pr_id" in existing.columns else pd.DataFrame()
        new_sub = new_rows

    if table == "pr_timeline.parquet":
        seen = {tl_fingerprint(r) for _, r in old_sub.iterrows()}
        add_rows = []
        for _, r in new_rows.iterrows():
            fp = tl_fingerprint(r.to_dict())
            if fp not in seen:
                seen.add(fp)
                add_rows.append(r)
        merged_sub = pd.concat([old_sub, pd.DataFrame(add_rows)], ignore_index=True) if add_rows else old_sub
    elif table == "pr_commits.parquet":
        seen = set(zip(old_sub["pr_id"].astype(int), old_sub["sha"].astype(str))) if not old_sub.empty else set()
        add_rows = []
        for _, r in new_sub.iterrows():
            key = (int(r["pr_id"]), str(r["sha"]))
            if key not in seen:
                seen.add(key)
                add_rows.append(r)
        merged_sub = pd.concat([old_sub, pd.DataFrame(add_rows)], ignore_index=True) if add_rows else old_sub
    elif table == "pr_review_comments_v2.parquet":
        seen = set(old_sub["id"].astype(int)) if not old_sub.empty else set()
        add_rows = []
        for _, r in new_sub.iterrows():
            rid = int(r["id"])
            if rid not in seen:
                seen.add(rid)
                add_rows.append(r)
        merged_sub = pd.concat([old_sub, pd.DataFrame(add_rows)], ignore_index=True) if add_rows else old_sub
    else:
        id_col = "id"
        seen = set(old_sub[id_col].astype(int)) if not old_sub.empty else set()
        add_rows = []
        for _, r in new_sub.iterrows():
            rid = int(r[id_col])
            if rid not in seen:
                seen.add(rid)
                add_rows.append(r)
        merged_sub = pd.concat([old_sub, pd.DataFrame(add_rows)], ignore_index=True) if add_rows else old_sub

    added = len(merged_sub) - len(old_sub)
    out = pd.concat([keep, merged_sub], ignore_index=True) if not keep.empty else merged_sub
    return out, added


def write_per_pr_for_ids(pr_ids: set[int], tables: dict[str, pd.DataFrame]) -> None:
    per_pr = OUT / "per_pr"
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
        for pid, grp in rev.groupby("pr_id"):
            rev_ids_by_pr[int(pid)] = set(grp["id"].astype(int))

    all_tables = dict(tables)
    if "related_issue.parquet" not in all_tables and (AUX / "related_issue.parquet").exists():
        all_tables["related_issue.parquet"] = pd.read_parquet(AUX / "related_issue.parquet")
    if "pr_commit_details.parquet" not in all_tables and (AUX / "pr_commit_details.parquet").exists():
        all_tables["pr_commit_details.parquet"] = pd.read_parquet(AUX / "pr_commit_details.parquet")

    for pr_id in sorted(pr_ids):
        d = per_pr / str(pr_id)
        d.mkdir(parents=True, exist_ok=True)
        for fname, df in all_tables.items():
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
            out_path = d / short[fname]
            if not sub.empty:
                sub.to_parquet(out_path, index=False)
            elif out_path.exists():
                out_path.unlink()


def target_pr_ids() -> list[int]:
    master = pd.read_csv(OUT / "pr_master" / "perf_prs_expanded_final.csv")
    report_path = OUT / "summary" / "status_refresh_report.json"
    changed: set[int] = set()
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        changed = {int(c["id"]) for c in report.get("changes", [])}
    still_open = set(master.loc[master["state"] == "open", "id"].astype(int))
    targets = sorted((changed | still_open) - SKIP_IDS)
    return targets


def main() -> None:
    targets = target_pr_ids()
    master = pd.read_csv(OUT / "pr_master" / "perf_prs_expanded_final.csv")
    url_by_id = dict(zip(master["id"].astype(int), master["html_url"].astype(str)))

    cache = load_cache()
    session = requests.Session()
    session.headers.update({"Accept": "application/vnd.github+json", "User-Agent": "MyStudy-aux-incremental"})
    token = load_github_token()
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
        print("Using GitHub token (5000 req/h).")
    else:
        print("No token — unauthenticated limit ~60 req/h. Add MyStudy/.github_token or GITHUB_TOKEN.")
    delay = 0.2 if token else 1.2

    tables = {
        "pr_timeline.parquet": pd.read_parquet(AUX / "pr_timeline.parquet"),
        "pr_comments.parquet": pd.read_parquet(AUX / "pr_comments.parquet"),
        "pr_reviews.parquet": pd.read_parquet(AUX / "pr_reviews.parquet"),
        "pr_review_comments_v2.parquet": pd.read_parquet(AUX / "pr_review_comments_v2.parquet"),
        "pr_commits.parquet": pd.read_parquet(AUX / "pr_commits.parquet"),
    }

    per_pr_stats: list[dict[str, Any]] = []
    totals = {k: 0 for k in tables}

    print(f"Syncing GitHub auxiliary for {len(targets)} PRs (skipping {len(SKIP_IDS)} 404s) …")
    for i, pr_id in enumerate(targets, 1):
        pid = str(pr_id)
        html_url = url_by_id[pr_id]
        print(f"[{i}/{len(targets)}] {pr_id} …", flush=True)
        try:
            if pid in cache["fetched"]:
                bundle = cache["fetched"][pid]
            else:
                bundle = fetch_pr_bundle(session, pr_id, html_url)
                cache["fetched"][pid] = bundle
                save_cache(cache)
                time.sleep(delay)
        except Exception as exc:  # noqa: BLE001
            cache.setdefault("errors", {})[pid] = str(exc)
            save_cache(cache)
            print(f"  error: {exc}")
            continue

        converted = convert_bundle(bundle)
        pr_added: dict[str, int] = {}
        for fname, new_df in converted.items():
            tables[fname], added = merge_table(
                tables[fname],
                new_df,
                pr_id,
                table=fname,
                reviews=tables["pr_reviews.parquet"],
            )
            pr_added[fname] = added
            totals[fname] += added
        per_pr_stats.append({"pr_id": pr_id, "html_url": html_url, "added": pr_added})

        if i % 10 == 0:
            for fname, df in tables.items():
                df.to_parquet(AUX / fname, index=False)
            print(f"  checkpoint saved ({i}/{len(targets)})", flush=True)

    for fname, df in tables.items():
        df.to_parquet(AUX / fname, index=False)

    write_per_pr_for_ids(set(targets), tables)

    report = {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "target_pr_count": len(targets),
        "skipped_404_ids": sorted(SKIP_IDS),
        "rows_added_by_table": totals,
        "per_pr": per_pr_stats,
        "cache_errors": cache.get("errors", {}),
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Done.")
    for k, v in totals.items():
        print(f"  {k}: +{v} rows")


if __name__ == "__main__":
    main()
