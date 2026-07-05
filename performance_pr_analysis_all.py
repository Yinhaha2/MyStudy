#!/usr/bin/env python3
"""
Full-corpus Agent PR analysis based on ``all_pull_request.parquet``.

Unlike AIDev-pop (``pull_request.parquet``), HF does **not** ship LLM ``pr_task_type``
labels for ~932k rows — only ``pr_task_type.parquet`` (≈33,596 labeled pop PRs).

This script therefore reports:
  * Corpus-level merge stats per agent on **all** PRs in ``all_pull_request``.
  * **LLM perf** (same definition as MyStudy/pop): rows with joined ``type == "perf"``.
  * **Title-regex perf** on the full corpus: Conventional Commit ``perf`` prefix in the
    first title line — same Stage-1 heuristic as ``analysis/classify_pr.py``.

Outputs mirror ``MyStudy/output`` but land in ``MyStudy/output_all/`` (no ``all_perfPR.json``).

Run:
    python performance_pr_analysis_all.py
    python performance_pr_analysis_all.py --local
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import performance_pr_analysis as pa

HF_BASE = pa.HF_BASE
ROOT = pa.ROOT
AIDEV = pa.AIDEV
Mystudy = pa.Mystudy
OUT_ALL = Mystudy / "output_all"
FIG_ALL = OUT_ALL / "figures"

# Stage-1 label from classify_pr.py (perf only)
_PERF_TITLE_PATTERN = re.compile(r"^perf(\([^)]*\))?!?(?=\W|$)", re.IGNORECASE)


def parquet_path(name: str, *, local: bool) -> str:
    if local:
        p = AIDEV / name
        if not p.exists():
            raise FileNotFoundError(
                f"Missing {p}. Download the dataset or run without --local.\n"
                "See analysis/helper.py / AIDev/README.md."
            )
        return str(p)
    return f"{HF_BASE}/{name}"


def read_parquet(name: str, *, local: bool, columns: list[str] | None = None) -> pd.DataFrame:
    path = parquet_path(name, local=local)
    kw: dict[str, Any] = {}
    if columns:
        kw["columns"] = columns
    return pd.read_parquet(path, **kw)


def title_has_perf_commit_prefix(title: str) -> bool:
    if not title or not isinstance(title, str):
        return False
    first = title.splitlines()[0].strip()
    return bool(_PERF_TITLE_PATTERN.match(first))


def summarize_corpus_by_agent(df: pd.DataFrame, *, suffix: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for ag in sorted(df["agent"].dropna().unique()):
        sub = df[df["agent"] == ag]
        merged_pct = 100 * (sub["status"] == "merged").mean()
        terminal = sub[sub["state"] == "closed"]
        term_rate = 100 * terminal["merged_at"].notna().mean() if len(terminal) else float("nan")
        rows.append({
            "agent": ag,
            f"corpus_n_{suffix}": len(sub),
            f"merged_pct_all_states_{suffix}": merged_pct,
            f"merged_pct_closed_only_{suffix}": term_rate,
        })
    return pd.DataFrame(rows)


def plot_dashboard_all(
    corp: pd.DataFrame,
    perf_llm: pd.DataFrame,
    perf_title: pd.DataFrame,
    out_fp: Path,
) -> None:
    import matplotlib.pyplot as plt

    corp = corp.sort_values("corpus_n_all_pull", ascending=True)
    pf = perf_llm.groupby("agent").size().reset_index(name="n")
    pt = perf_title.groupby("agent").size().reset_index(name="n")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    ax = axes[0, 0]
    ax.barh(corp["agent"], corp["corpus_n_all_pull"])
    ax.set_title("Full corpus: PR count per agent (all_pull_request)")
    ax.set_xlabel("Count")

    ax = axes[0, 1]
    merge_col = "merged_pct_all_states_all_pull"
    ax.barh(corp["agent"], corp[merge_col])
    ax.set_title("Full corpus: merge % (includes open)")
    ax.set_xlabel("% merged")

    ax = axes[1, 0]
    if pf.empty:
        ax.text(0.5, 0.5, "No LLM perf rows", ha="center")
    else:
        pf2 = pf.sort_values("n", ascending=True)
        ax.barh(pf2["agent"], pf2["n"])
        ax.set_title(f'LLM perf (join pr_task_type, type=="perf"): n={len(perf_llm)}')
        ax.set_xlabel("Count")

    ax = axes[1, 1]
    if pt.empty:
        ax.text(0.5, 0.5, "No title-regex perf", ha="center")
    else:
        pt2 = pt.sort_values("n", ascending=True)
        ax.barh(pt2["agent"], pt2["n"])
        ax.set_title(f"Full corpus title perf: perf: regex in title, n={len(perf_title)}")
        ax.set_xlabel("Count")

    fig.tight_layout()
    out_fp.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_fp, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Full all_pull_request corpus analysis")
    parser.add_argument("--local", action="store_true", help="Read Parquet files from ../AIDev")
    args = parser.parse_args()
    local: bool = args.local

    OUT_ALL.mkdir(parents=True, exist_ok=True)
    FIG_ALL.mkdir(parents=True, exist_ok=True)

    ds = "local AIDEV dir" if local else HF_BASE

    # --- Full Agent PR corpus ---
    pr_all = read_parquet("all_pull_request.parquet", local=local)
    lbl_ai = read_parquet("pr_task_type.parquet", local=local)
    lbl_ai = lbl_ai.drop_duplicates(subset=["id"], keep="first")
    lbl_cols = ["id"] + [c for c in ("type", "reason", "confidence") if c in lbl_ai.columns]

    merged = pr_all.merge(
        lbl_ai[lbl_cols],
        on="id",
        how="left",
        validate="many_to_one",
    )
    merged = pa.attach_status(merged)
    merged["perf_detected_title_regex"] = merged["title"].map(title_has_perf_commit_prefix)

    total_all = len(merged)
    n_labeled = merged["type"].notna().sum()

    perf_llm = merged[merged["type"] == "perf"].copy()
    perf_title_only = merged[merged["perf_detected_title_regex"]].copy()

    perf_llm_e = pa.add_export_rows(perf_llm, ["agent", "id"])
    perf_title_e = pa.add_export_rows(perf_title_only, ["agent", "id"])

    perf_llm_e.to_parquet(OUT_ALL / "performance_prs_agents.parquet", index=False)
    perf_title_e.to_parquet(
        OUT_ALL / "performance_prs_agents_title_regex.parquet",
        index=False,
    )

    corp_stats = summarize_corpus_by_agent(merged, suffix="all_pull")

    rev, cm_rev, isc = pa.load_rejection_aux(local=local)

    merged_pct_llm_pool = 100 * (perf_llm_e["status"] == "merged").mean() if len(perf_llm_e) else float("nan")
    merged_pct_title_pool = (
        100 * (perf_title_e["status"] == "merged").mean()
        if len(perf_title_e)
        else float("nan")
    )

    rejection_profiles: list[dict[str, Any]] = []
    for name, cdf in ("agent_perf_llm", perf_llm_e), ("agent_perf_title_regex", perf_title_e):
        closed_um = cdf[cdf["status"] == "closed"]
        buckets: dict[str, int] = {}
        for pid in closed_um["id"].tolist():
            sig = pa.rejection_signal_for_pr(int(pid), rev, cm_rev, isc)
            buckets[sig["bucket"]] = buckets.get(sig["bucket"], 0) + 1
        rejection_profiles.append({
            "cohort": name,
            "closed_unmerged_n": len(closed_um),
            "bucket_counts": buckets,
        })

    # --- Human baseline (AidDev-pop humans only — same as pop notebook) ---
    pr_human = read_parquet("human_pull_request.parquet", local=local)
    lbl_h = read_parquet("human_pr_task_type.parquet", local=local)
    pr_h_i = pa.merge_pr_labels(pr_human, lbl_h)
    total_human_pr = len(pr_human)
    perf_human = pa.attach_status(pr_h_i[pr_h_i["type"] == "perf"].copy())
    perf_h_e = pa.add_export_rows(perf_human, ["id"])
    perf_h_e.to_parquet(OUT_ALL / "performance_prs_human.parquet", index=False)

    merged_pct_human = 100 * (perf_h_e["status"] == "merged").mean() if len(perf_h_e) else float("nan")
    summary_human = pa.summarize_agent_perf(perf_h_e)
    summary_llm_perf = pa.summarize_agent_perf(perf_llm_e)
    summary_title_perf = pa.summarize_agent_perf(perf_title_e)

    for cohort_name, cohort_df in (("human", perf_h_e),):
        closed_um = cohort_df[cohort_df["status"] == "closed"]
        buckets = {}
        for pid in closed_um["id"].tolist():
            sig = pa.rejection_signal_for_pr(int(pid), rev, cm_rev, isc)
            buckets[sig["bucket"]] = buckets.get(sig["bucket"], 0) + 1
        rejection_profiles.append({
            "cohort": cohort_name,
            "closed_unmerged_n": len(closed_um),
            "bucket_counts": buckets,
        })

    overlap_llm_title = (
        int(perf_llm_e["perf_detected_title_regex"].fillna(False).astype(bool).sum())
        if len(perf_llm_e)
        else 0
    )

    metrics: dict[str, Any] = {
        "corpus_mode": "all_pull_request.parquet (+ pop-only pr_task_type join)",
        "data_source": ds,
        "methodology_zh": (
            "全量表中仅 AIDev-pop 的 PR 在 pr_task_type.parquet 中有 LLM type；其余行 type 为空。"
            "「LLM perf」与 MyStudy/pop 一致。「标题 perf」对标 classify_pr.py 的 perf 前缀规则，覆盖全部行。"
        ),
        "all_pull_request_rows": total_all,
        "rows_with_pr_task_type_join": int(n_labeled),
        "pr_task_type_file_rows_hint": int(len(lbl_ai)),
        "perf_count_llm_joined_agent": int(len(perf_llm_e)),
        "perf_ratio_of_all_pull_llm_defined": (
            len(perf_llm_e) / total_all if total_all else 0.0
        ),
        "perf_count_title_regex_agent": int(len(perf_title_e)),
        "perf_ratio_title_regex_of_all_pull": (
            len(perf_title_e) / total_all if total_all else 0.0
        ),
        "llm_perf_rows_also_matching_title_perf_prefix": int(overlap_llm_title),
        "perf_llm_merge_rate_pct_includes_open_pop_notebook_aligned": merged_pct_llm_pool,
        "perf_title_regex_merge_rate_pct_includes_open": merged_pct_title_pool,
        "human_perf_n_pop_baseline_same_as_output_folder": len(perf_h_e),
        "human_perf_merge_rate_pct_includes_open": merged_pct_human,
        "total_human_pull_request_baseline_rows": total_human_pr,
        "human_pr_dataset_scope_note_zh": (
            "human_pull_request.parquet 仍是论文中的对照子集（>500★ 仓库等），而非 93 万人库。"
        ),
        "corpus_merge_stats_per_agent_records": corp_stats.to_dict(orient="records"),
        "per_agent_perf_llm_same_definition_as_pop": summary_llm_perf.to_dict(orient="records"),
        "per_agent_perf_title_regex_only": summary_title_perf.to_dict(orient="records"),
        "human_perf_breakdown_records": summary_human.to_dict(orient="records"),
        "closed_unmerged_rejection_signal_profiles": rejection_profiles,
        "artifacts_excluded": ["all_perfPR.json (skipped for output_all pipeline)"],
    }

    examples: list[Any] = []
    examples.extend(
        pa.build_cited_examples(
            perf_llm_e,
            rev,
            cm_rev,
            isc,
            which="agent",
        )
    )
    examples.extend(
        pa.build_cited_examples(
            perf_h_e,
            rev,
            cm_rev,
            isc,
            which="human",
        )
    )
    for ex in examples:
        op = ex.get("output_parquet")
        if isinstance(op, str) and "MyStudy/output/" in op:
            ex["output_parquet"] = op.replace("MyStudy/output/", "MyStudy/output_all/", 1)

    with open(OUT_ALL / "summary_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    with open(OUT_ALL / "rejection_signal_examples.json", "w", encoding="utf-8") as f:
        json.dump(examples, f, ensure_ascii=False, indent=2)

    plot_dashboard_all(
        corp_stats,
        perf_llm,
        perf_title_only,
        out_fp=FIG_ALL / "performance_pr_dashboard_all.png",
    )

    md = f"""# 全量 Agent 对照分析（自动生成）

- **PR 表**：`all_pull_request.parquet`，共 **{total_all}** 条
- **`pr_task_type` 命中行数**：**{int(n_labeled)}**（AIDev-pop 官方标签覆盖；其余全量 PR 无 LLM `type`）
- **LLM perf**（join 后 `type=="perf"`）：**{len(perf_llm_e)}**，占全量 **{100 * len(perf_llm_e) / total_all:.4f}%**；合并率（含 open，与 `productivity.ipynb` 口径）**{merged_pct_llm_pool:.2f}%**
- **标题 `perf:` 正则（全表）**：**{len(perf_title_e)}**（与 `classify_pr.py` Stage-1 一致；多数性能 PR 不写该前缀）；合并率 **{merged_pct_title_pool:.2f}%**
- **Human perf**（仍为 `human_pull_request` 对照集）：**{len(perf_h_e)}**，合并率 **{merged_pct_human:.2f}%**

## 逐 Agent · 全库 PR 数与合并率

{corp_stats.to_string(index=False)}

## 逐 Agent · LLM perf（与 MyStudy/output 同定义）

{summary_llm_perf.to_string(index=False)}

## 逐 Agent · 标题 perf 前缀（全库标题规则）

{summary_title_perf.to_string(index=False)}
"""
    with open(OUT_ALL / "SUMMARY_zh.md", "w", encoding="utf-8") as f:
        f.write(md)

    print("Wrote", OUT_ALL)


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
