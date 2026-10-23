"""Extract every PR whose repository contains a performance test.

The PR's own diff does not have to edit that file. A repository qualifies when
any commit we can see in AIDev-7.6M touches a performance-test path.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

from scan_perf_tests import is_perf_test

HF = "hf://datasets/hao-li/AIDev-7.6M"
PHASE = Path(__file__).resolve().parents[1]
DATA = PHASE / "data"
DOCS = PHASE / "docs"


def outcome_of(state: str, merged_at) -> str:
    merged = merged_at is not None and str(merged_at) not in {"", "None", "NaT", "nan"}
    if merged:
        return "merged"
    if str(state).lower() == "open":
        return "open"
    return "closed_unmerged"


def slug(url: str) -> str:
    parts = (url or "").rstrip("/").split("/")
    if len(parts) < 2:
        return ""
    return f"{parts[-2]}/{parts[-1]}"


def load_population() -> list[dict]:
    commits = pq.read_table(f"{HF}/pr_commits.parquet", columns=["pr_id"])
    sha_ids = {int(item) for item in commits.column("pr_id").to_pylist() if item is not None}
    table = pq.read_table(
        f"{HF}/pull_request.parquet",
        columns=["id", "number", "state", "merged_at", "repo_url", "html_url", "agent"],
    )
    meta = table.to_pydict()
    rows = []
    for index, pr_id in enumerate(meta["id"]):
        pr_id = int(pr_id)
        if pr_id not in sha_ids:
            continue
        rows.append(
            {
                "pr_id": pr_id,
                "number": meta["number"][index],
                "outcome": outcome_of(meta["state"][index], meta["merged_at"][index]),
                "agent": meta["agent"][index] or "",
                "repo": slug(meta["repo_url"][index] or ""),
                "html_url": meta["html_url"][index] or "",
            }
        )
    return rows


def repos_with_perf_tests(pr_repo: dict[int, str]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = defaultdict(list)
    parquet = pq.ParquetFile(f"{HF}/pr_commit_details.parquet")
    seen = 0
    for batch in parquet.iter_batches(batch_size=250_000, columns=["pr_id", "filename", "status"]):
        data = batch.to_pydict()
        seen += len(data["pr_id"])
        for pr_id, filename, status in zip(data["pr_id"], data["filename"], data["status"]):
            if pr_id is None:
                continue
            repo = pr_repo.get(int(pr_id))
            if not repo:
                continue
            name = filename or ""
            if not is_perf_test(name):
                continue
            if (status or "").lower() == "removed":
                continue
            names = found[repo]
            if name not in names and len(names) < 5:
                names.append(name)
        print(f"scanned_rows={seen} repos_with_perf_tests={len(found)}", flush=True)
    return found


def write_readme(rows: list[dict], repo_files: dict[str, list[str]], population_n: int) -> None:
    outcome_name = {"merged": "已合并", "closed_unmerged": "关掉未合并", "open": "仍 open"}
    by_outcome = Counter(row["outcome"] for row in rows)
    by_agent = Counter(row["agent"] for row in rows)
    by_repo = Counter(row["repo"] for row in rows)
    lines = [
        "## 怎么判定",
        "",
        f"先取有 commit SHA 的 {population_n:,} 条 PR。某个仓库只要在这些提交里出现过性能测试路径，就视为这个仓库有性能测试，该仓库下的全部 PR 都列入。",
        "",
        "性能测试路径包括：",
        "",
        "- `*_benchmark_test.go`、`*_bench_test.go`、`bench_test.go`",
        "- `benches/*.rs`",
        "- `*.bench.ts` / `*.bench.js`",
        "- `*Benchmark.java`、`*PerfTest.java`、`*Macrobenchmark.kt`、`*Benchmark.cs`",
        "- `bench/`、`benchmarks/`、`perf/`、`performance/` 目录下的 `test_*.py` 或 `*_benchmark.py`",
        "- `src/bench/` 下的 C/C++ 基准用例",
        "",
        "基准目录里的脚手架（`main.go`、`__init__.py`、`doc.go`、配置和示例程序）没有算进去。",
        "",
        "## 规模",
        "",
        "| 结局 | PR 数 |",
        "| --- | ---: |",
    ]
    for key in ("merged", "closed_unmerged", "open"):
        lines.append(f"| {outcome_name[key]} | {by_outcome[key]:,} |")
    lines.append(f"| 合计 | {len(rows):,} |")
    lines.extend(
        [
            "",
            f"来自 {len(by_repo):,} 个仓库。有 SHA 的 PR 一共 {population_n:,} 条。",
            "",
            "按 Agent：",
            "",
            "| Agent | PR 数 |",
            "| --- | ---: |",
        ]
    )
    for name, count in by_agent.most_common():
        lines.append(f"| {name} | {count:,} |")
    lines.extend(
        [
            "",
            "## 仓库",
            "",
            "每个仓库下列出看到的性能测试路径，PR 数是该仓库收进这份名单的条数。",
            "",
            "| 仓库 | PR 数 | 看到的性能测试 |",
            "| --- | ---: | --- |",
        ]
    )
    for repo, count in by_repo.most_common():
        files = " / ".join(repo_files.get(repo, [])).replace("|", "/")
        lines.append(f"| {repo} | {count:,} | {files} |")
    lines.extend(
        [
            "",
            "## 边界",
            "",
            "这份名单用的是数据集里出现过的文件路径。仓库里有性能测试，但这批提交从来没碰到那个文件时，这里还看不到。普通 `*_test.go` 里只有 `func Benchmark`、文件名不带 bench 的，也没有算进去。",
            "",
        ]
    )
    DOCS.mkdir(parents=True, exist_ok=True)
    body = "\n".join(lines)
    readme_path = DOCS / "README.md"
    if readme_path.exists() and "## 怎么判定" in readme_path.read_text(encoding="utf-8"):
        head = readme_path.read_text(encoding="utf-8").split("## 怎么判定", 1)[0].rstrip()
        readme_path.write_text(head + "\n\n" + body, encoding="utf-8")
    else:
        header = "\n".join(
            [
                "# Phase 2：有性能测试的 PR",
                "",
                "仓库里只要能看到性能测试，这个仓库里的 PR 都收进来。这条 PR 自己的 diff 不必改到那个性能测试文件。",
                "",
                "数据来自 [AIDev-7.6M](https://huggingface.co/datasets/hao-li/AIDev-7.6M) 的 pop 子集（仓库大于 100 star，且数据集里有 commit SHA）。完整名单在 `../data/prs_with_perf_tests.csv`。",
                "",
            ]
        )
        readme_path.write_text(header + body, encoding="utf-8")


def main() -> None:
    population = load_population()
    pr_repo = {row["pr_id"]: row["repo"] for row in population}
    repo_files = repos_with_perf_tests(pr_repo)
    rows = [row for row in population if row["repo"] in repo_files]
    rows.sort(key=lambda row: (row["repo"], row["outcome"], int(row["number"])))
    DATA.mkdir(parents=True, exist_ok=True)
    csv_path = DATA / "prs_with_perf_tests.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["pr_id", "number", "outcome", "agent", "repo", "html_url", "perf_files"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "perf_files": " | ".join(repo_files[row["repo"]])})
    by_outcome = Counter(row["outcome"] for row in rows)
    summary = {
        "population_prs_with_sha": len(population),
        "repos_with_perf_tests": len(repo_files),
        "prs_in_those_repos": len(rows),
        "by_outcome": dict(by_outcome),
        "rule": "repository contains a performance-test path in some visible commit; the PR diff itself need not edit it",
        "csv": "prs_with_perf_tests.csv",
    }
    (DATA / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_readme(rows, repo_files, len(population))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
