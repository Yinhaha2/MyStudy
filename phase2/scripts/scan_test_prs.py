"""Find AIDev-7.6M pop PRs whose diff contains real test source files.

Streams pr_commit_details (filename only) from hao-li/AIDev-7.6M and keeps PRs
that add or modify a file named like a test, not merely a CI job or a fixture.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

OUT_DIR = Path(__file__).resolve().parents[1] / "archive" / "test_pr_scan"
HF = "hf://datasets/hao-li/AIDev-7.6M"

# Filename itself is a test module. Avoids tests/*.out, specs/*.md, *inspector*.
STRICT_TEST = re.compile(
    r"(?x)^(?:.*/)?"
    r"(?:"
    r"test_.+\.py"
    r"|tests\.py"
    r"|[^/]+_tests?\.py"
    r"|[^/]+_test\.go"
    r"|[^/]+_test\.rs"
    r"|[^/]+_spec\.rb"
    r"|[^/]+_test\.exs"
    r"|[^/]+\.(?:test|spec)\.(?:js|jsx|ts|tsx|mjs|cjs)"
    r"|[^/]+(?:Test|Tests)\.java"
    r"|[^/]+(?:Test|Tests)\.kt"
    r"|[^/]+(?:Test|Tests)\.scala"
    r"|[^/]+Test\.php"
    r"|[^/]+(?:Test|Tests)\.cs"
    r"|[^/]+_test\.(?:cc|cpp|cxx|c|h|hpp)"
    r")$"
)
SKIP_DIR = re.compile(
    r"(?i)(^|/)(testdata|fixtures|__snapshots__|node_modules|vendor|dist|third_party)(/|$)"
)

SELF_CHECK = [
    ("tests/test_mcp_reload.py", True),
    ("e2e/e2e_test.go", True),
    ("compiler_test.go", True),
    ("unit.test.ts", True),
    ("test/command-encoder.spec.ts", True),
    ("src/test/java/com/example/FooTest.java", True),
    ("pkg/manager_test.go", True),
    ("tests/sol1.out", False),
    ("tests/sol1.bench", False),
    ("tests/sol1.py", False),
    ("specs/technical-plan.md", False),
    ("testing.md", False),
    ("test.yml", False),
    ("set_inspector_handler.py", False),
    ("RUN_TESTS_force.rule", False),
    ("e2e/app.ts", False),
    ("test_crates/lib.rs", False),
]


def is_test_source(filename: str) -> bool:
    if not filename or SKIP_DIR.search(filename):
        return False
    return STRICT_TEST.match(filename.replace("\\", "/")) is not None


def outcome_of(state: str, merged_at) -> str:
    merged = merged_at is not None and str(merged_at) not in {"", "None", "NaT", "nan"}
    if merged:
        return "merged"
    if str(state).lower() == "open":
        return "open"
    return "closed_unmerged"


def scan_commit_details() -> tuple[dict[int, dict], dict]:
    pf = pq.ParquetFile(f"{HF}/pr_commit_details.parquet")
    stats = Counter()
    prs: dict[int, dict] = {}
    columns = ["pr_id", "filename", "status", "sha", "changes"]
    for batch in pf.iter_batches(batch_size=250_000, columns=columns):
        data = batch.to_pydict()
        n = len(data["pr_id"])
        stats["file_rows"] += n
        for i in range(n):
            pr_id = data["pr_id"][i]
            if pr_id is None:
                continue
            pr_id = int(pr_id)
            stats["rows_with_pr"] += 1
            name = data["filename"][i] or ""
            status = (data["status"][i] or "").lower()
            if not is_test_source(name):
                continue
            stats["test_file_rows"] += 1
            rec = prs.get(pr_id)
            if rec is None:
                rec = {
                    "added": 0,
                    "modified": 0,
                    "removed": 0,
                    "renamed": 0,
                    "names": [],
                    "sha": data["sha"][i] or "",
                    "example_file": name,
                    "example_changes": int(data["changes"][i] or 0),
                }
                prs[pr_id] = rec
            bucket = status if status in {"added", "modified", "removed", "renamed"} else "modified"
            rec[bucket] += 1
            if len(rec["names"]) < 5 and name not in rec["names"]:
                rec["names"].append(name)
            changes = int(data["changes"][i] or 0)
            # Prefer a newly added, human-sized test file as the example.
            if status == "added" and 20 <= changes <= 400:
                rec["sha"] = data["sha"][i] or rec["sha"]
                rec["example_file"] = name
                rec["example_changes"] = changes
        print(
            f"scanned_rows={stats['file_rows']} test_prs={len(prs)} test_rows={stats['test_file_rows']}",
            flush=True,
        )
    return prs, stats


def load_pr_table():
    table = pq.read_table(
        f"{HF}/pull_request.parquet",
        columns=["id", "number", "title", "agent", "state", "created_at", "merged_at", "repo_url", "html_url"],
    )
    return table.to_pydict()


def main() -> None:
    failed = [item for item in SELF_CHECK if is_test_source(item[0]) != item[1]]
    if failed:
        raise SystemExit(f"self-check failed: {failed}")

    prs, stats = scan_commit_details()
    meta = load_pr_table()
    by_outcome = Counter()
    by_agent = Counter()
    added_by_outcome = Counter()
    rows = []
    index = {int(i): k for k, i in enumerate(meta["id"]) if i is not None}

    for pr_id, rec in prs.items():
        touched = rec["added"] + rec["modified"] + rec["renamed"]
        if touched <= 0:
            stats["removed_only"] += 1
            continue
        pos = index.get(pr_id)
        if pos is None:
            stats["missing_pr_meta"] += 1
            continue
        state = meta["state"][pos]
        out = outcome_of(state, meta["merged_at"][pos])
        by_outcome[out] += 1
        agent = meta["agent"][pos] or ""
        by_agent[agent] += 1
        if rec["added"] > 0:
            added_by_outcome[out] += 1
        rows.append(
            {
                "pr_id": pr_id,
                "number": meta["number"][pos],
                "title": meta["title"][pos] or "",
                "agent": agent,
                "state": state,
                "outcome": out,
                "created_at": str(meta["created_at"][pos]),
                "repo_url": meta["repo_url"][pos] or "",
                "html_url": meta["html_url"][pos] or "",
                "n_added": rec["added"],
                "n_modified": rec["modified"],
                "n_renamed": rec["renamed"],
                "n_removed": rec["removed"],
                "example_file": rec["example_file"],
                "example_sha": rec["sha"],
                "example_changes": rec["example_changes"],
                "test_files": " | ".join(rec["names"]),
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Stable, readable sample first: added tests, then the rest.
    rows.sort(key=lambda r: (r["n_added"] == 0, r["outcome"], r["pr_id"]))
    csv_path = OUT_DIR / "prs_with_test_files.csv"
    import csv

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["pr_id"])
        writer.writeheader()
        writer.writerows(rows)

    pop_total = len(meta["id"])
    summary = {
        "dataset": "hao-li/AIDev-7.6M",
        "population": "pull_request (repos >100 stars) joined to pr_commit_details filenames",
        "pop_prs": pop_total,
        "file_rows_scanned": stats["file_rows"],
        "prs_with_added_or_modified_test_file": len(rows),
        "share_of_pop": round(len(rows) / pop_total, 4) if pop_total else None,
        "by_outcome": dict(by_outcome),
        "added_new_test_file_by_outcome": dict(added_by_outcome),
        "by_agent": dict(by_agent),
        "removed_test_only": stats["removed_only"],
        "missing_pr_meta": stats["missing_pr_meta"],
        "rule": "strict test-source filename; fixtures, specs markdown, and CI yaml excluded",
        "csv": str(csv_path),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
