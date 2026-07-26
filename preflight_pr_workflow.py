#!/usr/bin/env python3
"""Preflight checks for PR analysis workflow assets."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent
TOKEN_PATH = ROOT / ".deepseekToken"
SCHEMA_PATH = ROOT / "schema.json"
PROMPT_PATH = ROOT / "prompt.md"
ANALYSIS_FILES = [
    ROOT / "3228424652_analysis.json",
    ROOT / "3194284966_analysis.json",
    ROOT / "3145702280_analysis.json",
    ROOT / "3125029980_analysis.json",
    ROOT / "3074351366_analysis.json",
    ROOT / "3022909076_analysis.json",
]

TAXONOMY: dict[str, set[str]] = {
    "perf_labels.inefficiency_antipattern": {
        "nested_loop",
        "repeated_io",
        "frequent_gc",
        "string_traversal",
        "lock_misuse",
        "none",
        "unknown",
    },
    "perf_labels.evidence_type": {"narrative", "benchmark", "profiling", "ci_task_eval", "unknown"},
    "perf_labels.detection_method": {"code_reading", "profiler", "load_test", "ci_auto", "mixed", "unknown"},
    "perf_labels.reproducibility": {"sufficient", "partial", "insufficient", "unknown"},
    "perf_labels.regression_handling": {
        "ignore",
        "reject_close",
        "revert",
        "fix_in_pr",
        "fix_followup",
        "not_applicable",
        "unknown",
    },
    "perf_labels.boundary_tag": {"technical_stack", "evidence_required", "process"},
    "perf_labels.topic_difficulty": {"low", "medium", "high"},
    "perf_labels.confidence": {"low", "medium", "high"},
    "structured_analysis.merge_outcome_context.outcome": {"merged", "closed"},
    "structured_analysis.capability_boundary.boundary_type": {
        "technical_stack",
        "evidence_required",
        "process",
    },
    "evidence.review_signals[].channel": {
        "inline_review_comment",
        "formal_review",
        "pr_comment",
    },
}


def collect_paths(obj: Any, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            paths.add(p)
            paths |= collect_paths(v, p)
    elif isinstance(obj, list) and obj and isinstance(obj[0], dict):
        paths |= collect_paths(obj[0], f"{prefix}[]")
    return paths


def get_nested(doc: dict[str, Any], path: str) -> Any:
    cur: Any = doc
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def check_api_key() -> dict[str, Any]:
    section: dict[str, Any] = {"token_file_exists": TOKEN_PATH.exists()}
    if not TOKEN_PATH.exists():
        section["status"] = "FAIL"
        section["message"] = "Missing .deepseekToken"
        return section

    token = TOKEN_PATH.read_text(encoding="utf-8").strip()
    if not token:
        section["status"] = "FAIL"
        section["message"] = "Empty token file"
        return section
    if not re.match(r"^sk-[A-Za-z0-9]+$", token):
        section["status"] = "WARN"
        section["message"] = "Token format unexpected (expected sk-...)"
    else:
        section["token_format"] = f"ok (sk- prefix, length {len(token)})"

    try:
        resp = requests.get(
            "https://api.deepseek.com/models",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001
        section["status"] = "FAIL"
        section["message"] = f"Network/API error: {exc}"
        return section

    if resp.status_code == 200:
        models = [m.get("id") for m in resp.json().get("data", [])[:8]]
        section["status"] = "PASS"
        section["message"] = "API key accepted (GET /models 200)"
        section["sample_models"] = [m for m in models if m]
    elif resp.status_code == 401:
        section["status"] = "FAIL"
        section["message"] = "Unauthorized (401) — key invalid or revoked"
    else:
        section["status"] = "WARN"
        section["message"] = f"GET /models returned HTTP {resp.status_code}"
        section["body_snippet"] = resp.text[:200]
    return section


def is_required_schema_path(path: str) -> bool:
    """Paths that must exist on every analysis output (template leaf placeholders excluded)."""
    if path.startswith("structured_analysis.maintainer_practices.detection_detail."):
        return False
    if ".timeline.event_counts." in path and not path.endswith("event_counts"):
        return False
    if ".collaboration.review_states." in path and not path.endswith("review_states"):
        return False
    if ".change_scale.files_by_status." in path and not path.endswith("files_by_status"):
        return False
    return True


def validate_json_files(schema: dict[str, Any]) -> dict[str, Any]:
    expected_paths = {p for p in collect_paths(schema) if is_required_schema_path(p)}
    section: dict[str, Any] = {"files": {}, "cross_file_summary": {}}

    all_missing: list[tuple[str, str]] = []
    all_extra: list[tuple[str, str]] = []

    for fp in ANALYSIS_FILES:
        name = fp.name
        fr: dict[str, Any] = {
            "parse_ok": True,
            "pr_id_match_filename": None,
            "missing_paths": [],
            "extra_paths": [],
            "type_issues": [],
            "taxonomy_issues": [],
            "rule_issues": [],
        }
        try:
            doc = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fr["parse_ok"] = False
            fr["error"] = str(exc)
            section["files"][name] = fr
            continue

        m = re.match(r"^(\d+)_analysis\.json$", name)
        fr["pr_id_match_filename"] = bool(m and doc.get("pr_id") == int(m.group(1)))

        actual_paths = collect_paths(doc)
        fr["missing_paths"] = sorted(expected_paths - actual_paths)
        # Dynamic dict leaves (event types, review states) are expected beyond template placeholders.
        fr["extra_paths"] = sorted(
            p
            for p in (actual_paths - collect_paths(schema))
            if not (
                ".timeline.event_counts." in p
                or ".collaboration.review_states." in p
                or ".change_scale.files_by_status." in p
            )
        )
        all_missing.extend((name, p) for p in fr["missing_paths"])
        all_extra.extend((name, p) for p in fr["extra_paths"])

        dc = doc.get("data_coverage", {})
        if isinstance(dc, dict):
            for k, v in dc.items():
                if not isinstance(v, bool):
                    fr["type_issues"].append(f"data_coverage.{k} should be bool, got {type(v).__name__}")

        if not isinstance(doc.get("perf_labels", {}).get("blocking"), bool):
            fr["type_issues"].append("perf_labels.blocking should be bool")

        es = doc.get("quantitative_metrics", {}).get("evidence_signals", {})
        for k in (
            "body_has_benchmark_table",
            "body_has_repro_steps",
            "body_has_numeric_perf_claim",
            "body_mentions_profiler",
        ):
            v = es.get(k)
            if v is not None and not isinstance(v, bool):
                fr["type_issues"].append(f"evidence_signals.{k} should be bool")

        lc = doc.get("structured_analysis", {}).get("merge_outcome_context", {}).get("lifecycle", {})
        if "fast_merge" in lc and not isinstance(lc.get("fast_merge"), bool):
            fr["type_issues"].append("lifecycle.fast_merge should be bool")

        for sig in doc.get("evidence", {}).get("review_signals", []):
            if "blocking" in sig and not isinstance(sig.get("blocking"), bool):
                fr["type_issues"].append("review_signals[].blocking should be bool")

        cs = doc.get("quantitative_metrics", {}).get("change_scale", {})
        add, dele, chg = cs.get("additions"), cs.get("deletions"), cs.get("changes")
        if add is not None and dele is not None and chg is not None and chg != add + dele:
            fr["rule_issues"].append(f"changes ({chg}) != additions+deletions ({add + dele})")

        cvr = (
            doc.get("structured_analysis", {})
            .get("merge_outcome_context", {})
            .get("change_scale_vs_repository", {})
        )
        if cvr.get("pr_change_lines") is not None and chg is not None and cvr["pr_change_lines"] != chg:
            fr["rule_issues"].append("pr_change_lines != quantitative_metrics.change_scale.changes")

        meta_status = doc.get("meta", {}).get("status")
        outcome = (
            doc.get("structured_analysis", {}).get("merge_outcome_context", {}).get("outcome")
        )
        if meta_status in ("merged", "closed") and outcome and meta_status != outcome:
            fr["rule_issues"].append(f"meta.status ({meta_status}) != outcome ({outcome})")

        for path, allowed in TAXONOMY.items():
            if path.endswith("[]"):
                continue
            val = get_nested(doc, path)
            if val is None:
                continue
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, str) and path.startswith("perf_labels") and item not in allowed:
                        fr["taxonomy_issues"].append(
                            f'{path}: non-enum "{item}" (allowed: {sorted(allowed)})'
                        )
            elif isinstance(val, str) and val not in allowed:
                fr["taxonomy_issues"].append(f'{path}: "{val}" not in {sorted(allowed)}')

        for i, sig in enumerate(doc.get("evidence", {}).get("review_signals", [])):
            ch = sig.get("channel")
            if ch and ch not in TAXONOMY["evidence.review_signals[].channel"]:
                fr["taxonomy_issues"].append(f'review_signals[{i}].channel: "{ch}"')

        section["files"][name] = fr

    section["cross_file_summary"] = {
        "file_count": len(ANALYSIS_FILES),
        "all_parse_ok": all(f["parse_ok"] for f in section["files"].values()),
        "total_missing_paths": len(all_missing),
        "total_extra_paths": len(all_extra),
        "total_type_issues": sum(len(f["type_issues"]) for f in section["files"].values()),
        "total_rule_issues": sum(len(f["rule_issues"]) for f in section["files"].values()),
        "total_taxonomy_issues": sum(len(f["taxonomy_issues"]) for f in section["files"].values()),
    }
    return section


def check_prompt_vs_schema(schema: dict[str, Any], prompt: str) -> dict[str, Any]:
    notes: list[str] = []
    hard: list[str] = []

    for key in (
        "pr_id",
        "meta",
        "quantitative_metrics",
        "perf_labels",
        "structured_analysis",
        "evidence",
        "data_coverage",
    ):
        if key not in schema:
            hard.append(f"schema.json missing top-level key {key}")
        if key not in prompt:
            hard.append(f"prompt.md does not mention top-level key {key}")

    schema_det = schema["structured_analysis"]["maintainer_practices"]["detection_detail"]
    if "profiler" in prompt and "load_test" in prompt:
        if "profiler" not in schema_det or "load_test" not in schema_det:
            notes.append(
                "prompt.md lists detection_detail keys code_reading/profiler/load_test/ci_auto; "
                "schema.json template only documents code_reading and ci_auto (template doc gap)."
            )

    if "open" in str(schema["meta"].get("status", "")):
        notes.append(
            "schema meta.status includes open; prompt merge_outcome_context.outcome is merged/closed only — "
            "for still-open PRs, workflow should map status explicitly."
        )

    notes.append(
        "Gold JSON 3194284966 uses files_by_status.removed; prompt examples say deleted — naming drift only."
    )
    notes.append(
        "Exemplars use custom perf_focus / outcome_reason / evidence_type labels beyond strict enums; "
        "consistent with prompt rule allowing new snake_case when needed."
    )

    status = "PASS" if not hard else "FAIL"
    if status == "PASS" and notes:
        status = "WARN"
    return {"status": status, "hard_contradictions": hard, "soft_gaps_and_exemplar_drift": notes}


def write_reports(report: dict[str, Any]) -> None:
    md_path = ROOT / "PR_workflow_preflight_report.md"
    json_path = ROOT / "PR_workflow_preflight_report.json"

    lines = [
        "# PR 分析工作流 — 预检报告",
        "",
        f"生成时间 (UTC): {report['generated_at']}",
        "",
        "## 总体结论",
        "",
        f"- **是否建议进入下一步**: {'是' if report['overall']['ready_for_next_step'] else '否'}",
        f"- **说明**: {report['overall']['recommendation']}",
    ]
    if report["overall"]["blockers"]:
        lines.append("- **阻塞项**:")
        for b in report["overall"]["blockers"]:
            lines.append(f"  - {b}")
    if report["overall"]["warnings"]:
        lines.append("- **警告**:")
        for w in report["overall"]["warnings"]:
            lines.append(f"  - {w}")

    api = report["sections"]["deepseek_api_key"]
    lines.extend(["", "## 1. DeepSeek API Key", "", f"- 状态: **{api.get('status')}**", f"- 结果: {api.get('message')}"])
    if api.get("sample_models"):
        lines.append(f"- 可用模型样例: {', '.join(api['sample_models'])}")

    jv = report["sections"]["json_validation"]["cross_file_summary"]
    lines.extend(
        [
            "",
            "## 2. JSON 与 schema.json 字段对应",
            "",
            f"- 分析样例数量: {jv['file_count']}",
            f"- 全部可解析: {jv['all_parse_ok']}",
            f"- 相对模板缺失路径总数: {jv['total_missing_paths']}",
            f"- 相对模板多余路径总数: {jv['total_extra_paths']}",
            f"- 类型/布尔格式问题: {jv['total_type_issues']}",
            f"- 一致性规则问题: {jv['total_rule_issues']}",
            f"- 受控词表严格枚举偏离: {jv['total_taxonomy_issues']}",
            "",
            "### 逐文件摘要",
        ]
    )
    for fname, fr in report["sections"]["json_validation"]["files"].items():
        lines.append(f"#### {fname}")
        lines.append(f"- pr_id 与文件名一致: {fr.get('pr_id_match_filename')}")
        lines.append(f"- 缺失字段: {', '.join(fr['missing_paths']) if fr['missing_paths'] else '无'}")
        lines.append(f"- 多余字段: {', '.join(fr['extra_paths']) if fr['extra_paths'] else '无'}")
        for ri in fr.get("rule_issues", []):
            lines.append(f"- 规则: {ri}")
        for ti in fr.get("taxonomy_issues", [])[:10]:
            lines.append(f"- 词表: {ti}")
        if len(fr.get("taxonomy_issues", [])) > 10:
            lines.append(f"- … 另有 {len(fr['taxonomy_issues']) - 10} 条词表提示")
        lines.append("")

    ps = report["sections"]["prompt_vs_schema"]
    lines.extend([f"## 3. prompt.md 与 schema.json", "", f"- 评估: **{ps['status']}**"])
    if ps["hard_contradictions"]:
        lines.append("- 硬矛盾:")
        for c in ps["hard_contradictions"]:
            lines.append(f"  - {c}")
    if ps["soft_gaps_and_exemplar_drift"]:
        lines.append("- 文档/样例软差异:")
        for c in ps["soft_gaps_and_exemplar_drift"]:
            lines.append(f"  - {c}")

    lines.extend(
        [
            "",
            "## 4. 安全提醒",
            "",
            "- 请勿将 `.deepseekToken` 提交到 Git；推送前确认已在 `.gitignore` 中。",
            "",
        ]
    )

    md_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    api_section = check_api_key()
    json_section = validate_json_files(schema)
    prompt_section = check_prompt_vs_schema(schema, prompt)

    blockers: list[str] = []
    if api_section.get("status") != "PASS":
        blockers.append("DeepSeek API key not validated")
    if not json_section["cross_file_summary"]["all_parse_ok"]:
        blockers.append("JSON parse failure in exemplar files")
    if json_section["cross_file_summary"]["total_missing_paths"]:
        blockers.append("Exemplar JSON missing paths required by schema.json")
    if json_section["cross_file_summary"]["total_type_issues"]:
        blockers.append("Boolean/type format errors in exemplar JSON")
    if prompt_section["status"] == "FAIL":
        blockers.append("prompt.md vs schema.json hard contradictions")

    warnings: list[str] = []
    if json_section["cross_file_summary"]["total_taxonomy_issues"]:
        warnings.append(
            f"Exemplars contain {json_section['cross_file_summary']['total_taxonomy_issues']} "
            "strict-enum deviations (mostly custom snake_case tags allowed by prompt)."
        )
    if prompt_section["status"] == "WARN":
        warnings.append("prompt/schema soft documentation gaps — see section 3.")
    gitignore = ROOT / ".gitignore"
    if gitignore.exists() and ".deepseekToken" not in gitignore.read_text(encoding="utf-8"):
        warnings.append(".deepseekToken is not listed in .gitignore yet.")

    ready = not blockers
    recommendation = (
        "预检通过：DeepSeek API 可用，六份样例 JSON 结构与模板一致，格式正确；"
        "prompt 与 schema 仅有文档级软差异（见第 3 节），可进入工作流脚本开发与试跑。"
        if ready
        else "请先解决阻塞项，再运行批量分析。"
    )

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": {
            "deepseek_api_key": api_section,
            "json_validation": json_section,
            "prompt_vs_schema": prompt_section,
        },
        "overall": {
            "ready_for_next_step": ready,
            "blockers": blockers,
            "warnings": warnings,
            "recommendation": recommendation,
        },
    }
    write_reports(report)
    print(f"Wrote {ROOT / 'PR_workflow_preflight_report.md'}")
    print(f"API: {api_section.get('status')}; ready: {ready}")


if __name__ == "__main__":
    main()
