"""Apply the paper's RegexClassifier keyword list to phase2 PRs."""

import csv
import re
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

KEYWORDS = [
    "performance",
    "compile-time-hog",
    "perf",
    "hang",
    "optimization",
    "responsive",
    "slow",
    "speed",
    "latency",
    "throughput",
    "wait",
    "fast",
    "lag",
    "tim",
    "minor",
    "stuck",
    "instant",
    "respons",
    "react",
    "latenc",
    "perform",
    "memory",
    "leak",
]
PATTERN = re.compile(r"\b(?:{})\w*".format("|".join(map(re.escape, KEYWORDS))), re.IGNORECASE)
PHASE = Path("phase2/prs_with_perf_tests.csv")
HF = "hf://datasets/hao-li/AIDev-7.6M/pull_request.parquet"


def main() -> None:
    wanted = {}
    with PHASE.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            wanted[int(row["pr_id"])] = row
    table = pq.read_table(HF, columns=["id", "title", "body"])
    meta = table.to_pydict()
    hits = 0
    keyword_counts = Counter()
    out_rows = []
    for pr_id, title, body in zip(meta["id"], meta["title"], meta["body"]):
        if pr_id is None or int(pr_id) not in wanted:
            continue
        text = f"{title or ''}\n{body or ''}"
        matches = sorted({m.lower() for m in PATTERN.findall(text)})
        if not matches:
            continue
        hits += 1
        for match in matches:
            keyword_counts[match] += 1
        info = wanted[int(pr_id)]
        out_rows.append(
            {
                **{k: info[k] for k in ("pr_id", "number", "outcome", "agent", "repo", "html_url")},
                "title": title or "",
                "matched_words": " ".join(matches[:12]),
            }
        )
    print("population", len(wanted), "keyword_hits", hits)
    print("top", keyword_counts.most_common(20))
    path = Path("phase2/keyword_candidates.csv")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)
    print("wrote", path, len(out_rows))


if __name__ == "__main__":
    main()
