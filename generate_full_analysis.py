#!/usr/bin/env python3
"""Aggregate perf PR analysis JSON into FullAnalysis.md and a distilled CSV."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
PER_PR = ROOT / "finaldatabase" / "per_pr"
OUT_MD = ROOT / "FullAnalysis.md"
OUT_CSV = ROOT / "full_analysis_distilled.csv"

FEWSHOT_ROOT_ONLY = [
    3228424652,
    3074351366,
    3194284966,
    3145702280,
    3125029980,
    3022909076,
]


def load_all_analyses() -> list[dict]:
    records: list[dict] = []
    seen: set[int] = set()

    for pr_dir in PER_PR.iterdir():
        if not pr_dir.is_dir():
            continue
        path = pr_dir / f"{pr_dir.name}_analysis.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            records.append(data)
            seen.add(int(data["pr_id"]))

    for pr_id in FEWSHOT_ROOT_ONLY:
        if pr_id in seen:
            continue
        path = ROOT / f"{pr_id}_analysis.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            records.append(data)
            seen.add(pr_id)

    records.sort(key=lambda d: d["pr_id"])
    return records


def flatten_record(d: dict) -> dict:
    meta = d.get("meta") or {}
    pl = d.get("perf_labels") or {}
    qm = d.get("quantitative_metrics") or {}
    cs = qm.get("change_scale") or {}
    col = qm.get("collaboration") or {}
    tl = qm.get("timeline") or {}
    es = qm.get("evidence_signals") or {}
    sa = d.get("structured_analysis") or {}
    moc = sa.get("merge_outcome_context") or {}
    rd = sa.get("review_details") or {}
    cb = sa.get("capability_boundary") or {}
    mp = sa.get("maintainer_practices") or {}
    dc = d.get("data_coverage") or {}

    def join_list(val):
        if not val:
            return ""
        if isinstance(val, list):
            return "|".join(str(x) for x in val)
        return str(val)

    return {
        "pr_id": d.get("pr_id"),
        "title": meta.get("title"),
        "html_url": meta.get("html_url"),
        "repo": meta.get("repo"),
        "agent": meta.get("agent"),
        "status": meta.get("status"),
        "topic_id": meta.get("topic_id"),
        "topic_name": meta.get("topic_name"),
        "aidev_task_type": meta.get("aidev_task_type"),
        "outcome": moc.get("outcome"),
        "outcome_reason": pl.get("outcome_reason"),
        "optimization_layer": pl.get("optimization_layer"),
        "perf_focus": join_list(pl.get("perf_focus")),
        "inefficiency_antipattern": join_list(pl.get("inefficiency_antipattern")),
        "evidence_type": join_list(pl.get("evidence_type")),
        "detection_method": join_list(pl.get("detection_method")),
        "reproducibility": pl.get("reproducibility"),
        "material_reproducibility": mp.get("material_reproducibility"),
        "regression_handling": pl.get("regression_handling"),
        "boundary_tag": pl.get("boundary_tag"),
        "boundary_type": cb.get("boundary_type"),
        "topic_difficulty": pl.get("topic_difficulty"),
        "blocking": pl.get("blocking"),
        "confidence": pl.get("confidence"),
        "primary_concern": rd.get("primary_concern"),
        "review_comment_bucket": rd.get("review_comment_bucket"),
        "review_dimensions": join_list(pl.get("review_dimensions")),
        "performance_evidence_in_review": rd.get("performance_evidence_in_review"),
        "antipattern_addressed": rd.get("antipattern_addressed"),
        "antipattern_in_fix": rd.get("antipattern_in_fix"),
        "changes": cs.get("changes"),
        "file_count": cs.get("file_count"),
        "commit_count": cs.get("commit_count"),
        "additions": cs.get("additions"),
        "deletions": cs.get("deletions"),
        "review_count": col.get("review_count"),
        "review_comment_count": col.get("review_comment_count"),
        "pr_comment_count": col.get("pr_comment_count"),
        "comment_total": (col.get("review_comment_count") or 0) + (col.get("pr_comment_count") or 0),
        "linked_issue_count": col.get("linked_issue_count") or 0,
        "has_linked_issue": (col.get("linked_issue_count") or 0) > 0,
        "lifespan_hours": tl.get("lifespan_hours"),
        "fast_merge": moc.get("lifecycle", {}).get("fast_merge"),
        "has_revert": tl.get("has_revert"),
        "body_has_repro_steps": es.get("body_has_repro_steps"),
        "body_has_benchmark_table": es.get("body_has_benchmark_table"),
        "body_has_numeric_perf_claim": es.get("body_has_numeric_perf_claim"),
        "has_formal_review": dc.get("has_formal_review"),
        "has_review_or_comment_text": dc.get("has_review_or_comment_text"),
        "evidence_gap": mp.get("evidence_gap"),
        "regression_detail": mp.get("regression_detail"),
        "reproducibility_notes": mp.get("reproducibility_notes"),
        "performance_claim": rd.get("performance_claim"),
        "notes": pl.get("notes"),
    }


def pct(n: int, total: int) -> str:
    return f"{100 * n / total:.1f}%" if total else "0.0%"


def top_counter(series: pd.Series, n: int = 10) -> str:
    c = series.value_counts().head(n)
    lines = []
    for k, v in c.items():
        lines.append(f"| `{k}` | {v} | {pct(v, len(series))} |")
    return "\n".join(lines)


def classify_merge_reason(reason: str) -> str:
    r = (reason or "").lower()
    if "small_scope" in r or "low_risk" in r:
        return "small_scope_low_risk"
    if "after_review" in r or "maintainer_fix" in r or "iterative" in r:
        return "after_review_iteration"
    if "no_review" in r or "self_merge" in r or "self_approved" in r:
        return "without_formal_review"
    return "other"


def classify_close_reason(reason: str) -> str:
    r = (reason or "").lower()
    if "stale" in r or "inactiv" in r:
        return "stale_or_inactivity"
    if "no_review" in r or "self_closed" in r or "author_closed" in r:
        return "closed_without_meaningful_review"
    if "functional" in r or "correctness" in r or "bug" in r or "test_failure" in r:
        return "functional_or_correctness"
    if "benchmark" in r or "evidence" in r or "missing" in r:
        return "missing_evidence_or_benchmark"
    if "scope" in r:
        return "scope_too_large"
    if "regression" in r or "performance" in r and "fail" in r:
        return "performance_regression_or_no_gain"
    return "other"


def classify_fix_mode(detail: str, trajectory: str) -> str:
    text = f"{detail} {trajectory}".lower()
    if re.search(r"requested changes|changes_requested|review requested|maintainer requested", text):
        if re.search(r"author|agent|commit|push", text):
            return "human_ai_collaborative"
    if re.search(r"maintainer|human reviewer|reviewer", text) and re.search(
        r"fix|commit|push|address", text
    ):
        return "human_led_or_requested"
    if re.search(r"author|agent|copilot|cursor|devin|claude", text) and re.search(
        r"commit|push|fix", text
    ):
        return "ai_author_in_pr"
    return "unclear"


def build_markdown(df: pd.DataFrame, records: list[dict]) -> str:
    n = len(df)
    merged = df[df["status"] == "merged"]
    closed = df[df["status"] == "closed"]
    open_ = df[df["status"] == "open"]
    terminal = df[df["status"].isin(["merged", "closed"])]

    merged_groups = merged["merge_reason_group"].value_counts()
    closed_groups = closed["close_reason_group"].value_counts()

    # bins
    bins = [0, 100, 500, 2000, 10000, 10**9]
    labels = ["≤100", "101–500", "501–2k", "2k–10k", ">10k"]
    terminal = terminal.copy()
    terminal["changes_bin"] = pd.cut(terminal["changes"], bins=bins, labels=labels)
    merge_by_bin = terminal.groupby("changes_bin", observed=True)["status"].apply(
        lambda s: (s == "merged").mean()
    )

    comment_bins = [0, 1, 3, 10, 10**9]
    comment_labels = ["0", "1–2", "3–9", "≥10"]
    terminal["comment_bin"] = pd.cut(terminal["comment_total"], bins=comment_bins, labels=comment_labels)
    merge_by_comment = terminal.groupby("comment_bin", observed=True)["status"].apply(
        lambda s: (s == "merged").mean()
    )

    lifespan_bins = [0, 1, 24, 168, 10**9]
    lifespan_labels = ["<1h", "1–24h", "1–7d", ">7d"]
    terminal["lifespan_bin"] = pd.cut(terminal["lifespan_hours"], bins=lifespan_bins, labels=lifespan_labels)
    merge_by_life = terminal.groupby("lifespan_bin", observed=True)["status"].apply(
        lambda s: (s == "merged").mean()
    )

    det = Counter()
    for methods in df["detection_method"].fillna(""):
        if not methods:
            det["(empty)"] += 1
            continue
        for m in methods.split("|"):
            det[m] += 1

    reg = df["regression_handling"].value_counts()
    repro = df["reproducibility"].value_counts()

    fix_modes = Counter()
    new_issue = 0
    for d in records:
        if d["perf_labels"].get("regression_handling") != "fix_in_pr":
            continue
        mp = d["structured_analysis"]["maintainer_practices"]
        traj = " ".join(d.get("evidence", {}).get("collaboration_trajectory") or [])
        fix_modes[classify_fix_mode(mp.get("regression_detail") or "", traj)] += 1

    anti_fix = df[
        df["antipattern_in_fix"].notna()
        & ~df["antipattern_in_fix"].astype(str).str.lower().isin(["none", "null", "nan"])
    ]

    linked = int(df["has_linked_issue"].sum())

    agent_merge = (
        df.groupby("agent", as_index=False)
        .agg(n=("pr_id", "count"), merge_rate=("status", lambda s: (s == "merged").mean()))
        .query("n >= 30")
        .sort_values("merge_rate", ascending=False)
    )

    opt_layer = df["optimization_layer"].value_counts().head(12)
    anti_merged = Counter()
    anti_closed = Counter()
    for _, row in df.iterrows():
        for ap in (row["inefficiency_antipattern"] or "").split("|"):
            if not ap or ap == "none":
                continue
            if row["status"] == "merged":
                anti_merged[ap] += 1
            elif row["status"] == "closed":
                anti_closed[ap] += 1

    lines = [
        "# Full Analysis — Agent Performance PR Corpus",
        "",
        f"> 生成自 `finaldatabase/per_pr/{{pr_id}}/{{pr_id}}_analysis.json`（及 6 条根目录 few-shot 金标）；样本量 **{n}** 条，与主表对齐。",
        f"> 配套宽表：`full_analysis_distilled.csv`（由 `python3 generate_full_analysis.py` 再生成）。",
        "",
        "---",
        "",
        "## 1. 合并结果总体分布",
        "",
        "| 状态 | 数量 | 占比 |",
        "|------|------|------|",
        f"| merged | {len(merged)} | {pct(len(merged), n)} |",
        f"| closed（终态未合并） | {len(closed)} | {pct(len(closed), n)} |",
        f"| open（仍开放） | {len(open_)} | {pct(len(open_), n)} |",
        "",
        f"- **全库合并率**（含 open）：{pct(len(merged), n)}（{len(merged)}/{n}）",
        f"- **终态合并率**（仅 merged + closed，n={len(terminal)}）：**{pct(len(merged), len(terminal))}**",
        "",
        "说明：closed 在本数据集中指 GitHub 上已关闭但未合并的 PR，不等同于「审查通过」；open 为截至数据快照仍开放。",
        "",
        "---",
        "",
        "## 2. 通过（merged）与不通过（closed）的主要原因",
        "",
        "依据 `perf_labels.outcome_reason` 归并（分析 JSON 中的归纳标签，非原始 review 原文）。",
        "",
        "### 2.1 Merged — 归并后的主要原因",
        "",
        "| 归并类别 | 数量 | 占 merged 比例 |",
        "|----------|------|----------------|",
    ]
    for k, v in merged_groups.items():
        lines.append(f"| {k} | {v} | {pct(v, len(merged))} |")

    lines += [
        "",
        "**解读（描述性，非因果）**：绝大多数合并 PR 被标为 **小范围、低风险**（`small_scope_low_risk`）；其次为 **经 review 迭代后合并**（`after_review_iteration`）；另有约一成合并路径 **缺乏 formal review 信号**（`without_formal_review`）。",
        "",
        "Merged `outcome_reason` 原始 Top 5：",
        "",
        "| outcome_reason | 数量 |",
        "|----------------|------|",
    ]
    for k, v in merged["outcome_reason"].value_counts().head(5).items():
        lines.append(f"| `{k}` | {v} |")

    lines += [
        "",
        "### 2.2 Closed — 归并后的主要原因",
        "",
        "| 归并类别 | 数量 | 占 closed 比例 |",
        "|----------|------|----------------|",
    ]
    for k, v in closed_groups.items():
        lines.append(f"| {k} | {v} | {pct(v, len(closed))} |")

    lines += [
        "",
        "**解读**：closed 的 dominant 模式是 **流程性关闭**（stale / 无审查互动 / 作者自行关闭），而非单一「性能不达标」标签；在 **有 review 文本** 的子集中，`functional_failure`、`correctness_edge_case` 等才会更突出。",
        "",
        "Closed `outcome_reason` 原始 Top 5：",
        "",
        "| outcome_reason | 数量 |",
        "|----------------|------|",
    ]
    for k, v in closed["outcome_reason"].value_counts().head(5).items():
        lines.append(f"| `{k}` | {v} |")

    lines += [
        "",
        "---",
        "",
        "## 3. 合并结果与变更规模 / 评论规模",
        "",
        "### 3.1 代码变更量（changes）",
        "",
        "| changes 分箱 | 终态 PR 数 | 合并率 |",
        "|-------------|-----------|--------|",
    ]
    for idx, rate in merge_by_bin.items():
        cnt = int((terminal["changes_bin"] == idx).sum())
        lines.append(f"| {idx} | {cnt} | {100*rate:.1f}% |")

    lines += [
        "",
        f"- merged 中位数 changes：**{merged['changes'].median():.0f}**；closed 中位数：**{closed['changes'].median():.0f}**",
        "- **未发现「修改越多越容易合并」**：≤100 行合并率最高（约 63%），>10k 行合并率约 52%。",
        "",
        "### 3.2 评论规模（review comment + PR comment）",
        "",
        "| comment 分箱 | 终态 PR 数 | 合并率 |",
        "|-------------|-----------|--------|",
    ]
    for idx, rate in merge_by_comment.items():
        cnt = int((terminal["comment_bin"] == idx).sum())
        lines.append(f"| {idx} | {cnt} | {100*rate:.1f}% |")

    lines += [
        "",
        f"- merged 评论总数中位数：**{merged['comment_total'].median():.0f}**；closed：**{closed['comment_total'].median():.0f}**",
        "- 评论极少（0 条）的 PR 合并率反而较高，与「无 review 快速合并」路径一致；高评论量并不对应更高合并率。",
        "",
        "---",
        "",
        "## 4. 合并结果与 PR 存活时间",
        "",
        "| 存活时间 | 终态 PR 数 | 合并率 |",
        "|----------|-----------|--------|",
    ]
    for idx, rate in merge_by_life.items():
        cnt = int((terminal["lifespan_bin"] == idx).sum())
        lines.append(f"| {idx} | {cnt} | {100*rate:.1f}% |")

    lines += [
        "",
        f"- merged 存活时间中位数：**{merged['lifespan_hours'].median():.3f} 小时**（约 {merged['lifespan_hours'].median()*60:.0f} 分钟）",
        f"- closed 存活时间中位数：**{closed['lifespan_hours'].median():.1f} 小时**（约 {closed['lifespan_hours'].median()/24:.1f} 天）",
        f"- merged 中 `fast_merge=true` 占比：**{merged['fast_merge'].mean()*100:.1f}%**；closed 为 0%",
        "",
        "**关联描述**：合并 PR 显著更「短命」；长寿命 closed 多与 stale / 无互动相关，而非慢审后拒绝。",
        "",
        "---",
        "",
        "## 5. 性能优化与性能问题出现的层面",
        "",
        "### 5.1 优化所在层面（`optimization_layer`，Top 12）",
        "",
        "| optimization_layer | 数量 | 占比 |",
        "|-------------------|------|------|",
    ]
    for k, v in opt_layer.items():
        lines.append(f"| `{k}` | {v} | {pct(v, n)} |")

    lines += [
        "",
        "### 5.2 低效/问题反模式（`inefficiency_antipattern` ≠ none）",
        "",
        "**Merged 侧 Top：** " + ", ".join(f"`{k}`({v})" for k, v in anti_merged.most_common(6)),
        "",
        "**Closed 侧 Top：** " + ", ".join(f"`{k}`({v})" for k, v in anti_closed.most_common(6)),
        "",
        "两侧出现最多的均为 `repeated_io`；closed 侧 `repeated_io` 略多。整体反模式标签覆盖率有限（多数 PR 为 `none`）。",
        "",
        "---",
        "",
        "## 6. 维护者识别性能问题的方式",
        "",
        "字段：`perf_labels.detection_method`（可多选）。",
        "",
        "| detection_method | 出现 PR 数 | 占全库 |",
        "|------------------|-----------|--------|",
    ]
    for k, v in det.most_common(10):
        lines.append(f"| `{k}` | {v} | {pct(v, n)} |")

    lines += [
        "",
        "- **最主要方式**：在可识别时以 **`code_reading`（静态读码审查）** 为主（约 378 条 PR 至少出现一次）。",
        "- 其次为 **`ci_auto`**（约 93 条）；`profiler`、`load_test`、`benchmark` 单独出现极少。",
        "- 约 **786 条** 标为 `unknown`，与全库 **~71% 无 formal review** 一致——识别方式大量不可观测。",
        "",
        "---",
        "",
        "## 7. PR 材料能否支撑性能缺陷复现",
        "",
        "| reproducibility | 数量 | 占比 |",
        "|-----------------|------|------|",
    ]
    for k, v in repro.items():
        lines.append(f"| `{k}` | {v} | {pct(v, n)} |")

    lines += [
        "",
        "辅助信号：",
        f"- `body_has_repro_steps=true`：**{int(df['body_has_repro_steps'].sum())}**（{pct(int(df['body_has_repro_steps'].sum()), n)}）",
        f"- `body_has_benchmark_table=true`：**{int(df['body_has_benchmark_table'].sum())}**",
        f"- `material_reproducibility=sufficient`：**{int((df['material_reproducibility']=='sufficient').sum())}**",
        "",
        "**结论（材料维度）**：绝大多数 PR 的材料被标为 **insufficient 或 partial**；仅约 **2%** 达到 sufficient。",
        "",
        "---",
        "",
        "## 8. 性能退化 / 审查问题的处置方式",
        "",
        "| regression_handling | 数量 | 占比 |",
        "|---------------------|------|------|",
    ]
    for k, v in reg.items():
        lines.append(f"| `{k}` | {v} | {pct(v, n)} |")

    fix_total = int((df["regression_handling"] == "fix_in_pr").sum())
    lines += [
        "",
        f"- **`not_applicable`**（{pct(int((df['regression_handling']=='not_applicable').sum()), n)}）：无明确退化处置语境，多为直接合并或流程性关闭。",
        f"- **`reject_close`**（{pct(int((df['regression_handling']=='reject_close').sum()), n)}）：以拒绝/关闭为主，多见于 closed。",
        f"- **`fix_in_pr`**（{fix_total} 条）：同一 PR 内修复；`revert` 仅 **{int((df['regression_handling']=='revert').sum())}** 条。",
        "",
        "### 8.1 `fix_in_pr` 的修复主体（启发式文本分类，非 ground truth）",
        "",
        "| 修复模式 | 数量 | 占 fix_in_pr |",
        "|----------|------|--------------|",
    ]
    for k, v in fix_modes.most_common():
        lines.append(f"| {k} | {v} | {pct(v, fix_total)} |")

    lines += [
        "",
        "- 数据集 **每条 PR 仅一个 `meta.agent`**，无结构化 multi-agent 字段；文本中偶发多 bot 审查，但 **无法系统统计多 Agent 协同修复比例**。",
        f"- 修复引入新问题信号：`antipattern_in_fix` 非 none 共 **{len(anti_fix)}** 条（{pct(len(anti_fix), n)}），仅供参考。",
        "",
        "---",
        "",
        "## 9. 与 Issue 的关联",
        "",
        f"- `linked_issue_count > 0`：**{linked}** 条（**{pct(linked, n)}**）",
        f"- 无关联 issue：**{n - linked}** 条（**{pct(n - linked, n)}**）",
        "",
        "多数 Agent 性能 PR **并非**明确为修复某一 linked issue 而开；性能优化常直接由 Agent 发起。",
        "",
        "---",
        "",
        "## 10. 通过率、问题分布与能力边界（描述性归纳）",
        "",
        f"- **AI 性能 PR 终态合并率：约 {100*len(merged)/len(terminal):.1f}%**（{len(merged)}/{len(terminal)}）。",
        "",
        "### 10.1 合并成功侧常见的性能关注点（`perf_focus` Top，merged）",
        "",
    ]
    pf_m = Counter()
    for _, row in merged.iterrows():
        for f in (row["perf_focus"] or "").split("|"):
            if f:
                pf_m[f] += 1
    lines.append(", ".join(f"`{k}`({v})" for k, v in pf_m.most_common(8)))

    lines += [
        "",
        "### 10.2 未合并侧常见的性能关注点（`perf_focus` Top，closed）",
        "",
    ]
    pf_c = Counter()
    for _, row in closed.iterrows():
        for f in (row["perf_focus"] or "").split("|"):
            if f:
                pf_c[f] += 1
    lines.append(", ".join(f"`{k}`({v})" for k, v in pf_c.most_common(8)))

    lines += [
        "",
        "### 10.3 `boundary_tag` 分布",
        "",
        "| boundary_tag | 数量 |",
        "|--------------|------|",
    ]
    for k, v in df["boundary_tag"].value_counts().items():
        lines.append(f"| `{k}` | {v} |")

    lines += [
        "",
        "### 10.4 可能的特长点与边界点（基于标签分布，待人工验证）",
        "",
        "**特长点（合并侧信号）**",
        "- 小范围、控制流/编译器常量折叠、构建与缓存类改动，在 **低审查摩擦** 路径下易合并。",
        "- `technical_stack` 边界占多数（608 条），表示问题落在 Agent 可处理的常规技术栈层级。",
        "",
        "**边界点（未合并或高风险信号）**",
        "- 流程性关闭（stale / 无 review）占比极高，掩盖了真实「性能否决」比例。",
        "- `evidence_required` 类边界（35 条）与 `missing_benchmark` / insufficient reproducibility 呼应。",
        "- 大范围改动（>10k changes）合并不占优；`repeated_io` 等反模式在 closed 略多。",
        "- 性能效果缺乏可复现材料时，审查难以闭环。",
        "",
        "---",
        "",
        "## 11. Agent 分层合并率（n≥30）",
        "",
        "| Agent | PR 数 | 合并率 |",
        "|-------|-------|--------|",
    ]
    for _, row in agent_merge.iterrows():
        lines.append(f"| {row['agent']} | {int(row['n'])} | {100*row['merge_rate']:.1f}% |")

    lines += [
        "",
        "---",
        "",
        "## 12. 数据与方法说明",
        "",
        "- 统计基于分析 JSON 中的 **标签与叙述字段**，不是对 GitHub 原始事件的重新跑批。",
        "- `outcome_reason` 等标签由 LLM 分析生成，存在 **同义标签膨胀**；本报告对 merge/close 做了粗归并。",
        "- 修复主体、是否引入新问题等结论来自 **文本启发式**，写入论文前建议抽样人工复核。",
        "- open 状态 PR 在计算「通过率」时通常应剔除或单独报告。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    records = load_all_analyses()
    if not records:
        raise SystemExit("No analysis JSON files found.")

    df = pd.DataFrame([flatten_record(d) for d in records])
    df["merge_reason_group"] = df["outcome_reason"].map(classify_merge_reason)
    df["close_reason_group"] = df["outcome_reason"].map(classify_close_reason)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8")

    md = build_markdown(df, records)
    OUT_MD.write_text(md, encoding="utf-8")

    print(f"Wrote {OUT_CSV} ({len(df)} rows)")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
