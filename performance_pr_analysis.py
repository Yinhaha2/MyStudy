#!/usr/bin/env python3
"""
Extract AIDev-pop performance (perf) PRs, compute merge rates and rejection signals,
and write figures + cited examples under ./output/.

See README.md for metric definitions and join keys.
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

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
AIDEV = ROOT / "AIDev"
Mystudy = Path(__file__).resolve().parent
OUT = Mystudy / "output"
FIG = OUT / "figures"

HF_BASE = "hf://datasets/hao-li/AIDev"

AGENT_NAMES = [
    "OpenAI_Codex",
    "Devin",
    "Copilot",
    "Cursor",
    "Claude_Code",
]
HUMAN_NAME = "Human"


def _parquet(name: str, *, local: bool) -> str:
    if local:
        p = AIDEV / name
        if not p.exists():
            raise FileNotFoundError(
                f"Missing {p}. Download the dataset or run without --local.\n"
                "See analysis/helper.py / AIDev/README.md."
            )
        return str(p)
    return f"{HF_BASE}/{name}"


def _read_parquet(name: str, *, local: bool, columns: list[str] | None = None) -> pd.DataFrame:
    path = _parquet(name, local=local)
    kw: dict[str, Any] = {}
    if columns:
        kw["columns"] = columns
    return pd.read_parquet(path, **kw)


def attach_status(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ("created_at", "closed_at", "merged_at"):
        if col in out.columns and str(out[col].dtype) != "datetime64[ns, UTC]":
            out[col] = pd.to_datetime(out[col], utc=True, errors="coerce")
    out["status"] = np.select(
        [out["state"] == "open", out["merged_at"].notna()],
        ["open", "merged"],
        default="closed",
    )
    out["merged_flag"] = out["merged_at"].notna()
    # Terminal PRs only: closed state in GitHub sense
    terminal = out["state"] == "closed"
    out["terminal_merged_rate_naive"] = np.where(
        terminal,
        out["merged_at"].notna(),
        np.nan,
    )
    return out


def merge_pr_labels(pr: pd.DataFrame, lbl: pd.DataFrame) -> pd.DataFrame:
    keep_lbl = ["id"] + [c for c in ("type", "reason", "confidence") if c in lbl.columns]
    return pr.merge(lbl[keep_lbl], on="id", how="inner")


def json_serializable(v: Any) -> Any:
    """Convert a single cell / scalar to JSON-safe Python."""
    if v is None:
        return None
    if isinstance(v, (str, bool)):
        return v
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (int,)):
        return int(v)
    if isinstance(v, float):
        return None if np.isnan(v) else float(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, pd.Timestamp):
        return None if pd.isna(v) else v.isoformat()
    if isinstance(v, np.datetime64):
        ts = pd.Timestamp(v)
        return None if pd.isna(ts) else ts.isoformat()
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    try:
        if pd.isna(v):
            return None
    except (ValueError, TypeError):
        pass
    if hasattr(v, "item"):
        try:
            return json_serializable(v.item())
        except Exception:
            pass
    return str(v)


def build_all_perf_json_payload(
    perf_ai: pd.DataFrame,
    perf_human: pd.DataFrame,
    *,
    data_source: str,
) -> dict[str, Any]:
    """
    One aligned JSON object per perf PR (agent + human), same keys on every record
    (missing values are null). Written to ``all_perfPR.json``.
    """
    ai = perf_ai.copy()
    hum = perf_human.copy()
    ai["subset"] = "AIDev_pop_agent"
    ai["classification_table"] = "pr_task_type.parquet"
    hum["subset"] = "human_pull_request_baseline"
    hum["classification_table"] = "human_pr_task_type.parquet"

    cols = sorted(set(ai.columns) | set(hum.columns))
    ai = ai.reindex(columns=cols)
    hum = hum.reindex(columns=cols)

    combo = pd.concat([ai, hum], ignore_index=True)
    combo = combo.sort_values(["subset", "agent", "id"], kind="stable").reset_index(drop=True)
    combo.insert(0, "all_perfPR_row_1based", np.arange(1, len(combo) + 1))

    ordered_cols = ["all_perfPR_row_1based"] + [c for c in combo.columns if c != "all_perfPR_row_1based"]

    records: list[dict[str, Any]] = []
    for _, row in combo.iterrows():
        records.append({col: json_serializable(row[col]) for col in ordered_cols})

    return {
        "meta": {
            "data_source": data_source,
            "task_type_filter": 'type == "perf"',
            "count_agent_perf": int(perf_ai.shape[0]),
            "count_human_perf": int(perf_human.shape[0]),
            "total": len(records),
            "field_order": ordered_cols,
            "description_zh": (
                "每条 pull_requests 记录字段一致；来源区分见 subset 与 classification_table。"
            ),
        },
        "pull_requests": records,
    }


def load_rejection_aux(*, local: bool) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rev = _read_parquet(
        "pr_reviews.parquet",
        local=local,
        columns=["id", "pr_id", "state", "submitted_at", "body"],
    )
    rev["submitted_at"] = pd.to_datetime(rev["submitted_at"], utc=True, errors="coerce")
    cm = _read_parquet(
        "pr_review_comments_v2.parquet",
        local=local,
        columns=["pull_request_review_id", "body", "path"],
    )
    cm_rev = cm.merge(rev[["id", "pr_id"]], left_on="pull_request_review_id", right_on="id", how="inner")
    cm_rev = cm_rev.rename(columns={"id": "review_table_id"})
    isc = _read_parquet(
        "pr_comments.parquet",
        local=local,
        columns=["pr_id", "created_at", "body", "user"],
    )
    isc["created_at"] = pd.to_datetime(isc["created_at"], utc=True, errors="coerce")
    return rev.drop(columns=["id"], errors="ignore"), cm_rev, isc


def text_bucket(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return "no_review_text_in_dataset"
    t = text.lower()
    patterns: list[tuple[str, list[str]]] = [
        ("tests_missing_or_requested", [
            r"\btest\b", r"testing", r"unit test", r"覆盖率", r"测试",
        ]),
        ("correctness_or_bug", [
            r"broken", r"bug", r"wrong", r"incorrect", r"fail", r"错误", r"不正确", r"崩溃",
        ]),
        ("design_or_approach", [
            r"design", r"approach", r"alternative", r"naming", r"api", r"设计", r"方案",
        ]),
        ("performance_related_concern", [
            r"performance", r"slow", r"latency", r"memory", r"complexity",
            r"complex", r"o\(", r"优化", r"性能", r"耗时",
        ]),
        ("build_ci_or_tooling", [
            r"\bci\b", r"build", r"lint", r"webpack", r"npm", r"pipeline", r"编译",
        ]),
    ]
    for label, regexes in patterns:
        for pat in regexes:
            if re.search(pat, t, flags=re.IGNORECASE):
                return label
    return "other_or_general_comment"


def rejection_signal_for_pr(
    pr_id: int,
    rev: pd.DataFrame,
    cm_rev: pd.DataFrame,
    isc: pd.DataFrame,
    max_chars: int = 1200,
) -> dict[str, Any]:
    """Best-effort signal for closed-unmerged PRs."""
    r = rev[rev["pr_id"] == pr_id].sort_values("submitted_at")
    ch = r[r["state"] == "CHANGES_REQUESTED"]
    body_from_changes = ""
    if not ch.empty and ch["body"].notna().any():
        raw = str(ch.iloc[-1]["body"] or "")
        body_from_changes = raw.strip()

    cms = cm_rev[cm_rev["pr_id"] == pr_id]["body"].dropna().astype(str).head(8)
    iscs = isc[isc["pr_id"] == pr_id].sort_values("created_at")["body"].dropna().astype(str).head(8)

    combined = "\n---\n".join(
        [body_from_changes] + cms.tolist() + iscs.tolist()
    ).strip()

    summary = combined[:max_chars] + ("…" if len(combined) > max_chars else "")

    if body_from_changes:
        source_primary = (
            "`pr_reviews.parquet`: 使用该 PR `pr_id` 对应行中 `state==CHANGES_REQUESTED` "
            "且按 `submitted_at` 取最近一条的 `body`"
        )
    elif len(combined) > 0:
        source_primary = (
            "`pr_review_comments_v2.parquet`（经 `pull_request_review_id` 联接 `pr_reviews.id` 得到 "
            "`pr_id`）与 `pr_comments.parquet` 的正文拼接后做关键词分桶"
        )
    else:
        source_primary = "数据集中缺少与该 `pr_id` 关联的评审/评论正文"

    return {
        "pr_id": int(pr_id),
        "snippet": summary if summary else "(empty)",
        "bucket": text_bucket(combined),
        "source_notes": source_primary,
        "had_changes_requested_body": bool(body_from_changes),
    }


def summarize_agent_perf(df_perf: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ag in AGENT_NAMES + [HUMAN_NAME]:
        sub = df_perf[df_perf["agent"] == ag]
        if sub.empty:
            continue
        merged_pct = 100 * (sub["status"] == "merged").mean()
        terminal = sub[sub["state"] == "closed"]
        term_rate = (
            100 * terminal["merged_at"].notna().mean()
            if len(terminal)
            else float("nan")
        )
        rows.append({
            "agent": ag,
            "perf_n": len(sub),
            "perf_merged_pct_all_states": merged_pct,
            "perf_merged_pct_closed_only": term_rate,
            "perf_merged_n": int((sub["status"] == "merged").sum()),
            "perf_closed_unmerged_n": int((sub["status"] == "closed").sum()),
            "perf_open_n": int((sub["status"] == "open").sum()),
        })
    return pd.DataFrame(rows)


def add_export_rows(df: pd.DataFrame, sort_cols: list[str]) -> pd.DataFrame:
    out = df.sort_values(sort_cols).reset_index(drop=True)
    out.insert(0, "export_row_1based", np.arange(1, len(out) + 1))
    return out


def plot_dashboard(
    summary_rows: pd.DataFrame,
    total_agent: int,
    total_human: int,
    out_fp: Path,
) -> None:
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    ag = summary_rows[summary_rows["agent"] != HUMAN_NAME].sort_values("perf_n", ascending=True)
    ax = axes[0, 0]
    ax.barh(ag["agent"], ag["perf_n"])
    ax.set_title("AIDev-pop: perf PR count by agent")
    ax.set_xlabel("count")

    hum = summary_rows[summary_rows["agent"] == HUMAN_NAME]
    ax = axes[0, 1]
    labels = ["Agents (sum)", "Human"]
    counts = [total_agent, int(hum["perf_n"].iloc[0]) if not hum.empty else 0]
    ax.bar(labels, counts, color=["#888", "#56B4E9"])
    ax.set_title("perf PR volume: pooled agents vs Human")
    ax.set_ylabel("Count")

    ax = axes[1, 0]
    agents = summary_rows["agent"].tolist()
    x = np.arange(len(agents))
    w = 0.38
    ax.bar(
        x - w / 2,
        summary_rows["perf_merged_pct_all_states"].tolist(),
        width=w,
        label="merged % (includes open)",
        alpha=0.9,
    )
    closed_only = summary_rows["perf_merged_pct_closed_only"].fillna(0).tolist()
    ax.bar(x + w / 2, closed_only, width=w, label="merged % (closed PRs only)", alpha=0.75)
    ax.set_xticks(x)
    ax.set_xticklabels(agents)
    ax.set_title("perf PR merge rates (both definitions)")
    ax.set_ylabel("Percentage")
    ax.legend()
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")

    ax = axes[1, 1]
    share_agent = total_agent / (total_agent + counts[1]) * 100 if (total_agent + counts[1]) else 0
    ax.pie([total_agent, counts[1]], labels=["Agent perf", "Human perf"], autopct="%1.1f%%")
    ax.set_title(f"perf split: Agents {share_agent:.1f}% vs Human {100-share_agent:.1f}%")

    fig.tight_layout()
    out_fp.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_fp, dpi=200, bbox_inches="tight")
    plt.close(fig)


def build_cited_examples(
    df_perf: pd.DataFrame,
    rev: pd.DataFrame,
    cm_rev: pd.DataFrame,
    isc: pd.DataFrame,
    *,
    which: str,
) -> list[dict[str, Any]]:
    closed = df_perf[df_perf["status"] == "closed"]
    picks: list[int] = []
    # Prefer PRs that have structured review text
    for pid in closed["id"].tolist():
        r = rev[(rev["pr_id"] == pid) & (rev["state"] == "CHANGES_REQUESTED")]
        if not r.empty:
            picks.append(int(pid))
        if len(picks) >= 3:
            break
    # Backfill arbitrary closed
    rest = [int(i) for i in closed["id"].tolist() if int(i) not in picks]
    picks.extend(rest[: max(0, 3 - len(picks))])

    rows_out: list[dict[str, Any]] = []
    pr_lookup = df_perf.set_index("id")
    for pid in picks:
        sig = rejection_signal_for_pr(pid, rev, cm_rev, isc)
        prow = pr_lookup.loc[pid]
        row_num = int(prow["export_row_1based"]) if "export_row_1based" in prow else -1
        fname = (
            "performance_prs_agents.parquet"
            if which == "agent"
            else "performance_prs_human.parquet"
        )
        rows_out.append({
            "cohort": which,
            "pr_id": pid,
            "agent": prow["agent"],
            "export_row_in_output_parquet": row_num,
            "output_parquet": f"MyStudy/output/{fname}（列 export_row_1based）",
            "html_url": str(prow.get("html_url", "")),
            "title": str(prow.get("title", "")),
            "llm_task_type_reason_from_pr_task_type": str(prow.get("reason", "")),
            "derived_rejection_bucket": sig["bucket"],
            "review_snippet": sig["snippet"],
            "signal_provenance_zh": sig["source_notes"],
        })
    merged_samples = df_perf[df_perf["status"] == "merged"].head(2)
    for _, prow in merged_samples.iterrows():
        pid = int(prow["id"])
        row_num = int(prow["export_row_1based"]) if "export_row_1based" in prow.index else -1
        fname = (
            "performance_prs_agents.parquet"
            if which == "agent"
            else "performance_prs_human.parquet"
        )
        rows_out.append({
            "cohort": which,
            "pr_id": pid,
            "agent": prow["agent"],
            "export_row_in_output_parquet": row_num,
            "output_parquet": f"MyStudy/output/{fname}",
            "outcome": "merged",
            "html_url": str(prow.get("html_url", "")),
            "title": str(prow.get("title", "")),
        })
    return rows_out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true", help="Read Parquet files from ../AIDev")
    args = parser.parse_args()
    local: bool = args.local

    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    # --- Agent PR + labels ---
    pr_ai = _read_parquet("pull_request.parquet", local=local)
    lbl_ai = _read_parquet("pr_task_type.parquet", local=local)
    pr_ai_i = merge_pr_labels(pr_ai, lbl_ai)
    pr_human = _read_parquet("human_pull_request.parquet", local=local)
    lbl_human = _read_parquet("human_pr_task_type.parquet", local=local)
    pr_h_i = merge_pr_labels(pr_human, lbl_human)

    total_agent_pr = len(pr_ai)
    total_human_pr = len(pr_human)

    perf_ai = attach_status(pr_ai_i[pr_ai_i["type"] == "perf"].copy())
    perf_human = attach_status(pr_h_i[pr_h_i["type"] == "perf"].copy())

    perf_ai_e = add_export_rows(perf_ai, ["agent", "id"])
    perf_h_e = add_export_rows(perf_human, ["id"])

    perf_ai_e.to_parquet(OUT / "performance_prs_agents.parquet", index=False)
    perf_h_e.to_parquet(OUT / "performance_prs_human.parquet", index=False)

    all_perf_payload = build_all_perf_json_payload(
        perf_ai_e,
        perf_h_e,
        data_source="local AIDEV dir" if local else HF_BASE,
    )
    with open(OUT / "all_perfPR.json", "w", encoding="utf-8") as f:
        json.dump(all_perf_payload, f, ensure_ascii=False, indent=2)

    rev, cm_rev, isc = load_rejection_aux(local=local)

    merged_pct_agents_overall = 100 * (perf_ai_e["status"] == "merged").mean()
    merged_pct_human_overall = 100 * (perf_h_e["status"] == "merged").mean()

    summary_agent = summarize_agent_perf(perf_ai_e)
    summary_human = summarize_agent_perf(perf_h_e)
    summary_combo = pd.concat([summary_agent, summary_human], ignore_index=True)

    ratio_perf_to_all = {
        "agent_perf_over_agent_all_pr": perf_ai_e.shape[0] / total_agent_pr if total_agent_pr else 0,
        "human_perf_over_human_all_pr": perf_h_e.shape[0] / total_human_pr if total_human_pr else 0,
        "human_perf_over_agent_perf": perf_h_e.shape[0] / perf_ai_e.shape[0] if perf_ai_e.shape[0] else 0,
        "combined_perf_share_agent": perf_ai_e.shape[0]
        / (perf_ai_e.shape[0] + perf_h_e.shape[0])
        if (perf_ai_e.shape[0] + perf_h_e.shape[0])
        else 0,
    }

    rejection_profiles: list[dict[str, Any]] = []
    for cohort_name, cohort_df in ("agent", perf_ai_e), ("human", perf_h_e):
        closed_um = cohort_df[cohort_df["status"] == "closed"]
        buckets: dict[str, int] = {}
        for pid in closed_um["id"].tolist():
            sig = rejection_signal_for_pr(int(pid), rev, cm_rev, isc)
            buckets[sig["bucket"]] = buckets.get(sig["bucket"], 0) + 1
        rejection_profiles.append({
            "cohort": cohort_name,
            "closed_unmerged_n": len(closed_um),
            "bucket_counts": buckets,
        })

    metrics = {
        "data_source": "local AIDEV dir" if local else HF_BASE,
        "total_pr_pull_request_parquet_agent_pop": total_agent_pr,
        "total_pr_human_pull_request_parquet": total_human_pr,
        "perf_pr_count_agent_side": perf_ai_e.shape[0],
        "perf_pr_count_human_side": perf_h_e.shape[0],
        "perf_pr_count_ratio_vs_total_agent_pr": ratio_perf_to_all["agent_perf_over_agent_all_pr"],
        "perf_pr_count_ratio_vs_total_human_pr": ratio_perf_to_all["human_perf_over_human_all_pr"],
        "ratio_human_perf_over_agent_perf": ratio_perf_to_all["human_perf_over_agent_perf"],
        "merge_rate_notes_zh": (
            "merged_pct 与 analysis/productivity.ipynb 一致：分母包含 open PR；"
            "另参见 perf_merged_pct_closed_only。"
        ),
        "perf_merge_rate_agents_pooled_pct": merged_pct_agents_overall,
        "perf_merge_rate_human_pct": merged_pct_human_overall,
        "per_agent_and_human_breakdown_records": summary_combo.to_dict(orient="records"),
        "closed_unmerged_rejection_signal_profiles": rejection_profiles,
        "parquet_sources_for_classification": [
            "hf://datasets/hao-li/AIDev/pr_task_type.parquet（列 type, reason）",
            "hf://datasets/hao-li/AIDev/human_pr_task_type.parquet",
        ],
    }

    examples = []
    examples.extend(build_cited_examples(perf_ai_e, rev, cm_rev, isc, which="agent"))
    examples.extend(build_cited_examples(perf_h_e, rev, cm_rev, isc, which="human"))

    # Fix ratio key that was sloppy
    metrics["combined_perf_over_combined_supervision_pr"] = (
        (perf_ai_e.shape[0] + perf_h_e.shape[0]) / (total_agent_pr + total_human_pr)
        if (total_agent_pr + total_human_pr)
        else 0
    )
    metrics["all_perf_json"] = "MyStudy/output/all_perfPR.json"

    with open(OUT / "summary_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    with open(OUT / "rejection_signal_examples.json", "w", encoding="utf-8") as f:
        json.dump(examples, f, ensure_ascii=False, indent=2)

    plot_dashboard(
        summary_combo,
        total_agent=perf_ai_e.shape[0],
        total_human=perf_h_e.shape[0],
        out_fp=FIG / "performance_pr_dashboard.png",
    )

    # --- printable markdown appendix for the user ---
    lines = [
        "# 运行结果概要（自动生成）\n",
        f"- 数据源：`{metrics['data_source']}`\n",
        f"- Agent 全体 PR：`pull_request.parquet` 共 **{total_agent_pr}**，其中 perf **{perf_ai_e.shape[0]}**（"
        f"{100 * perf_ai_e.shape[0] / total_agent_pr:.2f}%）\n",
        f"- Human PR：`human_pull_request.parquet` 共 **{total_human_pr}**，其中 perf **{perf_h_e.shape[0]}**（"
        f"{100 * perf_h_e.shape[0] / total_human_pr:.2f}%）\n",
        f"- Agent perf 合并率（含 open，`productivity.ipynb` 口径）：**{merged_pct_agents_overall:.2f}%**\n",
        f"- Human perf 合并率（同上）：**{merged_pct_human_overall:.2f}%**\n",
        "\n",
        f"- **全量 perf PR（Agent+Human）JSON**：`MyStudy/output/all_perfPR.json`（共 **"
        f"{perf_ai_e.shape[0] + perf_h_e.shape[0]}** 条，`pull_requests` 数组逐项字段对齐）\n",
        "\n## 逐 Agent / Human perf 计数与合并率\n\n",
        summary_combo.to_string(index=False),
        "\n",
    ]
    with open(OUT / "SUMMARY_zh.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("Wrote outputs to", OUT)


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
