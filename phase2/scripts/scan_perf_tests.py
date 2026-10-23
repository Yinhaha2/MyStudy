"""Find performance tests among PRs whose repos already have a test suite.

A file counts as a performance test when its path is a bench/benchmark suite,
or when a perf/performance directory holds an actual test source file.
Ordinary unit tests are left out.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

HF = "hf://datasets/hao-li/AIDev-7.6M"
OUT = Path(__file__).resolve().parents[1] / "archive" / "test_pr_scan"
POPULATION = OUT / "prs_in_repos_with_existing_tests.csv"

SKIP_DIR = re.compile(
    r"(?i)(^|/)(testdata|fixtures|__snapshots__|node_modules|vendor|dist|third_party|examples|samples|cmd|tools)(/|$)"
)
NAMED_PERF_TEST = re.compile(
    r"""(?ix)
    (?:^|/)(?:
        .+_benchmark_test\.go
        | .+_bench_test\.go
        | bench_test\.go
        | .+\.bench\.(?:js|jsx|ts|tsx|mjs|cjs)
        | .+(?:Benchmark|PerfTest|PerformanceTest)\.java
        | .+(?:Macrobenchmark|Benchmark)\.kt
        | .+Benchmark\.cs
        | test_(?:perf|performance|benchmark)_.+\.py
        | bench_.+\.py
        | .+_benchmark\.py
        | .+_bench\.py
        | .+_benchmark\.(?:cc|cpp|cxx|c)
    )$
    """
)
BENCH_DIR_CASE = re.compile(
    r"(?i)(?:^|/)(?:bench|benches|benchmark|benchmarks|jmh)(?:/|.*)/(?:test_.+\.py|.+_test\.go|.+_benchmark\.py|bench_.+\.py)$"
)
RUST_BENCH = re.compile(r"(?i)(?:^|/)benches/.+\.rs$")
CPP_BENCH = re.compile(r"(?i)(?:^|/)bench/.+\.(?:c|cc|cpp|h|hpp)$")
PERF_DIR_TEST = re.compile(
    r"(?i)(?:^|/)(?:perf|performance)/(?:.+/)?(?:test_.+\.py|.+_test\.go|.+_benchmark_test\.go)$"
)

SELF_CHECK = [
    ("benches/decode.rs", True),
    ("tests/benchmarks/test_speed.py", True),
    ("pkg/foo_benchmark_test.go", True),
    ("src/test/java/com/example/FooBenchmark.java", True),
    ("benchmarks/simple_benchmark.py", True),
    ("src/bench/crypto_hash.cpp", True),
    ("tests/perf/test_latency.py", True),
    ("web/api.bench.ts", True),
    ("tests/test_foo.py", False),
    ("src/perfect.py", False),
    ("docs/performance.md", False),
    ("tests/test_perform_action.py", False),
    ("tests/test_benchmark.py", False),
    ("benchmarks/__init__.py", False),
    ("cmd/tools/benchmark/job/doc.go", False),
    ("examples/bench/bench.c", False),
    ("bench/runner.go", False),
    ("Microsoft.Azure.Cosmos.Samples/Tools/Benchmark/Program.cs", False),
]


def is_perf_test(filename: str) -> bool:
    if not filename:
        return False
    path = filename.replace("\\", "/")
    if SKIP_DIR.search(path):
        return False
    base = path.rsplit("/", 1)[-1]
    low = base.lower()
    if low in {"__init__.py", "conftest.py", "doc.go", "main.go", "main.rs", "lib.rs", "mod.rs", "program.cs"}:
        return False
    if low == "test_benchmark.py" or "config" in low:
        return False
    if (
        NAMED_PERF_TEST.search(path)
        or BENCH_DIR_CASE.search(path)
        or CPP_BENCH.search(path)
        or PERF_DIR_TEST.search(path)
    ):
        return True
    if RUST_BENCH.search(path) and low not in {"main.rs", "lib.rs", "mod.rs"}:
        return True
    return False


def main() -> None:
    failed = [item for item in SELF_CHECK if is_perf_test(item[0]) != item[1]]
    if failed:
        raise SystemExit(f"self-check failed: {failed}")

    population = list(csv.DictReader(POPULATION.open(encoding="utf-8")))
    pop_ids = {int(row["pr_id"]) for row in population}
    meta = {int(row["pr_id"]): row for row in population}

    pf = pq.ParquetFile(f"{HF}/pr_commit_details.parquet")
    touched: dict[int, dict] = {}
    repo_hits: dict[str, list[str]] = defaultdict(list)
    file_rows = 0
    for batch in pf.iter_batches(batch_size=250_000, columns=["pr_id", "filename", "status"]):
        data = batch.to_pydict()
        file_rows += len(data["pr_id"])
        for pr_id, filename, status in zip(data["pr_id"], data["filename"], data["status"]):
            if pr_id is None or int(pr_id) not in pop_ids:
                continue
            name = filename or ""
            if not is_perf_test(name):
                continue
            pr_id = int(pr_id)
            bucket = (status or "").lower()
            if bucket not in {"added", "modified", "renamed", "removed"}:
                bucket = "modified"
            rec = touched.get(pr_id)
            if rec is None:
                rec = {"added": 0, "modified": 0, "renamed": 0, "removed": 0, "names": []}
                touched[pr_id] = rec
            rec[bucket] += 1
            if len(rec["names"]) < 5 and name not in rec["names"]:
                rec["names"].append(name)
            repo = meta[pr_id]["repo"]
            if bucket == "modified" and len(repo_hits[repo]) < 5 and name not in repo_hits[repo]:
                repo_hits[repo].append(name)
        print(f"scanned_rows={file_rows} perf_prs={len(touched)}", flush=True)

    direct_rows = []
    by_outcome = Counter()
    added_by_outcome = Counter()
    for pr_id, rec in touched.items():
        if rec["added"] + rec["modified"] + rec["renamed"] <= 0:
            continue
        info = meta[pr_id]
        by_outcome[info["outcome"]] += 1
        if rec["added"] > 0:
            added_by_outcome[info["outcome"]] += 1
        direct_rows.append(
            {
                "pr_id": pr_id,
                "number": info["number"],
                "outcome": info["outcome"],
                "agent": info["agent"],
                "repo": info["repo"],
                "html_url": info["html_url"],
                "n_added": rec["added"],
                "n_modified": rec["modified"],
                "n_renamed": rec["renamed"],
                "perf_files": " | ".join(rec["names"]),
            }
        )

    repos_with_existing = set(repo_hits)
    repo_rows = [row for row in population if row["repo"] in repos_with_existing]
    repo_outcome = Counter(row["outcome"] for row in repo_rows)
    pop_outcome = Counter(row["outcome"] for row in population)

    direct_rows.sort(key=lambda row: (row["outcome"], int(row["pr_id"])))
    csv_path = OUT / "prs_with_perf_tests.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(direct_rows[0].keys()) if direct_rows else ["pr_id"])
        writer.writeheader()
        writer.writerows(direct_rows)

    repo_csv = OUT / "prs_in_repos_with_perf_tests.csv"
    with repo_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["pr_id", "number", "outcome", "agent", "repo", "html_url", "perf_files"],
        )
        writer.writeheader()
        for row in repo_rows:
            writer.writerow(
                {
                    "pr_id": row["pr_id"],
                    "number": row["number"],
                    "outcome": row["outcome"],
                    "agent": row["agent"],
                    "repo": row["repo"],
                    "html_url": row["html_url"],
                    "perf_files": " | ".join(repo_hits.get(row["repo"], [])),
                }
            )

    summary = {
        "population_prs": len(population),
        "population_by_outcome": dict(pop_outcome),
        "prs_that_touch_a_perf_test": len(direct_rows),
        "touch_by_outcome": dict(by_outcome),
        "touch_added_by_outcome": dict(added_by_outcome),
        "repos_with_existing_perf_test": len(repos_with_existing),
        "prs_in_those_repos": len(repo_rows),
        "repo_level_by_outcome": dict(repo_outcome),
        "rule": "benchmark test filename, benches/*.rs, src/bench C++ cases, or test_*.py under a bench/perf directory; harness files and examples excluded",
        "direct_csv": str(csv_path),
        "repo_csv": str(repo_csv),
    }
    (OUT / "perf_test_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
