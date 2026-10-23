"""Find added test files whose commit also has a finished test-named check."""

from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOKEN = Path(r"C:\Users\Y2698\Desktop\研究生\毕设\datebase\影子仓\.github_token").read_text(encoding="utf-8").strip()
CSV_PATH = HERE / "prs_with_test_files.csv"
OUT = HERE / "examples"
KEYS = ("test", "pytest", "unittest", "e2e", "playwright")


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
    pool = [
        row
        for row in rows
        if int(row["n_added"]) > 0
        and row["example_file"].endswith(".py")
        and 40 <= int(row["example_changes"]) <= 180
        and row["outcome"] in {"closed_unmerged", "merged"}
    ]
    pool.sort(key=lambda row: int(row["pr_id"]), reverse=True)
    found: dict[str, dict] = {}
    checked = 0
    for row in pool:
        kind = row["outcome"]
        if kind in found:
            continue
        repo = slug(row["repo_url"])
        status, body = get(
            f"https://api.github.com/repos/{repo}/commits/{row['example_sha']}/check-runs?per_page=100"
        )
        checked += 1
        if status != 200:
            print("probe", checked, "checks", status, kind, row["html_url"])
            if checked >= 40:
                break
            continue
        hits = []
        for item in json.loads(body).get("check_runs", []):
            name = item.get("name") or ""
            low = name.lower()
            conclusion = item.get("conclusion")
            if any(key in low for key in KEYS) and conclusion in {"success", "failure"}:
                hits.append({"conclusion": conclusion, "name": name})
        print(
            "probe",
            checked,
            "hits",
            len(hits),
            "total",
            json.loads(body).get("total_count"),
            kind,
            row["html_url"],
        )
        if not hits:
            if checked >= 40:
                break
            continue
        path = urllib.parse.quote(row["example_file"])
        file_status, file_body = get(
            f"https://api.github.com/repos/{repo}/contents/{path}?ref={row['example_sha']}",
            "application/vnd.github.raw",
        )
        text = file_body.decode("utf-8", "replace")
        if file_status != 200 or "def test_" not in text or "assert" not in text:
            print("  file rejected", file_status)
            if checked >= 40:
                break
            continue
        (OUT / f"{row['pr_id']}_ci.py").write_text(text, encoding="utf-8")
        meta = {
            "pr_id": row["pr_id"],
            "html_url": row["html_url"],
            "title": row["title"],
            "agent": row["agent"],
            "outcome": kind,
            "file": row["example_file"],
            "sha": row["example_sha"],
            "changes": int(row["example_changes"]),
            "test_checks": hits[:12],
        }
        (OUT / f"{row['pr_id']}_ci.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        found[kind] = meta
        print("SAVED", row["pr_id"], hits[0]["name"], hits[0]["conclusion"])
        if len(found) == 2 or checked >= 40:
            break
    print("checked", checked, "found", list(found))


if __name__ == "__main__":
    main()
