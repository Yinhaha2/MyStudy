#!/usr/bin/env python3
"""
Extract paper-expanded performance PRs (arXiv:2512.24630) and join AIDev-pop auxiliary tables
into MyStudy/databasephase1/.

Paper repo: AIDevPerf/LLM-performance
Canonical expanded set: POP_PULL_Requests_LLM_filtered_final.csv (1221 PRs)
LLM-only detection:      POP_PULL_Requests_LLM_filtered.csv (1160 PRs)
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
AIDEV = ROOT / "AIDev"
PAPER = ROOT / "AIDevPerf" / "LLM-performance" / "Outputs"
OUT = Path(__file__).resolve().parent / "databasephase1"

PAPER_PERF_FINAL = PAPER / "PerformancePRs" / "POP_PULL_Requests_LLM_filtered_final.csv"
PAPER_PERF_LLM = PAPER / "PerformancePRs" / "POP_PULL_Requests_LLM_filtered.csv"
PAPER_TOPICS = PAPER / "BERTopic" / "All_PR_Topics.csv"
PAPER_TOPIC_INFO = PAPER / "BERTopic" / "Topic_Info.csv"


def attach_status(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ("created_at", "closed_at", "merged_at"):
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], utc=True, errors="coerce")
    out["status"] = np.select(
        [out["state"] == "open", out["merged_at"].notna()],
        ["open", "merged"],
        default="closed",
    )
    return out


def filter_table(path: Path, pr_ids: set[int], *, key: str = "pr_id") -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_parquet(path)
    if key not in df.columns:
        return pd.DataFrame()
    return df[df[key].isin(pr_ids)].copy()


def main() -> None:
    if not PAPER_PERF_FINAL.exists():
        raise FileNotFoundError(f"Missing paper output: {PAPER_PERF_FINAL}")

    OUT.mkdir(parents=True, exist_ok=True)
    for sub in ("pr_master", "classification", "auxiliary", "summary", "paper_source_copy"):
        (OUT / sub).mkdir(exist_ok=True)

    # --- Paper perf PR lists ---
    perf_final = pd.read_csv(PAPER_PERF_FINAL)
    perf_llm = pd.read_csv(PAPER_PERF_LLM)
    pr_ids = set(perf_final["id"].astype(int))

    only_in_final = set(perf_final["id"]) - set(perf_llm["id"])
    perf_final = attach_status(perf_final)
    perf_final["detection_source"] = np.where(
        perf_final["id"].isin(only_in_final),
        "aidev_pr_task_type_perf_only",
        "llm_title_body_classifier",
    )
    perf_llm = attach_status(perf_llm)

    # --- AIDev official task type ---
    task_type = pd.read_parquet(AIDEV / "pr_task_type.parquet")
    task_type = task_type[task_type["id"].isin(pr_ids)].rename(
        columns={"type": "aidev_task_type", "reason": "aidev_task_reason", "confidence": "aidev_task_confidence"}
    )

    master = perf_final.merge(
        task_type[["id", "aidev_task_type", "aidev_task_reason", "aidev_task_confidence"]],
        on="id",
        how="left",
    )

    if PAPER_TOPICS.exists():
        topics = pd.read_csv(PAPER_TOPICS)
        topic_cols = [c for c in topics.columns if c not in master.columns or c == "id"]
        master = master.merge(topics[topic_cols], on="id", how="left", suffixes=("", "_topic_dup"))
        master = master[[c for c in master.columns if not c.endswith("_topic_dup")]]

    if "llm_output" not in master.columns and "llm_output" in perf_llm.columns:
        master = master.merge(perf_llm[["id", "llm_output"]], on="id", how="left")

    master.insert(0, "row_1based", np.arange(1, len(master) + 1))

    # --- Save master & subsets ---
    master.to_parquet(OUT / "pr_master" / "perf_prs_expanded_final.parquet", index=False)
    master.to_csv(OUT / "pr_master" / "perf_prs_expanded_final.csv", index=False)

    perf_llm_out = perf_llm.merge(
        task_type[["id", "aidev_task_type", "aidev_task_reason"]], on="id", how="left"
    )
    perf_llm_out.to_parquet(OUT / "pr_master" / "perf_prs_llm_detected_1160.parquet", index=False)

    # --- BERTopic exports ---
    if PAPER_TOPICS.exists():
        topics_f = topics[topics["id"].isin(pr_ids)].copy()
        topics_f.to_parquet(OUT / "classification" / "bertopic_topic_assignments.parquet", index=False)
    if PAPER_TOPIC_INFO.exists():
        shutil.copy2(PAPER_TOPIC_INFO, OUT / "classification" / "bertopic_topic_info.csv")
    task_type.to_parquet(OUT / "classification" / "aidev_pr_task_type_for_perf_prs.parquet", index=False)

    # --- Auxiliary tables (1:N, not embedded in PR row) ---
    aux_specs: list[tuple[str, str]] = [
        ("pr_commits.parquet", "pr_id"),
        ("pr_commit_details.parquet", "pr_id"),
        ("pr_reviews.parquet", "pr_id"),
        ("pr_comments.parquet", "pr_id"),
        ("pr_timeline.parquet", "pr_id"),
        ("related_issue.parquet", "pr_id"),
    ]
    coverage: dict[str, Any] = {"pr_count": len(pr_ids), "tables": {}}

    for fname, key in aux_specs:
        sub = filter_table(AIDEV / fname, pr_ids, key=key)
        out_path = OUT / "auxiliary" / fname
        if not sub.empty:
            sub.to_parquet(out_path, index=False)
        coverage["tables"][fname] = {
            "rows": int(len(sub)),
            "prs_with_any_row": int(sub[key].nunique()) if len(sub) else 0,
            "join_key": key,
        }

    rev = filter_table(AIDEV / "pr_reviews.parquet", pr_ids)
    if not rev.empty:
        cm = pd.read_parquet(AIDEV / "pr_review_comments_v2.parquet")
        cm_sub = cm[cm["pull_request_review_id"].isin(rev["id"])].copy()
        cm_sub.to_parquet(OUT / "auxiliary" / "pr_review_comments_v2.parquet", index=False)
        coverage["tables"]["pr_review_comments_v2.parquet"] = {
            "rows": int(len(cm_sub)),
            "join_via": "pull_request_review_id -> pr_reviews.id -> pr_id",
        }

    ri = filter_table(AIDEV / "related_issue.parquet", pr_ids)
    if not ri.empty:
        issues = pd.read_parquet(AIDEV / "issue.parquet")
        linked = issues[issues["id"].isin(ri["issue_id"])].copy()
        linked.to_parquet(OUT / "auxiliary" / "issues_linked.parquet", index=False)
        coverage["tables"]["issues_linked.parquet"] = {"rows": int(len(linked))}

    repo = pd.read_parquet(AIDEV / "repository.parquet")
    repo_ids = master["repo_id"].dropna().unique()
    repo_sub = repo[repo["id"].isin(repo_ids)]
    repo_sub.to_parquet(OUT / "auxiliary" / "repository.parquet", index=False)

    # --- Copy paper source CSVs for provenance ---
    for src in (PAPER_PERF_FINAL, PAPER_PERF_LLM):
        if src.exists():
            shutil.copy2(src, OUT / "paper_source_copy" / src.name)

    coverage["master_row_fields"] = list(master.columns)
    coverage["detection_breakdown"] = {
        "llm_detected_only": int((master["detection_source"] == "llm_title_body_classifier").sum()),
        "added_from_aidev_task_type_perf": int((master["detection_source"] == "aidev_pr_task_type_perf_only").sum()),
        "aidev_task_type_perf_total_in_pop": int((master["aidev_task_type"] == "perf").sum()),
        "aidev_task_type_fix_among_expanded": int((master["aidev_task_type"] == "fix").sum()),
    }

    with open(OUT / "summary" / "coverage_stats.json", "w", encoding="utf-8") as f:
        json.dump(coverage, f, ensure_ascii=False, indent=2)

    print(f"Wrote {OUT} ({len(master)} perf PRs)")


if __name__ == "__main__":
    main()
