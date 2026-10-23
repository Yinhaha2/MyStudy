"""Intersect test-file PRs with the SHA population and save two live examples."""

from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
TOKEN = Path(r"C:\Users\Y2698\Desktop\研究生\毕设\datebase\影子仓\.github_token").read_text(encoding="utf-8").strip()
CSV_PATH = HERE / "prs_with_test_files.csv"
OUT = HERE / "examples"
HF = "hf://datasets/hao-li/AIDev-7.6M"


def outcome(state, merged_at) -> str:
    merged = merged_at is not None and str(merged_at) not in {"", "None", "NaT", "nan"}
    if merged:
        return "merged"
    if str(state).lower() == "open":
        return "open"
    return "closed_unmerged"


def slug(url: str) -> str:
    parts = url.rstrip("/").split("/")
    return f"{parts[-2]}/{parts[-1]}"


def get(url: str, accept: str = "application/vnd.github+json"):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": accept,
            "User-Agent": "mystudy-test-scan",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            return resp.status, resp.read()
    except Exception as exc:
        raw = exc.read() if hasattr(exc, "read") else b""
        return getattr(exc, "code", None), raw


def main() -> None:
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    commits = pq.read_table(f"{HF}/pr_commits.parquet", columns=["pr_id"])
    sha_ids = {int(x) for x in commits.column("pr_id").to_pylist() if x is not None}
    prs = pq.read_table(f"{HF}/pull_request.parquet", columns=["id", "state", "merged_at"])
    meta = prs.to_pydict()
    den: Counter[str] = Counter()
    for i, pid in enumerate(meta["id"]):
        if int(pid) not in sha_ids:
            continue
        den[outcome(meta["state"][i], meta["merged_at"][i])] += 1

    touched: Counter[str] = Counter()
    added: Counter[str] = Counter()
    outside = 0
    for row in rows:
        if int(row["pr_id"]) not in sha_ids:
            outside += 1
            continue
        touched[row["outcome"]] += 1
        if int(row["n_added"]) > 0:
            added[row["outcome"]] += 1

    summary = {
        "sha_population": sum(den.values()),
        "denominator": dict(den),
        "prs_touching_test_file": dict(touched),
        "prs_touching_test_file_total": sum(touched.values()),
        "prs_adding_test_file": dict(added),
        "prs_adding_test_file_total": sum(added.values()),
        "outside_sha_set": outside,
        "touch_rate": {k: round(touched[k] / den[k], 4) for k in den},
        "add_rate": {k: round(added[k] / den[k], 4) for k in den},
    }
    print(json.dumps(summary, indent=2))
    (HERE / "sha_population_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    pool = [
        row
        for row in rows
        if int(row["n_added"]) > 0
        and row["example_file"].endswith(".py")
        and 40 <= int(row["example_changes"]) <= 160
        and int(row["pr_id"]) in sha_ids
    ]
    found: dict[str, dict] = {}
    checked = 0
    OUT.mkdir(parents=True, exist_ok=True)
    for row in pool:
        kind = row["outcome"]
        if kind not in {"closed_unmerged", "merged"} or kind in found:
            continue
        repo = slug(row["repo_url"])
        path = urllib.parse.quote(row["example_file"])
        status, body = get(
            f"https://api.github.com/repos/{repo}/contents/{path}?ref={row['example_sha']}",
            "application/vnd.github.raw",
        )
        checked += 1
        text = body.decode("utf-8", "replace")
        ok = status == 200 and ("def test_" in text or "assert " in text)
        print("probe", checked, status, ok, kind, row["html_url"], row["example_file"])
        if not ok:
            if checked >= 30:
                break
            continue
        status2, body2 = get(
            f"https://api.github.com/repos/{repo}/commits/{row['example_sha']}/check-runs?per_page=100"
        )
        checks = []
        if status2 == 200:
            for item in json.loads(body2).get("check_runs", []):
                name = item.get("name") or ""
                low = name.lower()
                if any(key in low for key in ("test", "pytest", "unittest", "e2e", "playwright")):
                    checks.append({"conclusion": item.get("conclusion"), "name": name})
        (OUT / f"{row['pr_id']}.py").write_text(text, encoding="utf-8")
        meta_out = {
            "pr_id": row["pr_id"],
            "html_url": row["html_url"],
            "title": row["title"],
            "agent": row["agent"],
            "outcome": kind,
            "file": row["example_file"],
            "sha": row["example_sha"],
            "changes": int(row["example_changes"]),
            "test_checks": checks,
        }
        (OUT / f"{row['pr_id']}.json").write_text(
            json.dumps(meta_out, indent=2), encoding="utf-8"
        )
        found[kind] = meta_out
        print("SAVED", row["pr_id"], "n_checks", len(checks))
        if len(found) == 2:
            break
        if checked >= 30:
            break
    print("checked", checked, "found", list(found))


if __name__ == "__main__":
    main()
