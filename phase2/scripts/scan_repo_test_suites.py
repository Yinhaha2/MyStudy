"""PRs whose repository already contained a test suite before the commit.

Local evidence: a commit in the repo modified an existing test source file.
That file was already in the tree. Repos with no such edit are checked on GitHub
at the parent of one commit, so files added by that commit are not counted.
"""

from __future__ import annotations

import csv
import json
import random
import re
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

HF = "hf://datasets/hao-li/AIDev-7.6M"
OUT = Path(__file__).resolve().parents[1] / "archive" / "test_pr_scan"
TOKEN_PATH = Path(__file__).resolve().parents[2] / ".github_token"
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


def slug(url: str) -> str:
    parts = (url or "").rstrip("/").split("/")
    if len(parts) < 2:
        return ""
    return f"{parts[-2]}/{parts[-1]}"


def load_population() -> list[dict]:
    commits = pq.read_table(f"{HF}/pr_commits.parquet", columns=["pr_id", "sha"])
    sha_of: dict[int, str] = {}
    for pr_id, sha in zip(commits.column("pr_id").to_pylist(), commits.column("sha").to_pylist()):
        if pr_id is None or not sha or int(pr_id) in sha_of:
            continue
        sha_of[int(pr_id)] = sha
    table = pq.read_table(
        f"{HF}/pull_request.parquet",
        columns=["id", "number", "state", "merged_at", "repo_url", "html_url", "agent"],
    )
    meta = table.to_pydict()
    rows = []
    for i, pr_id in enumerate(meta["id"]):
        pr_id = int(pr_id)
        if pr_id not in sha_of:
            continue
        rows.append(
            {
                "pr_id": pr_id,
                "number": meta["number"][i],
                "outcome": outcome_of(meta["state"][i], meta["merged_at"][i]),
                "repo": slug(meta["repo_url"][i] or ""),
                "html_url": meta["html_url"][i] or "",
                "agent": meta["agent"][i] or "",
                "sha": sha_of[pr_id],
            }
        )
    return rows


def repos_with_modified_tests() -> set[str]:
    found = set()
    with (OUT / "prs_with_test_files.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if int(row["n_modified"]) > 0:
                found.add(slug(row["repo_url"]))
    return found


def github_json(token: str, url: str) -> tuple[int, dict | None, dict]:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "mystudy-repo-test-scan",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8")), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"message": raw[:200]}
        return exc.code, payload, dict(exc.headers)


def parent_has_tests(token: str, repo: str, sha: str) -> dict:
    status, commit, headers = github_json(token, f"https://api.github.com/repos/{repo}/commits/{sha}")
    if status == 403 and headers.get("X-RateLimit-Remaining") == "0":
        reset = int(headers.get("X-RateLimit-Reset") or time.time() + 60)
        time.sleep(max(1, reset - time.time() + 2))
        status, commit, headers = github_json(token, f"https://api.github.com/repos/{repo}/commits/{sha}")
    if status != 200 or not commit:
        return {"repo": repo, "sha": sha, "http": status, "has_tests": None, "reason": "commit_missing"}
    parents = commit.get("parents") or []
    if not parents:
        return {"repo": repo, "sha": sha, "http": 200, "has_tests": False, "reason": "root_commit", "n_tests": 0}
    parent = parents[0]["sha"]
    status, tree, headers = github_json(
        token, f"https://api.github.com/repos/{repo}/git/trees/{parent}?recursive=1"
    )
    if status == 403 and headers.get("X-RateLimit-Remaining") == "0":
        reset = int(headers.get("X-RateLimit-Reset") or time.time() + 60)
        time.sleep(max(1, reset - time.time() + 2))
        status, tree, headers = github_json(
            token, f"https://api.github.com/repos/{repo}/git/trees/{parent}?recursive=1"
        )
    if status != 200 or not tree:
        return {"repo": repo, "sha": sha, "parent": parent, "http": status, "has_tests": None, "reason": "tree_missing"}
    examples = []
    for item in tree.get("tree") or []:
        if item.get("type") != "blob":
            continue
        path = item.get("path") or ""
        if is_test_source(path):
            examples.append(path)
            if len(examples) >= 5:
                break
    return {
        "repo": repo,
        "sha": sha,
        "parent": parent,
        "http": 200,
        "truncated": bool(tree.get("truncated")),
        "has_tests": bool(examples) or (bool(tree.get("truncated")) and None),
        "n_examples": len(examples),
        "examples": examples,
        "reason": "parent_tree",
    }


def main() -> None:
    population = load_population()
    confirmed_repos = repos_with_modified_tests()
    by_outcome = Counter(row["outcome"] for row in population)
    confirmed_prs = [row for row in population if row["repo"] in confirmed_repos]
    confirmed_outcome = Counter(row["outcome"] for row in confirmed_prs)
    unknown_repos: dict[str, str] = {}
    for row in population:
        if row["repo"] in confirmed_repos or row["repo"] in unknown_repos:
            continue
        unknown_repos[row["repo"]] = row["sha"]

    token = TOKEN_PATH.read_text(encoding="utf-8").strip()
    rng = random.Random(15)
    sample_repos = rng.sample(sorted(unknown_repos), k=min(250, len(unknown_repos)))
    hits = []
    missing = 0
    for i, repo in enumerate(sample_repos, start=1):
        result = parent_has_tests(token, repo, unknown_repos[repo])
        hits.append(result)
        if result["has_tests"] is None:
            missing += 1
        if i % 25 == 0 or i == len(sample_repos):
            yes = sum(1 for item in hits if item["has_tests"] is True)
            print(f"sampled {i} yes {yes} missing {missing}", flush=True)
        time.sleep(0.05)

    known = [item for item in hits if item["has_tests"] is not None]
    yes_n = sum(1 for item in known if item["has_tests"])
    rate = yes_n / len(known) if known else 0
    unknown_prs = [row for row in population if row["repo"] not in confirmed_repos]
    unknown_by_repo = Counter(row["repo"] for row in unknown_prs)
    # Repos are not equally sized; weight the sample by PR count.
    weighted_yes = 0
    weighted_known = 0
    hit_repo = {item["repo"]: item["has_tests"] for item in hits}
    for repo, n_prs in unknown_by_repo.items():
        if repo not in hit_repo or hit_repo[repo] is None:
            continue
        weighted_known += n_prs
        if hit_repo[repo]:
            weighted_yes += n_prs
    weighted_rate = weighted_yes / weighted_known if weighted_known else 0

    summary = {
        "population_prs": len(population),
        "population_repos": len({row["repo"] for row in population}),
        "by_outcome": dict(by_outcome),
        "confirmed_by_modified_existing_test_file": {
            "repos": len(confirmed_repos),
            "prs": len(confirmed_prs),
            "by_outcome": dict(confirmed_outcome),
            "rule": "some commit in the repo modified a test source file, so that file already existed",
        },
        "unknown_repos": len(unknown_repos),
        "unknown_prs": len(unknown_prs),
        "sample_of_unknown_repos": {
            "n": len(sample_repos),
            "resolved": len(known),
            "repos_with_tests_before_commit": yes_n,
            "repo_rate": round(rate, 4),
            "pr_weighted_rate": round(weighted_rate, 4),
            "weighted_prs_seen": weighted_known,
        },
        "estimated_additional_prs": round(len(unknown_prs) * weighted_rate),
        "estimated_total_prs": len(confirmed_prs) + round(len(unknown_prs) * weighted_rate),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "repo_suite_sample.json").write_text(
        json.dumps({"summary": summary, "sample": hits}, indent=2), encoding="utf-8"
    )
    (OUT / "repo_suite_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (OUT / "prs_in_repos_with_existing_tests.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["pr_id", "number", "outcome", "agent", "repo", "html_url", "evidence"]
        )
        writer.writeheader()
        for row in confirmed_prs:
            writer.writerow(
                {
                    "pr_id": row["pr_id"],
                    "number": row["number"],
                    "outcome": row["outcome"],
                    "agent": row["agent"],
                    "repo": row["repo"],
                    "html_url": row["html_url"],
                    "evidence": "modified_existing_test_file",
                }
            )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
