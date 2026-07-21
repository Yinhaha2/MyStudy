#!/usr/bin/env python3
"""Estimate DeepSeek workflow context usage and tier PRs for routing.

Each workflow call is modeled as::

    prompt + target_pr_payload + 6 * fewshot_pr_payload (+ output reserve)

Few-shot PRs are the fixed A+C set from candidate.md. Token estimates use a
configurable chars-per-token ratio (default 3.5, conservative for code-heavy text).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent
FINALDB = ROOT / "finaldatabase"
MASTER_CSV = FINALDB / "pr_master" / "perf_prs_expanded_final.csv"
AUX = FINALDB / "auxiliary"

# A+C few-shot set (fixed workflow overhead)
FEWSHOT_PR_IDS = [
    3228424652,
    3074351366,
    3194284966,
    3145702280,
    3125029980,
    3022909076,
]

MODEL_PROFILES: dict[str, dict[str, int]] = {
    # DeepSeek V4 API (current default for new integrations)
    "deepseek-v4-flash": {
        "context_tokens": 1_000_000,
        "output_reserve_tokens": 16_000,
        "notes": "Non-thinking / thinking modes; 1M context per API docs (2026-07).",
    },
    "deepseek-v4-pro": {
        "context_tokens": 1_000_000,
        "output_reserve_tokens": 32_000,
        "notes": "Higher capability tier; same 1M context.",
    },
    # Legacy aliases (deprecated 2026-07-24) — kept for conservative planning
    "deepseek-chat-64k": {
        "context_tokens": 64_000,
        "output_reserve_tokens": 8_000,
        "notes": "Legacy deepseek-chat default window before byte-level extension.",
    },
    "deepseek-chat-128k": {
        "context_tokens": 128_000,
        "output_reserve_tokens": 12_000,
        "notes": "Legacy deepseek-chat with extended context.",
    },
}

PAYLOAD_MODES = ("standard_no_patch", "with_patch", "compact")

# Tier thresholds as fractions of usable input budget
TIER_AUTO_MAX = 0.70
TIER_RISKY_MAX = 0.90
TIER_OVERFLOW_MAX = 1.00

# Hard manual routing regardless of token estimate
MANUAL_CHANGES_THRESHOLD = 100_000
MANUAL_PATCH_CHARS_THRESHOLD = 2_000_000


@dataclass
class PrCharBreakdown:
    pr_id: int
    master_chars: int
    review_chars: int
    comment_chars: int
    review_comment_chars: int
    commit_msg_chars: int
    file_meta_chars: int
    timeline_chars: int
    patch_chars: int
    commit_count: int
    file_detail_rows: int
    review_count: int
    comment_count: int
    review_comment_count: int
    total_changes: int

    @property
    def text_without_patch(self) -> int:
        return (
            self.master_chars
            + self.review_chars
            + self.comment_chars
            + self.review_comment_chars
            + self.commit_msg_chars
            + self.file_meta_chars
            + self.timeline_chars
        )

    @property
    def text_with_patch(self) -> int:
        return self.text_without_patch + self.patch_chars


def _text_len(series: pd.Series) -> int:
    return int(series.fillna("").astype(str).str.len().sum())


def _truncate_text(text: str, limit: int) -> int:
    if len(text) <= limit:
        return len(text)
    return limit + len("\n...[truncated]...")


def load_char_breakdowns() -> dict[int, PrCharBreakdown]:
    master = pd.read_csv(MASTER_CSV)
    reviews = pd.read_parquet(AUX / "pr_reviews.parquet")
    comments = pd.read_parquet(AUX / "pr_comments.parquet")
    review_comments = pd.read_parquet(AUX / "pr_review_comments_v2.parquet")
    commits = pd.read_parquet(AUX / "pr_commits.parquet")
    commit_details = pd.read_parquet(AUX / "pr_commit_details.parquet")
    timeline = pd.read_parquet(AUX / "pr_timeline.parquet")

    review_comments = review_comments.merge(
        reviews[["id", "pr_id"]],
        left_on="pull_request_review_id",
        right_on="id",
        how="left",
    )

    master_chars = master.set_index("id").apply(
        lambda r: len(str(r.get("title") or ""))
        + len(str(r.get("body") or ""))
        + len(str(r.get("agent") or ""))
        + len(str(r.get("status") or ""))
        + len(str(r.get("Topic") or ""))
        + 120,
        axis=1,
    )

    review_chars = reviews.groupby("pr_id")["body"].apply(_text_len)
    comment_chars = comments.groupby("pr_id")["body"].apply(_text_len)

    def review_comment_group(g: pd.DataFrame) -> int:
        body = _text_len(g["body"]) if "body" in g else 0
        diff = _text_len(g["diff_hunk"]) if "diff_hunk" in g else 0
        path = _text_len(g["path"]) if "path" in g else 0
        return body + diff + path

    rc_chars = review_comments.groupby("pr_id").apply(review_comment_group, include_groups=False)
    commit_msg_chars = commits.groupby("pr_id")["message"].apply(_text_len)

    file_meta_cols = [c for c in ["filename", "status", "message"] if c in commit_details.columns]
    file_meta_chars = commit_details.groupby("pr_id")[file_meta_cols].apply(
        lambda g: g.fillna("").astype(str).apply(lambda col: col.str.len()).sum().sum(),
        include_groups=False,
    )
    patch_chars = commit_details.groupby("pr_id")["patch"].apply(_text_len)

    timeline_cols = [c for c in ["event", "actor", "message", "label"] if c in timeline.columns]
    timeline_chars = timeline.groupby("pr_id")[timeline_cols].apply(
        lambda g: g.fillna("").astype(str).apply(lambda col: col.str.len()).sum().sum(),
        include_groups=False,
    )

    commit_counts = commits.groupby("pr_id").size()
    file_rows = commit_details.groupby("pr_id").size()
    review_counts = reviews.groupby("pr_id").size()
    comment_counts = comments.groupby("pr_id").size()
    rc_counts = review_comments.groupby("pr_id").size()

    changes_by_pr = (
        commit_details.groupby("pr_id")["changes"].sum()
        if "changes" in commit_details.columns
        else commit_details.groupby("pr_id")["commit_stats_total"].sum()
    )

    breakdowns: dict[int, PrCharBreakdown] = {}
    for pr_id in master["id"].astype(int):
        breakdowns[pr_id] = PrCharBreakdown(
            pr_id=pr_id,
            master_chars=int(master_chars.get(pr_id, 0)),
            review_chars=int(review_chars.get(pr_id, 0)),
            comment_chars=int(comment_chars.get(pr_id, 0)),
            review_comment_chars=int(rc_chars.get(pr_id, 0)),
            commit_msg_chars=int(commit_msg_chars.get(pr_id, 0)),
            file_meta_chars=int(file_meta_chars.get(pr_id, 0)),
            timeline_chars=int(timeline_chars.get(pr_id, 0)),
            patch_chars=int(patch_chars.get(pr_id, 0)),
            commit_count=int(commit_counts.get(pr_id, 0)),
            file_detail_rows=int(file_rows.get(pr_id, 0)),
            review_count=int(review_counts.get(pr_id, 0)),
            comment_count=int(comment_counts.get(pr_id, 0)),
            review_comment_count=int(rc_counts.get(pr_id, 0)),
            total_changes=int(changes_by_pr.get(pr_id, 0)),
        )
    return breakdowns


def estimate_pr_chars(b: PrCharBreakdown, payload_mode: str) -> int:
    if payload_mode == "with_patch":
        return b.text_with_patch

    if payload_mode == "standard_no_patch":
        return b.text_without_patch

    if payload_mode == "compact":
        # Conservative caps mirroring a trimmed workflow upload
        review_cap = min(b.review_chars, b.review_count * 4_000)
        comment_cap = min(b.comment_chars, b.comment_count * 4_000)
        rc_cap = min(b.review_comment_chars, b.review_comment_count * 2_000)
        commit_cap = min(b.commit_msg_chars, b.commit_count * 1_500)
        file_cap = min(b.file_meta_chars, min(b.file_detail_rows, 50) * 120)
        timeline_cap = min(b.timeline_chars, 3_000)
        return (
            b.master_chars
            + review_cap
            + comment_cap
            + rc_cap
            + commit_cap
            + file_cap
            + timeline_cap
        )

    raise ValueError(f"Unknown payload_mode: {payload_mode}")


def load_fixed_overhead_chars(
    breakdowns: dict[int, PrCharBreakdown],
    payload_mode: str,
    prompt_extra_chars: int = 2_500,
) -> dict[str, int]:
    guide_chars = len((ROOT / "RQ_fewshot_guide.md").read_text(encoding="utf-8"))
    schema_path = ROOT / "schema.json"
    schema_chars = len(schema_path.read_text(encoding="utf-8")) if schema_path.exists() else 6_000

    analysis_chars = 0
    for pr_id in FEWSHOT_PR_IDS:
        path = ROOT / f"{pr_id}_analysis.json"
        if path.exists():
            analysis_chars += path.stat().st_size

    fewshot_pr_chars = sum(
        estimate_pr_chars(breakdowns[pr_id], payload_mode) for pr_id in FEWSHOT_PR_IDS
    )

    return {
        "prompt_template_chars": prompt_extra_chars,
        "guide_chars": guide_chars,
        "schema_chars": schema_chars,
        "fewshot_pr_chars": fewshot_pr_chars,
        "fewshot_analysis_chars": analysis_chars,
        "total_fixed_chars": prompt_extra_chars
        + guide_chars
        + schema_chars
        + fewshot_pr_chars
        + analysis_chars,
    }


def chars_to_tokens(chars: int, chars_per_token: float) -> int:
    return int(chars / chars_per_token + 0.999)  # ceil


def classify_tier(
    total_input_tokens: int,
    usable_budget: int,
    b: PrCharBreakdown,
) -> str:
    if (
        b.total_changes >= MANUAL_CHANGES_THRESHOLD
        or b.patch_chars >= MANUAL_PATCH_CHARS_THRESHOLD
    ):
        return "manual_xlarge"

    ratio = total_input_tokens / usable_budget if usable_budget > 0 else float("inf")

    if ratio <= TIER_AUTO_MAX:
        return "workflow_auto"
    if ratio <= TIER_RISKY_MAX:
        return "workflow_risky"
    if ratio <= TIER_OVERFLOW_MAX:
        return "workflow_overflow"
    return "manual_xlarge"


def build_report(
    model: str,
    payload_mode: str,
    chars_per_token: float,
    breakdowns: dict[int, PrCharBreakdown],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    profile = MODEL_PROFILES[model]
    context_tokens = profile["context_tokens"]
    output_reserve = profile["output_reserve_tokens"]
    usable_budget = context_tokens - output_reserve

    fixed = load_fixed_overhead_chars(breakdowns, payload_mode)
    fixed_tokens = chars_to_tokens(fixed["total_fixed_chars"], chars_per_token)

    master = pd.read_csv(MASTER_CSV, usecols=["id", "title", "status", "agent", "html_url"])

    rows: list[dict[str, Any]] = []
    for pr_id, b in breakdowns.items():
        target_chars = estimate_pr_chars(b, payload_mode)
        total_chars = fixed["total_fixed_chars"] + target_chars
        total_input_tokens = chars_to_tokens(total_chars, chars_per_token)
        target_tokens = chars_to_tokens(target_chars, chars_per_token)
        budget_ratio = round(total_input_tokens / usable_budget, 4)

        tier = classify_tier(total_input_tokens, usable_budget, b)
        fits_one_call = total_input_tokens <= usable_budget

        rows.append(
            {
                "pr_id": pr_id,
                "tier": tier,
                "fits_one_call": fits_one_call,
                "total_input_tokens_est": total_input_tokens,
                "target_pr_tokens_est": target_tokens,
                "fixed_overhead_tokens_est": fixed_tokens,
                "budget_ratio": budget_ratio,
                "usable_input_budget_tokens": usable_budget,
                "target_pr_chars_est": target_chars,
                "patch_chars": b.patch_chars,
                "total_changes": b.total_changes,
                "commit_count": b.commit_count,
                "file_detail_rows": b.file_detail_rows,
                "review_count": b.review_count,
                "comment_count": b.comment_count,
                "review_comment_count": b.review_comment_count,
            }
        )

    df = pd.DataFrame(rows).merge(master, left_on="pr_id", right_on="id", how="left")
    df.drop(columns=["id"], inplace=True, errors="ignore")

    tier_counts = df["tier"].value_counts().to_dict()
    overflow = df[~df["fits_one_call"]]

    summary: dict[str, Any] = {
        "model_profile": model,
        "model_notes": profile["notes"],
        "payload_mode": payload_mode,
        "chars_per_token": chars_per_token,
        "context_tokens": context_tokens,
        "output_reserve_tokens": output_reserve,
        "usable_input_budget_tokens": usable_budget,
        "fewshot_pr_ids": FEWSHOT_PR_IDS,
        "fixed_overhead": fixed,
        "fixed_overhead_tokens_est": fixed_tokens,
        "total_prs": len(df),
        "tier_counts": tier_counts,
        "fits_one_call_count": int(df["fits_one_call"].sum()),
        "fits_one_call_pct": round(100 * df["fits_one_call"].mean(), 2),
        "cannot_fit_one_call_count": int((~df["fits_one_call"]).sum()),
        "cannot_fit_one_call_pct": round(100 * (~df["fits_one_call"]).mean(), 2),
        "token_stats": {
            "target_pr_tokens_median": int(df["target_pr_tokens_est"].median()),
            "target_pr_tokens_p95": int(df["target_pr_tokens_est"].quantile(0.95)),
            "total_input_tokens_median": int(df["total_input_tokens_est"].median()),
            "total_input_tokens_p95": int(df["total_input_tokens_est"].quantile(0.95)),
            "total_input_tokens_max": int(df["total_input_tokens_est"].max()),
        },
        "top_overflow_prs": overflow.nlargest(15, "total_input_tokens_est")[
            ["pr_id", "title", "status", "agent", "total_input_tokens_est", "tier", "total_changes"]
        ].to_dict(orient="records"),
        "tier_thresholds": {
            "workflow_auto": f"<= {TIER_AUTO_MAX:.0%} of usable budget",
            "workflow_risky": f"{TIER_AUTO_MAX:.0%}–{TIER_RISKY_MAX:.0%}",
            "workflow_overflow": f"{TIER_RISKY_MAX:.0%}–{TIER_OVERFLOW_MAX:.0%}",
            "manual_xlarge": f"> {TIER_OVERFLOW_MAX:.0%} or hard size rules",
        },
    }
    return df, summary


def write_markdown_summary(summary: dict[str, Any], out_path: Path) -> None:
    tc = summary["tier_counts"]
    lines = [
        "# Workflow 体量扫描结果",
        "",
        f"- **模型**: `{summary['model_profile']}` ({summary['model_notes']})",
        f"- **载荷模式**: `{summary['payload_mode']}`",
        f"- **字符→Token 换算**: {summary['chars_per_token']} chars/token",
        f"- **可用输入预算**: {summary['usable_input_budget_tokens']:,} tokens "
        f"(总上下文 {summary['context_tokens']:,} − 输出预留 {summary['output_reserve_tokens']:,})",
        f"- **固定开销（prompt + 6 few-shot PR + 分析样例）**: "
        f"~{summary['fixed_overhead_tokens_est']:,} tokens",
        "",
        "## 一次 Workflow 能否装下",
        "",
        f"| 结果 | 数量 | 占比 |",
        f"|------|------|------|",
        f"| 可一次分析 | {summary['fits_one_call_count']} | {summary['fits_one_call_pct']}% |",
        f"| 大概率装不下 | {summary['cannot_fit_one_call_count']} | {summary['cannot_fit_one_call_pct']}% |",
        "",
        "## 路由分层",
        "",
        "| 层级 | 数量 | 建议处置 |",
        "|------|------|----------|",
        f"| workflow_auto | {tc.get('workflow_auto', 0)} | 自动 workflow，优先批量 |",
        f"| workflow_risky | {tc.get('workflow_risky', 0)} | 可自动但需监控截断/超时 |",
        f"| workflow_overflow | {tc.get('workflow_overflow', 0)} | 启用 compact 模式或拆分 |",
        f"| manual_xlarge | {tc.get('manual_xlarge', 0)} | 人工分析或专项 pipeline |",
        "",
        "## Token 分布（估计）",
        "",
        f"- 待分析 PR 中位数: {summary['token_stats']['target_pr_tokens_median']:,} tokens",
        f"- 待分析 PR P95: {summary['token_stats']['target_pr_tokens_p95']:,} tokens",
        f"- 总输入（含固定开销）中位数: {summary['token_stats']['total_input_tokens_median']:,} tokens",
        f"- 总输入 P95: {summary['token_stats']['total_input_tokens_p95']:,} tokens",
        f"- 总输入最大值: {summary['token_stats']['total_input_tokens_max']:,} tokens",
        "",
        "## 装不下的 Top PR（按总 token 降序）",
        "",
    ]

    for item in summary["top_overflow_prs"]:
        lines.append(
            f"- `{item['pr_id']}` ({item['status']}, {item['agent']}, "
            f"changes={item['total_changes']:,}): ~{item['total_input_tokens_est']:,} tokens — "
            f"{item['title'][:80]}"
        )

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan PR corpus for DeepSeek workflow context fit.")
    parser.add_argument(
        "--model",
        choices=sorted(MODEL_PROFILES),
        default="deepseek-v4-flash",
        help="DeepSeek model profile (default: deepseek-v4-flash)",
    )
    parser.add_argument(
        "--payload",
        choices=PAYLOAD_MODES,
        default="standard_no_patch",
        help="What text to include per PR (default: standard_no_patch)",
    )
    parser.add_argument(
        "--chars-per-token",
        type=float,
        default=3.5,
        help="Conservative chars/token ratio for estimation (default: 3.5)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "output_workflow_size",
        help="Output directory for CSV/JSON/MD reports",
    )
    parser.add_argument(
        "--compare-models",
        action="store_true",
        help="Also emit a cross-model comparison table (standard_no_patch only)",
    )
    args = parser.parse_args()

    breakdowns = load_char_breakdowns()
    df, summary = build_report(args.model, args.payload, args.chars_per_token, breakdowns)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    tag = f"{args.model}_{args.payload}"
    df.sort_values("total_input_tokens_est", ascending=False).to_csv(
        out_dir / f"pr_tiers_{tag}.csv", index=False
    )
    (out_dir / f"summary_{tag}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_markdown_summary(summary, out_dir / f"SUMMARY_{tag}.md")

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.compare_models:
        compare_rows = []
        for model_name in MODEL_PROFILES:
            _, sm = build_report(model_name, "standard_no_patch", args.chars_per_token, breakdowns)
            compare_rows.append(
                {
                    "model": model_name,
                    "usable_budget": sm["usable_input_budget_tokens"],
                    "fixed_overhead_tokens": sm["fixed_overhead_tokens_est"],
                    "fits_one_call_count": sm["fits_one_call_count"],
                    "fits_one_call_pct": sm["fits_one_call_pct"],
                    "manual_xlarge_count": sm["tier_counts"].get("manual_xlarge", 0),
                    "workflow_overflow_count": sm["tier_counts"].get("workflow_overflow", 0),
                }
            )
        compare_df = pd.DataFrame(compare_rows)
        compare_df.to_csv(out_dir / "model_comparison_standard_no_patch.csv", index=False)
        print("\nModel comparison (standard_no_patch):")
        print(compare_df.to_string(index=False))


if __name__ == "__main__":
    main()
