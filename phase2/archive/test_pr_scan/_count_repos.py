"""Count unique repos and PRs that edited a test file which already existed."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

HF = "hf://datasets/hao-li/AIDev-7.6M"
CSV_PATH = Path(__file__).resolve().parent / "prs_with_test_files.csv"


def outcome(state, merged_at) -> str:
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


def main() -> None:
    commits = pq.read_table(f"{HF}/pr_commits.parquet", columns=["pr_id", "sha"])
    sha_ids = {int(x) for x in commits.column("pr_id").to_pylist() if x is not None}
    prs = pq.read_table(
        f"{HF}/pull_request.parquet",
        columns=["id", "state", "merged_at", "repo_url", "created_at"],
    )
    meta = prs.to_pydict()
    by_repo: dict[str, list[int]] = defaultdict(list)
    den = Counter()
    for i, pid in enumerate(meta["id"]):
        pid = int(pid)
        if pid not in sha_ids:
            continue
        repo = slug(meta["repo_url"][i] or "")
        by_repo[repo].append(pid)
        den[outcome(meta["state"][i], meta["merged_at"][i])] += 1
    sizes = sorted((len(v) for v in by_repo.values()), reverse=True)
    print("prs", sum(den.values()), "repos", len(by_repo), "top10", sizes[:10])
    print("denominator", dict(den))

    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    pre = Counter()
    only_added = Counter()
    repos_pre = set()
    prs_in_pre_repos = Counter()
    for row in rows:
        repo = slug(row["repo_url"])
        if int(row["n_modified"]) + int(row["n_renamed"]) > 0:
            pre[row["outcome"]] += 1
            repos_pre.add(repo)
        elif int(row["n_added"]) > 0:
            only_added[row["outcome"]] += 1
    for repo, pids in by_repo.items():
        if repo in repos_pre:
            prs_in_pre_repos["prs"] += len(pids)
            prs_in_pre_repos["repos"] += 1
    print("edited_preexisting_test_file", dict(pre), "total", sum(pre.values()))
    print("only_added_test_file", dict(only_added), "total", sum(only_added.values()))
    print("repos_with_preexisting_touch", len(repos_pre), "prs_in_those_repos", prs_in_pre_repos["prs"])


if __name__ == "__main__":
    main()
