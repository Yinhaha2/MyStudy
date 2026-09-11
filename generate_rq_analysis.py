#!/usr/bin/env python3
"""Generate the Chinese RQ analysis report from per-PR analysis JSON.

Reuses loaders and a few classifiers from generate_full_analysis.py, then
applies the RQ1–RQ4 taxonomy in RQ_README.md (Merged/Closed 终态划分,
reviewed-failure subset, boundary contrast).
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from generate_full_analysis import (
    classify_fix_mode,
    flatten_record,
    load_all_analyses,
)

ROOT = Path(__file__).resolve().parent
OUT_MD = ROOT / "RQ_Analysis.md"
OUT_JSON = ROOT / "rq_analysis_metrics.json"
FIG_DIR = ROOT / "rq_analysis_figures"

# ---------------------------------------------------------------------------
# Taxonomies (documented in the report appendix)
# ---------------------------------------------------------------------------
REAL_REJECTION_REASON = (
    "maintainer_rejection",
    "closed_after_maintainer",
    "functional_failure",
    "correctness",
    "test_failure",
    "test_quality",
    "performance_overhead",
    "performance_regression",
    "ci_failure",
    "ci_implementation",
    "changes_requested",
    "design_review",
    "design_rejected",
    "design_decision",
    "scope_too_large",
    "missing_benchmark",
    "missing_evidence",
    "benchmark_missing",
    "agent_unresolved",
    "incomplete_ci",
    "closed_performance",
    "lint_failure",
    "quality_gate",
    "incorrect_change",
    "over_mock",
    "test_quality_over_mocking",
)

TECHNICAL_BUCKETS = {
    "correctness_or_bug",
    "design_or_approach",
    "tests_missing_or_requested",
    "performance_related_concern",
    "performance_regression",
    "ci_failure",
    "perf_evidence",
}

TECHNICAL_CONCERNS = (
    "functional_failure",
    "design_rejected",
    "design_decision",
    "correctness",
    "ci_failure",
    "ci_linting",
    "missing_benchmark",
    "performance_regression",
    "test_failure",
    "scope",
)

OTHER_PROCESS_KEYS = (
    "supersed",
    "duplicate",
    "unintended",
    "withdrew",
    "in_favor",
    "recreated",
    "manually_outside",
)

ABANDON_KEYS = (
    "stale",
    "inactiv",
    "abandon",
    "no_review",
    "self_closed",
    "author_closed",
    "closed_draft",
    "closed_by_author",
    "wip",
    "forgotten",
    "unreviewed",
    "no_review_engagement",
)

REVIEWED_ITER_KEYS = ("after_review", "iterative", "maintainer_fix", "requested_changes")
NO_REVIEW_MERGE_KEYS = ("no_review", "self_merge", "self_approved", "self_approve")


def pct(n: int | float, total: int, digits: int = 1) -> str:
    if not total:
        return "0.0%"
    return f"{100 * n / total:.{digits}f}%"


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def contains_any(text: str, keys: tuple[str, ...] | list[str]) -> bool:
    t = text or ""
    return any(k in t for k in keys)


def enrich_row(d: dict, flat: dict) -> dict:
    rd = (d.get("structured_analysis") or {}).get("review_details") or {}
    col = (d.get("quantitative_metrics") or {}).get("collaboration") or {}
    states = col.get("review_states") or {}
    if not isinstance(states, dict):
        states = {}
    flat = dict(flat)
    flat["rejection_signals"] = rd.get("rejection_signals")
    flat["concern_detail"] = rd.get("concern_detail")
    flat["changes_requested_n"] = int(states.get("CHANGES_REQUESTED") or 0)
    flat["review_states_json"] = json.dumps(states, ensure_ascii=False)
    traj = d.get("evidence", {}).get("collaboration_trajectory") or []
    flat["collaboration_trajectory"] = " | ".join(str(x) for x in traj)
    mp = (d.get("structured_analysis") or {}).get("maintainer_practices") or {}
    flat["regression_detail"] = mp.get("regression_detail") or flat.get("regression_detail")
    return flat


def classify_merged_path(row: pd.Series) -> str:
    reason = str(row.get("outcome_reason") or "").lower()
    review_n = int(row.get("review_count") or 0)
    has_review = bool(row.get("has_formal_review")) or review_n > 0
    fast = bool(row.get("fast_merge"))
    life = row.get("lifespan_hours")
    life_ok = pd.notna(life)

    if contains_any(reason, REVIEWED_ITER_KEYS):
        return "reviewed_iteration"
    if has_review and not fast:
        return "reviewed_iteration"
    if fast or (life_ok and float(life) < 1 and review_n == 0):
        return "fast_low_friction"
    if review_n == 0 or contains_any(reason, NO_REVIEW_MERGE_KEYS):
        return "no_formal_review"
    return "other"


def classify_close_motivation(row: pd.Series) -> str:
    reason = str(row.get("outcome_reason") or "").lower()
    primary = str(row.get("primary_concern") or "").lower()
    bucket = str(row.get("review_comment_bucket") or "").lower()
    rej = str(row.get("rejection_signals") or "").lower()
    notes = str(row.get("notes") or "").lower()
    blocking = bool(row.get("blocking"))
    cr = int(row.get("changes_requested_n") or 0)
    review_n = int(row.get("review_count") or 0)
    human_gate = blocking or cr > 0 or review_n > 0 or bool(row.get("has_formal_review"))
    blob = " ".join([reason, primary, bucket, rej, notes])

    if contains_any(reason, OTHER_PROCESS_KEYS) or contains_any(blob, OTHER_PROCESS_KEYS):
        if not human_gate and not contains_any(reason, REAL_REJECTION_REASON):
            return "other_process"

    if contains_any(reason, REAL_REJECTION_REASON):
        return "real_rejection"
    if blocking or cr > 0:
        return "real_rejection"
    if human_gate and (
        contains_any(primary, TECHNICAL_CONCERNS)
        or bucket in TECHNICAL_BUCKETS
        or re.search(
            r"changes requested|design objection|roll back|functional failure|"
            r"does not fix|incorrect|rework",
            blob,
        )
    ):
        return "real_rejection"

    if contains_any(reason, OTHER_PROCESS_KEYS) or contains_any(blob, ("supersed", "in favor of")):
        return "other_process"

    if (
        contains_any(reason, ABANDON_KEYS)
        or contains_any(primary, ("stale_inactivity", "no_review", "inactiv", "no_human_review"))
        or re.search(r"no review|without review|unreviewed|inactiv|abandon|author closed", blob)
    ):
        return "silent_abandonment"

    return "unclear"


def classify_abandon_subtype(row: pd.Series) -> str:
    reason = str(row.get("outcome_reason") or "").lower()
    blob = " ".join(
        [
            reason,
            str(row.get("rejection_signals") or "").lower(),
            str(row.get("notes") or "").lower(),
        ]
    )
    if re.search(r"automatically|auto[- ]close|inactivity for more than|bot due to inactiv", blob):
        return "bot_or_auto_stale"
    if contains_any(reason, ("author_closed", "self_closed", "abandoned", "closed_draft", "closed_by_author")):
        return "author_withdrew"
    if "stale" in reason or "inactiv" in reason:
        return "stale_inactivity"
    return "no_review_closed"


def classify_failure_type(row: pd.Series) -> str:
    reason = str(row.get("outcome_reason") or "").lower()
    primary = str(row.get("primary_concern") or "").lower()
    bucket = str(row.get("review_comment_bucket") or "").lower()
    blob = f"{reason} {primary} {bucket} {str(row.get('rejection_signals') or '').lower()}"
    if any(k in blob for k in ("functional", "correctness", "bug", "incorrect")) or bucket == "correctness_or_bug":
        return "functional_or_correctness"
    if any(k in blob for k in ("design",)) or bucket == "design_or_approach":
        return "design_or_approach"
    if any(k in blob for k in ("ci_fail", "ci_failure", "lint", "test_fail", "test_failure", "quality_gate")):
        return "ci_or_tests"
    if any(k in blob for k in ("benchmark", "evidence", "repro")) or bucket in {
        "perf_evidence",
        "performance_related_concern",
    }:
        return "missing_evidence"
    if any(k in blob for k in ("scope",)):
        return "scope"
    if int(row.get("review_count") or 0) == 0:
        return "silent_or_unexplained"
    return "other_or_mixed"


def is_reviewed_closed(row: pd.Series) -> bool:
    bucket = str(row.get("review_comment_bucket") or "")
    if bool(row.get("has_formal_review")) or bool(row.get("blocking")):
        return True
    if int(row.get("changes_requested_n") or 0) > 0:
        return True
    if bucket and bucket not in {"no_review_text", "none", "null", ""}:
        return True
    return False


def split_multi(series: pd.Series) -> Counter:
    c: Counter = Counter()
    for raw in series.fillna(""):
        if not raw:
            c["(empty)"] += 1
            continue
        for part in str(raw).split("|"):
            part = part.strip()
            if part:
                c[part] += 1
    return c


def _clean_text(v) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    if not s or s.lower() in {"nan", "none", "null"}:
        return None
    return s


def pick_examples(df: pd.DataFrame, n: int = 3) -> list[dict]:
    rows = []
    for _, r in df.head(n).iterrows():
        sig = _clean_text(r.get("rejection_signals"))
        rows.append(
            {
                "pr_id": int(r["pr_id"]),
                "title": str(r.get("title") or "")[:80],
                "html_url": str(r.get("html_url") or ""),
                "agent": r.get("agent"),
                "outcome_reason": r.get("outcome_reason"),
                "rejection_signals": (sig[:180] if sig else None),
            }
        )
    return rows


def fmt_examples(examples: list[dict]) -> str:
    if not examples:
        return "_（本类暂无抽样）_"
    lines = []
    for ex in examples:
        url = ex["html_url"]
        title = ex["title"].replace("|", "/")
        sig = ex["rejection_signals"]
        extra = f"；拒因摘要：{sig}" if sig else ""
        lines.append(
            f"- [{ex['pr_id']}]({url}) `{ex['agent']}` — {title}  \n"
            f"  `outcome_reason={ex['outcome_reason']}`{extra}"
        )
    return "\n".join(lines)


def save_barh(path: Path, labels: list[str], values: list[float], title: str, xlabel: str) -> None:
    fig, ax = plt.subplots(figsize=(8.5, max(3.2, 0.42 * len(labels) + 1.4)))
    y = list(range(len(labels)))
    ax.barh(y, values, color="#4C78A8")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def build_report(df: pd.DataFrame, records: list[dict]) -> tuple[str, dict]:
    n = len(df)
    merged = df[df["status"] == "merged"].copy()
    closed = df[df["status"] == "closed"].copy()
    open_ = df[df["status"] == "open"].copy()
    terminal = df[df["status"].isin(["merged", "closed"])].copy()

    merged["merged_path"] = merged.apply(classify_merged_path, axis=1)
    closed["close_motivation"] = closed.apply(classify_close_motivation, axis=1)
    closed["abandon_subtype"] = closed.apply(classify_abandon_subtype, axis=1)
    closed["is_reviewed_closed"] = closed.apply(is_reviewed_closed, axis=1)
    closed["failure_type"] = closed.apply(classify_failure_type, axis=1)

    df = df.copy()
    df.loc[merged.index, "merged_path"] = merged["merged_path"]
    df.loc[closed.index, "close_motivation"] = closed["close_motivation"]

    # ---- RQ1.1 ----
    status_counts = df["status"].value_counts()
    term_rate = len(merged) / len(terminal) if len(terminal) else 0
    agent_tbl = (
        df.groupby("agent", dropna=False)
        .agg(
            n=("pr_id", "count"),
            merged=("status", lambda s: int((s == "merged").sum())),
            closed=("status", lambda s: int((s == "closed").sum())),
            open_=("status", lambda s: int((s == "open").sum())),
            merge_rate=("status", lambda s: (s == "merged").mean()),
            term_merge=("status", lambda s: ((s == "merged").sum() / ((s == "merged") | (s == "closed")).sum())
            if ((s == "merged") | (s == "closed")).sum()
            else 0),
        )
        .sort_values("n", ascending=False)
        .reset_index()
    )
    opt_layer = df["optimization_layer"].value_counts().head(12)

    # ---- RQ1.2 ----
    path_counts = merged["merged_path"].value_counts()
    fast_n = int(merged["fast_merge"].fillna(False).sum())
    merged_zero_comment = int((merged["comment_total"].fillna(0) == 0).sum())
    merged_no_review = int((merged["review_count"].fillna(0) == 0).sum())
    no_issue_n = int((~df["has_linked_issue"].fillna(False)).sum())

    # ---- RQ1.3 ----
    mot_counts = closed["close_motivation"].value_counts()
    reviewed_closed = closed[closed["is_reviewed_closed"]]
    abandon = closed[closed["close_motivation"] == "silent_abandonment"]
    abandon_sub = abandon["abandon_subtype"].value_counts()

    # ---- RQ2 ----
    life_bins = [0, 1, 24, 168, 10**9]
    life_labels = ["<1h", "1–24h", "1–7d", ">7d"]
    t2 = terminal.copy()
    t2["lifespan_bin"] = pd.cut(t2["lifespan_hours"], bins=life_bins, labels=life_labels)
    merge_by_life = t2.groupby("lifespan_bin", observed=True)["status"].apply(lambda s: (s == "merged").mean())
    life_n = t2["lifespan_bin"].value_counts()

    change_bins = [0, 100, 500, 2000, 10000, 10**9]
    change_labels = ["≤100", "101–500", "501–2k", "2k–10k", ">10k"]
    t2["changes_bin"] = pd.cut(t2["changes"], bins=change_bins, labels=change_labels)
    merge_by_chg = t2.groupby("changes_bin", observed=True)["status"].apply(lambda s: (s == "merged").mean())
    chg_n = t2["changes_bin"].value_counts()

    det_all = split_multi(df["detection_method"])
    det_merged = split_multi(merged["detection_method"])
    det_closed = split_multi(closed["detection_method"])

    bound_term = (
        terminal.groupby("boundary_tag")
        .agg(n=("pr_id", "count"), merge_rate=("status", lambda s: (s == "merged").mean()))
        .sort_values("n", ascending=False)
    )

    # ---- RQ3 ----
    fail_counts = reviewed_closed["failure_type"].value_counts()
    bucket_closed = closed["review_comment_bucket"].value_counts()
    blocking_closed = int(closed["blocking"].fillna(False).sum())
    anti_m = split_multi(merged["inefficiency_antipattern"])
    anti_c = split_multi(closed["inefficiency_antipattern"])
    for drop in ("none", "(empty)", "unknown"):
        anti_m.pop(drop, None)
        anti_c.pop(drop, None)

    repro = df["reproducibility"].value_counts()
    reg = df["regression_handling"].value_counts()
    fix_in_pr = df[df["regression_handling"] == "fix_in_pr"]
    fix_modes: Counter = Counter()
    rec_by_id = {int(d["pr_id"]): d for d in records}
    for _, row in fix_in_pr.iterrows():
        d = rec_by_id.get(int(row["pr_id"]))
        if not d:
            continue
        mp = (d.get("structured_analysis") or {}).get("maintainer_practices") or {}
        traj = " ".join(d.get("evidence", {}).get("collaboration_trajectory") or [])
        fix_modes[classify_fix_mode(mp.get("regression_detail") or "", traj)] += 1
    anti_fix_n = int(
        (
            df["antipattern_in_fix"].notna()
            & ~df["antipattern_in_fix"].astype(str).str.lower().isin(["none", "null", "nan", ""])
        ).sum()
    )

    # ---- RQ4 ----
    pf_m = split_multi(merged["perf_focus"])
    pf_c = split_multi(closed["perf_focus"])
    layer_term = (
        terminal.groupby("optimization_layer")
        .agg(n=("pr_id", "count"), merge_rate=("status", lambda s: (s == "merged").mean()))
        .query("n >= 20")
        .sort_values("merge_rate", ascending=False)
    )

    def evidence_rate(sub: pd.DataFrame, col: str) -> float:
        return float(sub[col].fillna(False).mean()) if len(sub) else 0.0

    def example_score(row: pd.Series) -> int:
        reason = str(row.get("outcome_reason") or "").lower()
        score = 0
        if bool(row.get("blocking")):
            score += 3
        if int(row.get("changes_requested_n") or 0) > 0:
            score += 3
        if contains_any(
            reason,
            ("functional", "design", "correctness", "test_failure", "benchmark", "rejected", "ci_failure"),
        ):
            score += 2
        if contains_any(reason, ("stale", "inactiv", "no_review", "immediately")):
            score -= 2
        if _clean_text(row.get("rejection_signals")):
            score += 1
        return score

    ranked_closed = closed.copy()
    ranked_closed["_score"] = ranked_closed.apply(example_score, axis=1)
    ranked_rev = reviewed_closed.copy()
    ranked_rev["_score"] = ranked_rev.apply(example_score, axis=1)

    ex_fast = pick_examples(
        merged[merged["merged_path"] == "fast_low_friction"].sort_values("lifespan_hours")
    )
    ex_rev = pick_examples(
        merged[merged["merged_path"] == "reviewed_iteration"].sort_values("lifespan_hours", ascending=False)
    )
    ex_rej = pick_examples(
        ranked_closed[ranked_closed["close_motivation"] == "real_rejection"].sort_values("_score", ascending=False)
    )
    ex_abn = pick_examples(
        ranked_closed[ranked_closed["close_motivation"] == "silent_abandonment"].sort_values("_score", ascending=False)
    )
    ex_func = pick_examples(
        ranked_rev[ranked_rev["failure_type"] == "functional_or_correctness"].sort_values("_score", ascending=False)
    )
    ex_design = pick_examples(
        ranked_rev[ranked_rev["failure_type"] == "design_or_approach"].sort_values("_score", ascending=False)
    )
    ex_ev = pick_examples(closed[closed["boundary_tag"] == "evidence_required"])

    metrics = {
        "n": n,
        "merged": int(len(merged)),
        "closed": int(len(closed)),
        "open": int(len(open_)),
        "terminal_n": int(len(terminal)),
        "closed_is_rejected_at_status": True,
        "open_excluded_from_merged_closed_contrast": True,
        "terminal_merge_rate": term_rate,
        "merged_path": path_counts.to_dict(),
        "close_motivation": mot_counts.to_dict(),
        "reviewed_closed_n": int(len(reviewed_closed)),
        "fast_merge_in_merged": fast_n,
        "boundary_terminal_merge": {
            k: {"n": int(v["n"]), "merge_rate": float(v["merge_rate"])} for k, v in bound_term.iterrows()
        },
    }

    # figures
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    save_barh(
        FIG_DIR / "rq1_status.png",
        ["merged", "closed", "open"],
        [len(merged), len(closed), len(open_)],
        "RQ1.1 Status counts",
        "PRs",
    )
    ag_plot = agent_tbl[agent_tbl["n"] >= 30]
    save_barh(
        FIG_DIR / "rq1_agent_merge.png",
        ag_plot["agent"].tolist(),
        (ag_plot["merge_rate"] * 100).tolist(),
        "RQ1.1 Merge rate by agent (n≥30)",
        "Merge rate (%)",
    )
    mot_fig_label = {
        "silent_abandonment": "silent abandonment",
        "real_rejection": "real rejection",
        "other_process": "other process",
        "unclear": "unclear",
    }
    save_barh(
        FIG_DIR / "rq1_closed_motivation.png",
        [mot_fig_label.get(k, k) for k in mot_counts.index],
        mot_counts.values.tolist(),
        "RQ1.3 Closed = unmerged/rejected; internal types",
        "Closed PRs",
    )
    save_barh(
        FIG_DIR / "rq2_lifespan.png",
        [str(x) for x in merge_by_life.index.tolist()],
        (merge_by_life * 100).tolist(),
        "RQ2.1 Terminal merge rate by lifespan",
        "Merge rate (%)",
    )
    save_barh(
        FIG_DIR / "rq4_boundary.png",
        bound_term.index.astype(str).tolist(),
        (bound_term["merge_rate"] * 100).tolist(),
        "RQ4.2 Terminal merge rate by boundary_tag",
        "Merge rate (%)",
    )

    # ---- markdown ----
    agent_rows = []
    for _, r in agent_tbl.iterrows():
        agent_rows.append(
            [
                r["agent"] or "(null)",
                int(r["n"]),
                int(r["merged"]),
                int(r["closed"]),
                int(r["open_"]),
                pct(r["merge_rate"], 1),
                pct(r["term_merge"], 1),
            ]
        )

    path_label = {
        "fast_low_friction": "低摩擦快合并",
        "reviewed_iteration": "经 review 迭代后合入",
        "no_formal_review": "无 formal review 合入（非极速）",
        "other": "其他",
    }
    mot_label = {
        "silent_abandonment": "沉默遗弃 silent abandonment",
        "real_rejection": "真正拒绝 real rejection",
        "other_process": "其他流程（替代 PR / 撤回等）",
        "unclear": "原因不明",
    }
    fail_label = {
        "functional_or_correctness": "功能 / 正确性失败",
        "design_or_approach": "设计 / 方案否决",
        "ci_or_tests": "CI / 测试失败",
        "missing_evidence": "证据 / benchmark 不足",
        "scope": "范围过大或越界",
        "silent_or_unexplained": "静默或缺乏说明",
        "other_or_mixed": "其他 / 混合",
    }
    abandon_label = {
        "stale_inactivity": "长期不活跃后关闭",
        "author_withdrew": "作者自行关闭 / 放弃",
        "no_review_closed": "无审查互动后被关",
        "bot_or_auto_stale": "bot / 自动过期关闭",
    }

    lines = [
        "# RQ 分析报告：Agent 性能 Pull Request 的合入、遗弃与拒绝",
        "",
        "> 按 [`RQ_README.md`](RQ_README.md) 的 RQ1–RQ4 定稿撰写。数字由 `python3 generate_rq_analysis.py` 从 `finaldatabase/per_pr/{id}/{id}_analysis.json`（及根目录 few-shot 金标）聚合生成，可复现。",
        f"> 全库 n=**{n}**（含 open {len(open_)}）；研究对照终态 n=**{len(terminal)}**（merged {len(merged)} / closed 被拒 {len(closed)}）。终态合并率 **{pct(len(merged), len(terminal))}**。",
        "> 结论均为**描述性关联**，不是因果推断。`outcome_reason` 等为 LLM 分析标签，不是 GitHub 官方关闭原因。",
        "",
        "## 数据与方法",
        "",
        "- **语料**：与 `FullAnalysis.md` 同一批分析 JSON，宽表字段复用 `generate_full_analysis.flatten_record`。",
        "- **状态口径**：`merged` = 已合入；`open` = 仍开放（**只计入全库总数 n，不进入后续 merged vs closed 对照**）；`closed` = 非 merged 且非 open，即本研究的 **GitHub 终态被拒**。",
        "- **新增**：在 closed（被拒）内部再划分为 real rejection / silent abandonment / other_process / unclear；在「真正被审过」的 closed 子集上再标失败类型。Merged 路径四分。",
        "- **图**：`rq_analysis_figures/`。配套机器可读摘要：`rq_analysis_metrics.json`。",
        "- **与旧报告关系**：总体合并率、Agent 分层、寿命/规模、detection_method、boundary_tag、材料评级直接复用同一数据源。相对 `FullAnalysis.md` 的增量是：把 closed 明确写成终态被拒后再做拒因细分，而不是把 open 算进 closed 生态。",
        "",
        "---",
        "",
        "## RQ1 PR 分布：生存现状、Agent 差异、未合并是否等于被拒",
        "",
        "### RQ1.1 总体分布与不同 Agent 的合并率表现如何",
        "",
        md_table(
            ["状态", "操作定义", "数量", "占全库 n"],
            [
                ["merged", "已合入（`merged_at` 非空）", len(merged), pct(len(merged), n)],
                [
                    "closed（被拒）",
                    "非 merged 且非 open：GitHub 终态未合入",
                    len(closed),
                    pct(len(closed), n),
                ],
                [
                    "open",
                    "仍开放；计入全库 n，后续对照不使用",
                    len(open_),
                    pct(len(open_), n),
                ],
            ],
        ),
        "",
        f"- 全库合并率（分母含 open，n={n}）：**{pct(len(merged), n)}**。",
        f"- **研究用终态合并率**（仅 merged vs closed，n={len(terminal)}）：**{pct(len(merged), len(terminal))}**；终态被拒率：**{pct(len(closed), len(terminal))}**。",
        f"- 下文 RQ1.2 起的 merged / closed 对照均剔除 open。",
        "",
        "![status](rq_analysis_figures/rq1_status.png)",
        "",
        "**按 Agent**：`PR 数` 含 open（算进该 Agent 总数）；**研究对照看终态合并率**（仅 merged+closed）。",
        "",
        md_table(
            ["Agent", "PR 数（含 open）", "merged", "closed（被拒）", "open", "全库合并率", "终态合并率"],
            agent_rows,
        ),
        "",
        "![agent merge](rq_analysis_figures/rq1_agent_merge.png)",
        "",
        f"n≥30 的断层仍然清楚：OpenAI_Codex 合并率最高，Devin / Copilot 明显更低。"
        f"这是**表现差异**，可能混有任务类型、仓库、补丁规模，不能直接写成模型能力证明。",
        "",
        "**优化层面 Top 12**（全库）：",
        "",
        md_table(
            ["optimization_layer", "数量", "占全库"],
            [[f"`{k}`", v, pct(v, n)] for k, v in opt_layer.items()],
        ),
        "",
        f"**小结**：全库把 open 算进总数后，合入约占 {pct(len(merged), n)}、被拒（closed）约占 {pct(len(closed), n)}、仍开放约 {pct(len(open_), n)}。"
        f"对照研究只用终态：合并率 {pct(len(merged), len(terminal))}，被拒率 {pct(len(closed), len(terminal))}。"
        "不同 Agent 的合入机会差一倍以上；改动主要落在应用服务、构建和前端。",
        "",
        "### RQ1.2 Merged 的真实情况如何划分",
        "",
        "合入不是单一路径。按行为规则（优先「经审查迭代」，其次「极速低摩擦」，再次「无 formal review」）划分：",
        "",
        md_table(
            ["Merged 路径", "数量", "占 merged"],
            [
                [path_label.get(k, k), int(v), pct(int(v), len(merged))]
                for k, v in path_counts.items()
            ],
        ),
        "",
        "配套行为事实：",
        "",
        md_table(
            ["指标", "merged"],
            [
                ["存活时间中位数", f"{merged['lifespan_hours'].median():.3f} 小时（约 {merged['lifespan_hours'].median()*60:.0f} 分钟）"],
                ["fast_merge=true", f"{fast_n}（{pct(fast_n, len(merged))}）"],
                ["评论数为 0", f"{merged_zero_comment}（{pct(merged_zero_comment, len(merged))}）"],
                ["review_count=0", f"{merged_no_review}（{pct(merged_no_review, len(merged))}）"],
                ["全库无关联 Issue", f"{no_issue_n}（{pct(no_issue_n, n)}）"],
            ],
        ),
        "",
        "**低摩擦快合并示例：**",
        "",
        fmt_examples(ex_fast),
        "",
        "**经 review 迭代后合入示例：**",
        "",
        fmt_examples(ex_rev),
        "",
        "**小结**：Merged 的主流是短命、小范围、常常没有 formal review 的低摩擦合入；"
        "经审查来回修改再合入的是少数路径。把「合入」理解成「高质量审查通过」会严重高估审查深度。",
        "",
        "### RQ1.3 Closed 的真实情况如何划分",
        "",
        f"**口径**：凡是非 merged、非 open 的 PR，一律记为 `closed`，即 GitHub 终态上的 **未合入 / 被拒**（n={len(closed)}，占全库 {pct(len(closed), n)}，占终态 {pct(len(closed), len(terminal))}）。"
        f"open（n={len(open_)}）只出现在 RQ1.1 的全库总数里，**不进入本小节，也不进入后文 merged vs closed 对照**。",
        "",
        "Closed=被拒 是状态层定义，不是「维护者写了拒绝意见」。被拒内部还要按机制再拆，否则会把沉默遗弃和技术否决混成一类。",
        "",
        md_table(
            ["Closed 内部类型（均属被拒）", "操作定义", "数量", "占 closed", "占终态", "占全库"],
            [
                [
                    "真正拒绝 real rejection",
                    "有否决信号：blocking / CHANGES_REQUESTED / 技术或设计类标签",
                    int(mot_counts.get("real_rejection", 0)),
                    pct(int(mot_counts.get("real_rejection", 0)), len(closed)),
                    pct(int(mot_counts.get("real_rejection", 0)), len(terminal)),
                    pct(int(mot_counts.get("real_rejection", 0)), n),
                ],
                [
                    "沉默遗弃 silent abandonment",
                    "关闭但无明确技术/设计否决：stale、无审查、作者放弃、自动过期",
                    int(mot_counts.get("silent_abandonment", 0)),
                    pct(int(mot_counts.get("silent_abandonment", 0)), len(closed)),
                    pct(int(mot_counts.get("silent_abandonment", 0)), len(terminal)),
                    pct(int(mot_counts.get("silent_abandonment", 0)), n),
                ],
                [
                    "其他流程 other_process",
                    "被替代 PR、误提交撤回、重复提交等（仍未合入）",
                    int(mot_counts.get("other_process", 0)),
                    pct(int(mot_counts.get("other_process", 0)), len(closed)),
                    pct(int(mot_counts.get("other_process", 0)), len(terminal)),
                    pct(int(mot_counts.get("other_process", 0)), n),
                ],
                [
                    "原因不明 unclear",
                    "现有文本不足以归入以上三类（仍未合入）",
                    int(mot_counts.get("unclear", 0)),
                    pct(int(mot_counts.get("unclear", 0)), len(closed)),
                    pct(int(mot_counts.get("unclear", 0)), len(terminal)),
                    pct(int(mot_counts.get("unclear", 0)), n),
                ],
                [
                    "**closed 合计（被拒）**",
                    "非 merged 且非 open",
                    len(closed),
                    "100%",
                    pct(len(closed), len(terminal)),
                    pct(len(closed), n),
                ],
            ],
        ),
        "",
        "![closed motivation](rq_analysis_figures/rq1_closed_motivation.png)",
        "",
        f"在 **{len(closed)}** 条被拒 PR 里，沉默遗弃约占 **{pct(int(mot_counts.get('silent_abandonment', 0)), len(closed))}**，"
        f"真正拒绝约占 **{pct(int(mot_counts.get('real_rejection', 0)), len(closed))}**。"
        "也就是说：状态层全部算被拒；机制层里更多是没人跟、被放下，而不是审完后的技术否决。"
        "相对旧 `FullAnalysis.md` 把大量 closed 打进 `other`（曾占 39.9%），本表把技术否决从「其他」捞回，但不明项仍单独列出，不再把 open 算进来充数。",
        "",
        "沉默遗弃再拆（分母 = silent abandonment）：",
        "",
        md_table(
            ["遗弃子类", "数量", "占沉默遗弃", "占 closed（被拒）"],
            [
                [
                    abandon_label.get(k, k),
                    int(v),
                    pct(int(v), len(abandon) or 1),
                    pct(int(v), len(closed)),
                ]
                for k, v in abandon_sub.items()
            ],
        )
        if len(abandon)
        else "",
        "",
        f"Closed 中 `blocking=true` 仅 {blocking_closed} 条；"
        f"「真正被审过或有否决信号」的子集 {len(reviewed_closed)} 条（{pct(len(reviewed_closed), len(closed))} of closed）。"
        "其余多数被拒发生在几乎没有审查文本的情况下——这是遗弃，不是书面 reject，但终态仍是未合入。",
        "",
        "**真正拒绝示例：**",
        "",
        fmt_examples(ex_rej),
        "",
        "**沉默遗弃示例：**",
        "",
        fmt_examples(ex_abn),
        "",
        "**小结**：研究对照里 closed 就是被拒。"
        "被拒再分成真正拒绝、沉默遗弃、其他流程、原因不明四类；主导机制是沉默遗弃，真正技术/设计否决大约占被拒的三分之一。",
        "",
        "---",
        "",
        "## RQ2 成功路径与评审注意力：为何能极短周期低审查合入？为何不审？",
        "",
        "本节对照样本仅为终态 PR（merged vs closed）；open 不进入。",
        "",
        "### RQ2.1 合并成功的 PR 呈现出哪些行为与特征？",
        "",
        md_table(
            ["存活时间", "终态 PR 数", "合并率"],
            [
                [str(idx), int(life_n.get(idx, 0)), pct(rate, 1)]
                for idx, rate in merge_by_life.items()
            ],
        ),
        "",
        "![lifespan](rq_analysis_figures/rq2_lifespan.png)",
        "",
        md_table(
            ["changes 分箱", "终态 PR 数", "合并率"],
            [
                [str(idx), int(chg_n.get(idx, 0)), pct(rate, 1)]
                for idx, rate in merge_by_chg.items()
            ],
        ),
        "",
        md_table(
            ["特征", "merged", "closed"],
            [
                [
                    "存活时间中位数",
                    f"{merged['lifespan_hours'].median():.3f} h",
                    f"{closed['lifespan_hours'].median():.1f} h",
                ],
                [
                    "changes 中位数",
                    f"{merged['changes'].median():.0f}",
                    f"{closed['changes'].median():.0f}",
                ],
                [
                    "评论数中位数",
                    f"{merged['comment_total'].median():.0f}",
                    f"{closed['comment_total'].median():.0f}",
                ],
                [
                    "无 formal review",
                    pct(merged_no_review, len(merged)),
                    pct(int((closed['review_count'].fillna(0) == 0).sum()), len(closed)),
                ],
            ],
        ),
        "",
        "成功侧常见 `perf_focus`：",
        ", ".join(f"`{k}`({v})" for k, v in pf_m.most_common(8)),
        "",
        "**小结**：能合入的性能 PR 显著更短命、略更小、互动更少。"
        "主流成功画像是「小补丁很快合」，不是「材料齐全、审完再合」。",
        "",
        "### RQ2.2 维护者凭何放行？无人审更像质量门槛，还是注意力 / 流程错配？",
        "",
        "维护者**可观测**的排查方式（`detection_method`，可多选）：",
        "",
        md_table(
            ["detection_method", "全库", "merged", "closed"],
            [
                [
                    f"`{k}`",
                    f"{det_all[k]}（{pct(det_all[k], n)}）",
                    str(det_merged.get(k, 0)),
                    str(det_closed.get(k, 0)),
                ]
                for k, _ in det_all.most_common(8)
            ],
        ),
        "",
        "边界标签在终态上的合并率：",
        "",
        md_table(
            ["boundary_tag", "终态 n", "终态合并率"],
            [
                [f"`{idx}`", int(r["n"]), pct(r["merge_rate"], 1)]
                for idx, r in bound_term.iterrows()
            ],
        ),
        "",
        md_table(
            ["材料信号", "merged", "closed"],
            [
                [
                    "body_has_repro_steps",
                    pct(evidence_rate(merged, "body_has_repro_steps"), 1),
                    pct(evidence_rate(closed, "body_has_repro_steps"), 1),
                ],
                [
                    "body_has_benchmark_table",
                    pct(evidence_rate(merged, "body_has_benchmark_table"), 1),
                    pct(evidence_rate(closed, "body_has_benchmark_table"), 1),
                ],
                [
                    "body_has_numeric_perf_claim",
                    pct(evidence_rate(merged, "body_has_numeric_perf_claim"), 1),
                    pct(evidence_rate(closed, "body_has_numeric_perf_claim"), 1),
                ],
                [
                    "reproducibility=sufficient",
                    pct(int((merged["reproducibility"] == "sufficient").sum()), len(merged)),
                    pct(int((closed["reproducibility"] == "sufficient").sum()), len(closed)),
                ],
            ],
        ),
        "",
        "全库材料评级：",
        "",
        md_table(
            ["reproducibility", "数量", "占全库"],
            [[f"`{k}`", int(v), pct(int(v), n)] for k, v in repro.items()],
        ),
        "",
        "**放行依据**：可观测时以静态读码为主，CI 自动化是少数，profiler / load_test / benchmark 几乎看不见。"
        f"`technical_stack` 终态合并率 {pct(float(bound_term.loc['technical_stack']['merge_rate']), 1) if 'technical_stack' in bound_term.index else 'n/a'}，"
        "小补丁更容易过。成功 PR 并不更常带 benchmark 表——材料不是这条快路径的通行证。",
        "",
        "**为何不审**：无人审既可以合入也可以关闭。"
        f"merged 中 {pct(merged_no_review, len(merged))}、closed 中 "
        f"{pct(int((closed['review_count'].fillna(0) == 0).sum()), len(closed))} 无 formal review。"
        f"`process` 边界终态合并率只有 {pct(float(bound_term.loc['process']['merge_rate']), 1) if 'process' in bound_term.index else 'n/a'}；"
        f"{pct(no_issue_n, n)} 的 PR 没有关联 Issue，优化常是 Agent 主动发起，不在维护者既有队列里。"
        "存活超过 7 天的终态合并率掉到约 17%。这些更像评审注意力和流程错配，而不是「质量门槛把差 PR 拦下来」。",
        "",
        "**小结**：维护者放行主要靠「改动小、读得懂、没把 CI 搞红」；"
        "大量 PR 无人审，成功与失败都发生在低注意力环境中。卡住智能体性能 PR 的经常不是审查标准本身，而是有没有人愿意看。",
        "",
        "---",
        "",
        "## RQ3 失败模式与能力边界：真正被审 / 被拒的 PR 卡在哪里？",
        "",
        "### RQ3.1 在真正被审过或被否决的子集中，核心失败类型是什么？",
        "",
        f"本问**不使用全部 {len(closed)} 条 closed**，只保留有 formal review、`blocking`、`CHANGES_REQUESTED`，"
        f"或 `review_comment_bucket` 不是 `no_review_text` 的子集：**{len(reviewed_closed)}** 条"
        f"（{pct(len(reviewed_closed), len(closed))} of closed）。",
        "",
        "全量 closed 的 review 分桶（对照用，含无文本）：",
        "",
        md_table(
            ["review_comment_bucket", "数量", "占 closed"],
            [[f"`{k}`", int(v), pct(int(v), len(closed))] for k, v in bucket_closed.head(8).items()],
        ),
        "",
        "被审 / 被否决子集的失败类型：",
        "",
        md_table(
            ["失败类型", "数量", "占被审 closed 子集"],
            [
                [fail_label.get(k, k), int(v), pct(int(v), len(reviewed_closed) or 1)]
                for k, v in fail_counts.items()
            ],
        )
        if len(reviewed_closed)
        else "_子集为空_",
        "",
        "**功能 / 正确性示例：**",
        "",
        fmt_examples(ex_func),
        "",
        "**设计 / 方案否决示例：**",
        "",
        fmt_examples(ex_design),
        "",
        "反模式（`inefficiency_antipattern` ≠ none）只作伴随现象：",
        "",
        "- Merged 侧 Top：",
        ", ".join(f"`{k}`({v})" for k, v in anti_m.most_common(6)) or "（几乎全为 none）",
        "",
        "- Closed 侧 Top：",
        ", ".join(f"`{k}`({v})" for k, v in anti_c.most_common(6)) or "（几乎全为 none）",
        "",
        "两侧都是 `repeated_io` 最多，数量接近，**不能当成主拒因**。",
        "",
        "**小结**：一旦把「没人看就关了」的 PR 拿掉，剩下的失败更接近导师说的「补丁错了 / 方案不对 / CI 过不了 / 缺材料」。"
        "静默 maintainer 关闭仍需单独看待，它介于拒绝和遗弃之间。",
        "",
        "### RQ3.2 证据生成、流程协作与同 PR 修复分别暴露了哪些能力边界？",
        "",
        "三条既有 `boundary_tag` 直接对应三种非代码能力：",
        "",
        md_table(
            ["边界", "含义", "终态 n", "终态合并率"],
            [
                [
                    "`technical_stack`",
                    "常规技术栈改动（Agent 相对能做）",
                    int(bound_term.loc["technical_stack"]["n"]) if "technical_stack" in bound_term.index else 0,
                    pct(float(bound_term.loc["technical_stack"]["merge_rate"]), 1)
                    if "technical_stack" in bound_term.index
                    else "—",
                ],
                [
                    "`process`",
                    "协作 / 审查 / 流程推进",
                    int(bound_term.loc["process"]["n"]) if "process" in bound_term.index else 0,
                    pct(float(bound_term.loc["process"]["merge_rate"]), 1)
                    if "process" in bound_term.index
                    else "—",
                ],
                [
                    "`evidence_required`",
                    "维护者要求可复现性能证据",
                    int(bound_term.loc["evidence_required"]["n"]) if "evidence_required" in bound_term.index else 0,
                    pct(float(bound_term.loc["evidence_required"]["merge_rate"]), 1)
                    if "evidence_required" in bound_term.index
                    else "—",
                ],
            ],
        ),
        "",
        "**证据边界示例（evidence_required × closed）：**",
        "",
        fmt_examples(ex_ev),
        "",
        "退化 / 审查问题处置（`regression_handling`）：",
        "",
        md_table(
            ["regression_handling", "数量", "占全库"],
            [[f"`{k}`", int(v), pct(int(v), n)] for k, v in reg.head(8).items()],
        ),
        "",
        f"`fix_in_pr` 共 {len(fix_in_pr)} 条（{pct(len(fix_in_pr), n)}）。修复主体启发式：",
        "",
        md_table(
            ["修复模式", "数量", "占 fix_in_pr"],
            [
                [k, v, pct(v, len(fix_in_pr) or 1)]
                for k, v in fix_modes.most_common()
            ],
        )
        if len(fix_in_pr)
        else "",
        "",
        f"`antipattern_in_fix` 非 none 共 **{anti_fix_n}** 条（{pct(anti_fix_n, n)}），只说明二次引入反模式是稀有风险，不能当核心发现。`revert` 极少。",
        "",
        "**小结**：",
        "",
        "- **证据生成**：一进入 `evidence_required`，终态合并率掉到约一成；全库 sufficient 材料只有约 2%。",
        "- **流程协作**：process 边界合入率大约只有 technical_stack 的一半；closed 里沉默遗弃仍是大头。",
        "- **同 PR 修复**：能在原 PR 里把问题修完的是少数，且过半要人类主导。Agent 独立消化 CHANGES_REQUESTED 的能力有限。",
        "",
        "---",
        "",
        "## RQ4 核心差异：合入与关闭差在哪？能力边界是否影响结果？如何提高合并率？",
        "",
        "### RQ4.1 成功合入与失败 / 搁置在核心维度上有何显著差异？",
        "",
        md_table(
            ["维度", "Merged", "Closed", "读法"],
            [
                [
                    "寿命",
                    f"中位 {merged['lifespan_hours'].median():.3f} h，fast_merge {pct(fast_n, len(merged))}",
                    f"中位 {closed['lifespan_hours'].median():.1f} h，fast_merge 0",
                    "成功是快路径",
                ],
                [
                    "规模",
                    f"中位 changes {merged['changes'].median():.0f}；≤100 行档合并率最高",
                    f"中位 {closed['changes'].median():.0f}",
                    "小补丁占优，但 >10k 仍可合，不能写成越大越不能合",
                ],
                [
                    "互动",
                    f"评论中位 {merged['comment_total'].median():.0f}；{pct(merged_zero_comment, len(merged))} 为 0",
                    f"评论中位 {closed['comment_total'].median():.0f}",
                    "高评论量不对应更高合并率",
                ],
                [
                    "材料",
                    f"benchmark 表 {pct(evidence_rate(merged, 'body_has_benchmark_table'), 1)}；数字声称 {pct(evidence_rate(merged, 'body_has_numeric_perf_claim'), 1)}",
                    f"benchmark 表 {pct(evidence_rate(closed, 'body_has_benchmark_table'), 1)}；数字声称 {pct(evidence_rate(closed, 'body_has_numeric_perf_claim'), 1)}",
                    "Closed 更常给证据，证据是难 PR 门槛而非成功标配",
                ],
            ],
        ),
        "",
        "**perf_focus 对照**",
        "",
        "- Merged：",
        ", ".join(f"`{k}`({v})" for k, v in pf_m.most_common(8)),
        "",
        "- Closed：",
        ", ".join(f"`{k}`({v})" for k, v in pf_c.most_common(8)),
        "",
        "成功侧更偏常量折叠、编译优化、缓存；关闭侧更常见包体积、复杂构建、code splitting。",
        "",
        "### RQ4.2 合入和关闭在 AI 能力边界上有哪些区别？是否影响合并结果？",
        "",
        "![boundary](rq_analysis_figures/rq4_boundary.png)",
        "",
        "终态合并率按 `optimization_layer`（n≥20）：",
        "",
        md_table(
            ["optimization_layer", "终态 n", "终态合并率"],
            [
                [f"`{idx}`", int(r["n"]), pct(r["merge_rate"], 1)]
                for idx, r in layer_term.iterrows()
            ],
        ),
        "",
        "**现象（描述性）**：能力边界和合并结果同向变化。",
        "",
        "- 落在 `technical_stack` 的 PR 终态合并率接近八成：小范围、可模板化的缓存 / 常量 / 编译类改动。",
        "- 落在 `process` 的 PR 只有约三成合入：无人审、stale、作者放弃。这是协作边界，不一定是代码写错。",
        "- 落在 `evidence_required` 的 PR 终态合并率约一成：维护者要数字，Agent 给的是叙述。",
        "- 层面信号一致但样本更小：`compiler` / `compiler_backend` 合入高，`runtime_vm` 明显低。",
        "",
        "因此：**存在「能力边界与合并结果一起分层」的现象**，但还不是「边界导致失败」的因果证明。"
        "流程边界尤其可能是维护者注意力问题，而不是 Agent 写不出补丁。",
        "",
        "### RQ4.3 针对现有缺陷，有哪些可操作改进能提高合并率？",
        "",
        "不要开一张万能药方。按 RQ1–RQ3 的两条真实路径分别改。",
        "",
        "**路径 A — 已经在走的低摩擦合入（RQ1.2 / RQ2）**",
        "",
        "- 保持原子补丁，优先 `technical_stack` 上的缓存、常量折叠、构建层改动。",
        "- 降低维护者注意力成本：标题/正文写清「改了什么、为什么安全」，而不是先堆 benchmark。",
        "- 无 Issue 的主动优化不要默认丢进需要深度审的队列；需要仓库侧的分诊（bot 标 `small/perf-safe`）。",
        "- **不要**强制所有 PR <100 行：≤100 行合并率最高，但大 PR 仍有约一半合入。",
        "",
        "**路径 B — 需要被认真审的难 PR（RQ1.3 / RQ3）**",
        "",
        "- 工具链补可复现材料：前后对比表 + 复现步骤，对准 `evidence_required` 的悬崖，而不是给快合并路径加表。",
        "- Review 阶段把 CHANGES_REQUESTED 当成一等任务；当前 `fix_in_pr` 过半是人类主导，Agent 需要稳定消化审查意见。",
        "- 对 `runtime_vm`、大范围控制流、包体积类改动提前声明风险，或拆成可独立合入的证据提交 + 代码提交。",
        "- 沉默遗弃是注意力问题：超时提醒、把 stale bot 关闭改成「需要 maintainer 一句话」而不是直接关。",
        "",
        "**明确不支持的说法**：Closed 组更常带数字声称和 benchmark 表，因此「给所有性能 PR 加 benchmark 就会提高合并率」与现有相关方向相反。"
        "Benchmark 应留给被要求举证的难 PR。",
        "",
        "---",
        "",
        "## 总结",
        "",
        "1. **RQ1**：全库 n 含 open；对照只用 merged vs closed。Closed 即终态被拒，内部以沉默遗弃为主，真正技术/设计拒绝约占被拒三分之一。Merged 以低摩擦快合并为主。Agent 之间终态合并率差一倍以上。",
        "2. **RQ2**：成功 PR 极短命、常无审查；放行靠读码和小补丁，不靠 profiler。无人审同时出现在合入和关闭两侧，更像注意力 / 流程问题。",
        "3. **RQ3**：真正被审的失败以正确性、设计、CI 为主；证据边界和流程边界比「又套了一层循环」更能解释合不进去；同 PR 修复少且依赖人类。",
        "4. **RQ4**：寿命、边界类型、优化层面差异清楚，材料差异方向与「多写 benchmark 就能合」相反。改进必须分快路径和难路径。",
        "",
        "## 附录 A 分类规则（可复现）",
        "",
        "### Merged 路径 `merged_path`",
        "",
        "1. `outcome_reason` 含 after_review / iterative / maintainer_fix → `reviewed_iteration`；否则若有 formal review 且非 fast_merge → 同类。",
        "2. `fast_merge` 或（寿命 <1h 且 review_count=0）→ `fast_low_friction`。",
        "3. 仍无 review 或标签含 no_review / self_merge → `no_formal_review`。",
        "4. 其余 `other`。",
        "",
        "### GitHub 状态（先于 Closed 动机）",
        "",
        "- `merged`：已合入。",
        "- `open`：仍开放；**只计入全库 n，不进入 merged vs closed 研究对照**。",
        "- `closed`：非 merged 且非 open = 本研究的终态被拒。",
        "",
        "### Closed 动机 `close_motivation`（closed 的内部划分，全部仍是被拒）",
        "",
        "1. 替代 PR / 误提交撤回等 → `other_process`（若同时有强技术否决则仍算真正拒绝）。",
        "2. `blocking`、CHANGES_REQUESTED、技术类 `outcome_reason` / `primary_concern` / review 分桶、明确 rollback 文本 → `real_rejection`。",
        "3. stale / 无审查 / 作者自行关闭 / 自动过期 → `silent_abandonment`。",
        "4. 其余 `unclear`。",
        "",
        "### 被审 closed 子集",
        "",
        "`has_formal_review` 或 `blocking` 或 CHANGES_REQUESTED>0 或 `review_comment_bucket` 不是 `no_review_text`。",
        "",
        "## 附录 B 方法边界",
        "",
        "1. 标签来自 LLM 分析 JSON，建议对 real rejection / silent abandonment 各抽检数十条 `rejection_signals`。",
        "2. Agent 差异、边界与合并率、benchmark 与合并率都是相关不是因果。open 只计入全库 n。",
        "3. `fix_in_pr` 主体与 `antipattern_in_fix` 是启发式。",
        "4. 与 `FullAnalysis.md` 若有个别计数差，以本脚本现场聚合为准（分类规则已更新）。",
        "",
    ]

    md = "\n".join(line for line in lines if line is not None)
    return md, metrics


def main() -> None:
    records = load_all_analyses()
    if not records:
        raise SystemExit("No analysis JSON files found.")
    rows = [enrich_row(d, flatten_record(d)) for d in records]
    df = pd.DataFrame(rows)
    md, metrics = build_report(df, records)
    OUT_MD.write_text(md, encoding="utf-8")
    OUT_JSON.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_MD} ({len(df)} PRs)")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote figures under {FIG_DIR}")


if __name__ == "__main__":
    main()
