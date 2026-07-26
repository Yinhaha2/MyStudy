#!/usr/bin/env python3
"""Assemble PR analysis prompts, call DeepSeek, write {pr_id}_analysis.json."""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

MYSTUDY = Path(__file__).resolve().parent
OUT_ANALYSIS = MYSTUDY / "output_pr_analysis"
FINALDB = MYSTUDY / "finaldatabase"
MASTER_CSV = FINALDB / "pr_master" / "perf_prs_expanded_final.csv"
PROMPT_PATH = MYSTUDY / "prompt.md"
SCHEMA_PATH = MYSTUDY / "schema.json"
TOKEN_PATH = MYSTUDY / ".deepseekToken"
DEEPSEEK_CHAT_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-v4-pro"

# USD per 1M tokens (DeepSeek official list prices, 2026-07)
PRICE_TABLE: dict[str, dict[str, float]] = {
    "deepseek-v4-flash": {"input_miss": 0.14, "input_cached": 0.0028, "output": 0.28},
    "deepseek-v4-pro": {"input_miss": 0.435, "input_cached": 0.003625, "output": 0.87},
}

FEWSHOT_PR_IDS = [
    3228424652,
    3074351366,
    3194284966,
    3145702280,
    3125029980,
    3022909076,
]

PAYLOAD_MODE = "standard_no_patch"
MAX_TEXT_FIELD = 12_000
MAX_DIFF_HUNK = 8_000
MAX_FILE_DETAIL_ROWS = 200
ANALYSIS_ATTEMPTS = 2

FAILURE_LIST_JSON = OUT_ANALYSIS / "failed_prs.json"
FAILURE_LIST_MD = OUT_ANALYSIS / "failed_prs.md"


def load_token() -> str:
    token = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_TOKEN")
    if token:
        return token.strip()
    if TOKEN_PATH.exists():
        t = TOKEN_PATH.read_text(encoding="utf-8").strip()
        if t:
            return t
    raise SystemExit("Missing DeepSeek API key (.deepseekToken or DEEPSEEK_API_KEY)")


def _clip(text: Any, limit: int) -> str:
    s = "" if text is None or (isinstance(text, float) and pd.isna(text)) else str(text)
    if len(s) <= limit:
        return s
    return s[:limit] + "\n...[truncated]..."


def _parse_topic(row: pd.Series) -> tuple[int | None, str]:
    topic = str(row.get("Topic") or row.get("topic_name") or "").strip()
    if not topic:
        return None, ""
    m = re.match(r"^(\d+)_", topic)
    topic_id = int(m.group(1)) if m else None
    return topic_id, topic


def _repo_from_url(html_url: str) -> str:
    if not html_url or "github.com/" not in html_url:
        return ""
    path = html_url.replace("https://github.com/", "").split("/pull/")[0]
    return path.strip("/")


def _read_parquet_dir(pr_id: int, name: str) -> pd.DataFrame:
    path = FINALDB / "per_pr" / str(pr_id) / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def _df_to_records(df: pd.DataFrame, *, drop_cols: set[str] | None = None) -> list[dict[str, Any]]:
    if df.empty:
        return []
    drop_cols = drop_cols or set()
    out = df.copy()
    for c in drop_cols:
        if c in out.columns:
            out = out.drop(columns=[c])
    out = out.where(pd.notna(out), None)
    return json.loads(out.to_json(orient="records", date_format="iso"))


def build_payload(pr_id: int, *, mode: str = PAYLOAD_MODE) -> dict[str, Any]:
    master = pd.read_csv(MASTER_CSV)
    row = master.loc[master["id"] == pr_id]
    if row.empty:
        raise ValueError(f"pr_id {pr_id} not in {MASTER_CSV}")
    row = row.iloc[0]

    topic_id, topic_name = _parse_topic(row)
    meta = {
        "pr_id": int(pr_id),
        "title": _clip(row.get("title"), 500),
        "html_url": str(row.get("html_url") or ""),
        "repo": _repo_from_url(str(row.get("html_url") or "")),
        "agent": str(row.get("agent") or ""),
        "user": str(row.get("user") or ""),
        "status": str(row.get("status") or ""),
        "state": str(row.get("state") or ""),
        "created_at": str(row.get("created_at") or ""),
        "merged_at": None if pd.isna(row.get("merged_at")) else str(row.get("merged_at")),
        "closed_at": None if pd.isna(row.get("closed_at")) else str(row.get("closed_at")),
        "detection_source": str(row.get("detection_source") or ""),
        "aidev_task_type": str(row.get("aidev_task_type") or ""),
        "aidev_task_confidence": (
            None
            if pd.isna(row.get("aidev_task_confidence"))
            else float(row.get("aidev_task_confidence"))
            if isinstance(row.get("aidev_task_confidence"), (int, float))
            else row.get("aidev_task_confidence")
        ),
        "topic_id": topic_id,
        "topic_name": topic_name,
        "body": _clip(row.get("body"), MAX_TEXT_FIELD),
    }

    reviews = _read_parquet_dir(pr_id, "reviews.parquet")
    comments = _read_parquet_dir(pr_id, "comments.parquet")
    review_comments = _read_parquet_dir(pr_id, "review_comments.parquet")
    commits = _read_parquet_dir(pr_id, "commits.parquet")
    commit_details = _read_parquet_dir(pr_id, "commit_details.parquet")
    timeline = _read_parquet_dir(pr_id, "timeline.parquet")
    related = _read_parquet_dir(pr_id, "related_issue.parquet")

    if not review_comments.empty and "body" in review_comments.columns:
        review_comments = review_comments.copy()
        review_comments["body"] = review_comments["body"].map(lambda x: _clip(x, MAX_TEXT_FIELD))
    if "diff_hunk" in review_comments.columns:
        review_comments["diff_hunk"] = review_comments["diff_hunk"].map(lambda x: _clip(x, MAX_DIFF_HUNK))

    for df, col in [(reviews, "body"), (comments, "body")]:
        if not df.empty and col in df.columns:
            df[col] = df[col].map(lambda x: _clip(x, MAX_TEXT_FIELD))

    drop_patch = {"patch"} if mode == "standard_no_patch" else set()
    if not commit_details.empty and len(commit_details) > MAX_FILE_DETAIL_ROWS:
        commit_details = commit_details.head(MAX_FILE_DETAIL_ROWS)

    def _has_text(records: list[dict[str, Any]]) -> bool:
        return any(str(r.get("body") or "").strip() for r in records)

    payload: dict[str, Any] = {
        "pr_id": pr_id,
        "payload_mode": mode,
        "meta": meta,
        "reviews": _df_to_records(reviews),
        "pr_comments": _df_to_records(comments),
        "review_comments": _df_to_records(review_comments),
        "commits": _df_to_records(commits),
        "commit_file_stats": _df_to_records(commit_details, drop_cols=drop_patch),
        "timeline": _df_to_records(timeline),
        "linked_issues": _df_to_records(related),
        "data_coverage": {
            "has_commit_details": not commit_details.empty,
            "has_timeline": not timeline.empty,
            "has_formal_review": not reviews.empty,
            "has_review_or_comment_text": (
                _has_text(_df_to_records(reviews))
                or _has_text(_df_to_records(comments))
                or _has_text(_df_to_records(review_comments))
            ),
            "has_linked_issue": not related.empty,
            "per_pr_folder": (FINALDB / "per_pr" / str(pr_id)).exists(),
        },
    }
    payload["quantitative_hints"] = _quantitative_hints(payload)
    return payload


def _quantitative_hints(payload: dict[str, Any]) -> dict[str, Any]:
    commits = payload.get("commits") or []
    files = payload.get("commit_file_stats") or []
    reviews = payload.get("reviews") or []
    pr_comments = payload.get("pr_comments") or []
    review_comments = payload.get("review_comments") or []
    timeline = payload.get("timeline") or []

    additions = deletions = changes = 0
    for f in files:
        additions += int(f.get("additions") or 0)
        deletions += int(f.get("deletions") or 0)
        changes += int(f.get("changes") or f.get("commit_stats_total") or 0)
    if changes == 0 and (additions or deletions):
        changes = additions + deletions

    review_states: dict[str, int] = {}
    for r in reviews:
        st = str(r.get("state") or "UNKNOWN")
        review_states[st] = review_states.get(st, 0) + 1

    event_counts: dict[str, int] = {}
    for ev in timeline:
        et = str(ev.get("event") or "unknown")
        event_counts[et] = event_counts.get(et, 0) + 1

    body = str(payload.get("meta", {}).get("body") or "").lower()
    return {
        "change_scale": {
            "commit_count": len(commits),
            "file_count": len({f.get("filename") for f in files if f.get("filename")}),
            "additions": additions,
            "deletions": deletions,
            "changes": changes,
        },
        "collaboration": {
            "review_count": len(reviews),
            "review_states": review_states,
            "review_comment_count": len(review_comments),
            "pr_comment_count": len(pr_comments),
            "linked_issue_count": len(payload.get("linked_issues") or []),
        },
        "timeline": {
            "event_count": len(timeline),
            "event_counts": event_counts,
        },
        "evidence_signals": {
            "body_has_benchmark_table": "|" in body and ("ms" in body or "sec" in body or "%" in body),
            "body_mentions_profiler": any(k in body for k in ("profiler", "flamegraph", "perf record")),
            "body_has_repro_steps": any(k in body for k in ("repro", "reproduce", "steps to")),
            "body_has_numeric_perf_claim": bool(re.search(r"\d+\s*(%|ms|s|x|times|fold)", body)),
        },
    }


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if hasattr(obj, "item") and callable(obj.item):
        try:
            return obj.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(obj, float) and pd.isna(obj):
        return None
    return obj


def dumps_payload(obj: dict[str, Any]) -> str:
    return json.dumps(_json_safe(obj), ensure_ascii=False, indent=2)


def load_gold_analysis(pr_id: int) -> dict[str, Any]:
    path = MYSTUDY / f"{pr_id}_analysis.json"
    if not path.exists():
        raise FileNotFoundError(f"Few-shot gold missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def assemble_messages(target_pr_id: int) -> list[dict[str, str]]:
    system = PROMPT_PATH.read_text(encoding="utf-8")
    schema_text = SCHEMA_PATH.read_text(encoding="utf-8")

    parts = [
        "## Output schema template (field reference)\n",
        schema_text,
        "\n\n## Few-shot exemplars (reference only — do not re-analyze)\n",
    ]

    for i, fs_id in enumerate(FEWSHOT_PR_IDS, 1):
        payload = build_payload(fs_id)
        gold = load_gold_analysis(fs_id)
        parts.append(f"\n### Few-shot example {i} — pr_id={fs_id}\n")
        parts.append("\n#### Source payload\n```json\n")
        parts.append(dumps_payload(payload))
        parts.append("\n```\n\n#### Gold analysis\n```json\n")
        parts.append(json.dumps(gold, ensure_ascii=False, indent=2))
        parts.append("\n```\n")

    target_payload = build_payload(target_pr_id)
    parts.append(f"\n## Target Pull Request — pr_id={target_pr_id}\n\n```json\n")
    parts.append(dumps_payload(target_payload))
    parts.append(
        "\n```\n\nAnalyze the **target PR** above and return the JSON analysis object only "
        f"(root `pr_id` must be {target_pr_id})."
    )

    user = "".join(parts)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def parse_assistant_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def call_deepseek(
    messages: list[dict[str, str]],
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
    max_tokens: int = 16_000,
) -> tuple[str, dict[str, Any]]:
    token = load_token()
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.post(DEEPSEEK_CHAT_URL, headers=headers, json=body, timeout=600)
            if resp.status_code == 429:
                time.sleep(15 * (attempt + 1))
                continue
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content, data.get("usage") or {}
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"DeepSeek API failed after retries: {last_err}")


def output_path(pr_id: int) -> Path:
    d = FINALDB / "per_pr" / str(pr_id)
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{pr_id}_analysis.json"


def load_failure_list() -> dict[str, Any]:
    if not FAILURE_LIST_JSON.exists():
        return {"entries": []}
    data = json.loads(FAILURE_LIST_JSON.read_text(encoding="utf-8"))
    if "entries" not in data:
        return {"entries": data if isinstance(data, list) else []}
    return data


def failed_pr_ids() -> set[int]:
    return {int(e["pr_id"]) for e in load_failure_list().get("entries", []) if "pr_id" in e}


def remove_from_failure_list(pr_id: int) -> None:
    data = load_failure_list()
    before = len(data.get("entries", []))
    data["entries"] = [e for e in data.get("entries", []) if int(e.get("pr_id", 0)) != pr_id]
    if len(data["entries"]) == before:
        return
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    FAILURE_LIST_JSON.parent.mkdir(parents=True, exist_ok=True)
    FAILURE_LIST_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_failure_record(record: dict[str, Any]) -> None:
    FAILURE_LIST_JSON.parent.mkdir(parents=True, exist_ok=True)
    data = load_failure_list()
    pid = int(record["pr_id"])
    data["entries"] = [e for e in data.get("entries", []) if int(e.get("pr_id", 0)) != pid]
    data.setdefault("entries", []).append(record)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    FAILURE_LIST_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    line = (
        f"- {record['pr_id']}: {record.get('failed_at', '')} "
        f"attempts={record.get('attempts')} — {record.get('error_summary', '')}\n"
    )
    if FAILURE_LIST_MD.exists():
        FAILURE_LIST_MD.write_text(FAILURE_LIST_MD.read_text(encoding="utf-8") + line, encoding="utf-8")
    else:
        FAILURE_LIST_MD.write_text("# Failed PR analysis runs\n\n" + line, encoding="utf-8")


def estimate_cost_usd(usage: dict[str, Any], *, model: str = DEFAULT_MODEL) -> dict[str, float]:
    prices = PRICE_TABLE.get(model, PRICE_TABLE["deepseek-v4-pro"])
    prompt = int(usage.get("prompt_tokens") or 0)
    completion = int(usage.get("completion_tokens") or 0)
    cached = int(usage.get("prompt_cache_hit_tokens") or usage.get("cached_tokens") or 0)
    if cached == 0 and usage.get("prompt_tokens_details"):
        cached = int(usage["prompt_tokens_details"].get("cached_tokens") or 0)
    miss = max(prompt - cached, 0)
    cost_in = cached * prices["input_cached"] / 1_000_000 + miss * prices["input_miss"] / 1_000_000
    cost_out = completion * prices["output"] / 1_000_000
    return {
        "input_usd": cost_in,
        "output_usd": cost_out,
        "total_usd": cost_in + cost_out,
        "cached_prompt_tokens": cached,
        "miss_prompt_tokens": miss,
    }


def run_analysis(
    pr_id: int,
    *,
    dry_run: bool = False,
    model: str = DEFAULT_MODEL,
    save_prompt: bool = False,
) -> tuple[Path | None, dict[str, Any]]:
    t0 = time.perf_counter()
    run_meta: dict[str, Any] = {"pr_id": pr_id, "ok": False}
    messages = assemble_messages(pr_id)
    if save_prompt or dry_run:
        prompt_out = FINALDB / "per_pr" / str(pr_id) / f"{pr_id}_workflow_prompt.txt"
        prompt_out.parent.mkdir(parents=True, exist_ok=True)
        blob = "\n\n---\n\n".join(f"### {m['role']}\n{m['content']}" for m in messages)
        prompt_out.write_text(blob, encoding="utf-8")
        print(f"Wrote prompt dump: {prompt_out} ({len(blob):,} chars)")
    if dry_run:
        run_meta["wall_seconds"] = time.perf_counter() - t0
        return None, run_meta

    out = output_path(pr_id)
    raw_backup = out.with_suffix(".raw.txt")
    errors: list[str] = []
    last_raw = ""
    last_usage: dict[str, Any] = {}

    for attempt in range(1, ANALYSIS_ATTEMPTS + 1):
        if attempt > 1:
            print(f"  Retry attempt {attempt}/{ANALYSIS_ATTEMPTS} …", flush=True)
            time.sleep(5)
        else:
            print(f"Calling DeepSeek ({model}) for pr_id={pr_id} …", flush=True)
        try:
            raw, usage = call_deepseek(messages, model=model)
            last_raw = raw if raw is not None else ""
            last_usage = usage or {}
            parsed = parse_assistant_json(last_raw)
            if int(parsed.get("pr_id", 0)) != pr_id:
                raise ValueError(f"pr_id mismatch: expected {pr_id}, got {parsed.get('pr_id')}")
            out.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
            cost = estimate_cost_usd(last_usage, model=model)
            remove_from_failure_list(pr_id)
            run_meta.update(
                {
                    "ok": True,
                    "attempts": attempt,
                    "usage": last_usage,
                    "cost": cost,
                    "wall_seconds": time.perf_counter() - t0,
                    "output": str(out),
                }
            )
            meta_path = out.parent / f"{pr_id}_analysis_run.json"
            meta_path.write_text(
                json.dumps(
                    {"usage": last_usage, "cost": cost, "model": model, "output": str(out), "attempts": attempt},
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(f"Wrote {out}")
            if last_usage:
                print(
                    f"  tokens: prompt={last_usage.get('prompt_tokens')} "
                    f"completion={last_usage.get('completion_tokens')} "
                    f"cache_hit={cost['cached_prompt_tokens']} "
                    f"~${cost['total_usd']:.4f} "
                    f"({run_meta['wall_seconds']:.1f}s)",
                    flush=True,
                )
            return out, run_meta
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            errors.append(msg)
            raw_backup.write_text(last_raw, encoding="utf-8")
            print(f"  attempt {attempt} failed: {msg}", flush=True)

    run_meta.update(
        {
            "ok": False,
            "attempts": ANALYSIS_ATTEMPTS,
            "errors": errors,
            "error": errors[-1] if errors else "unknown",
            "wall_seconds": time.perf_counter() - t0,
            "raw_path": str(raw_backup),
        }
    )
    append_failure_record(
        {
            "pr_id": pr_id,
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "attempts": ANALYSIS_ATTEMPTS,
            "errors": errors,
            "error_summary": errors[-1] if errors else "unknown",
            "raw_path": str(raw_backup),
        }
    )
    print(f"  FAILED after {ANALYSIS_ATTEMPTS} attempts; logged to {FAILURE_LIST_JSON}", flush=True)
    return None, run_meta


def pick_batch_pr_ids(count: int, *, skip_analyzed: bool = True) -> list[int]:
    master = pd.read_csv(MASTER_CSV)
    skip = set(FEWSHOT_PR_IDS) | failed_pr_ids()
    picked: list[int] = []
    for pid in master["id"].astype(int):
        if pid in skip:
            continue
        if skip_analyzed and output_path(pid).exists():
            continue
        picked.append(pid)
        if len(picked) >= count:
            break
    return picked


def _empty_cumulative() -> dict[str, Any]:
    return {
        "requested": 0,
        "succeeded": 0,
        "failed": 0,
        "total_wall_seconds": 0.0,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "total_cost_cny_approx": 0.0,
        "prompt_tokens_sum": 0,
        "cached_prompt_tokens_sum": 0,
        "cache_hit_rate_of_prompt": 0.0,
    }


def load_cumulative_report(report_path: Path) -> dict[str, Any]:
    if not report_path.exists():
        return {"batch_count": 0, "runs": [], "cumulative": _empty_cumulative(), "model": DEFAULT_MODEL}
    data = json.loads(report_path.read_text(encoding="utf-8"))
    if "cumulative" in data and "runs" in data:
        return data
    # Migrate single-batch legacy format
    runs = data.get("runs", [])
    cum = _empty_cumulative()
    cum["requested"] = int(data.get("requested", len(runs)))
    cum["succeeded"] = int(data.get("succeeded", sum(1 for r in runs if r.get("ok"))))
    cum["failed"] = int(data.get("failed", cum["requested"] - cum["succeeded"]))
    cum["total_wall_seconds"] = float(data.get("total_wall_seconds", 0))
    cum["total_tokens"] = int(data.get("total_tokens", 0))
    cum["total_cost_usd"] = float(data.get("total_cost_usd", 0))
    cum["total_cost_cny_approx"] = float(data.get("total_cost_cny_approx", cum["total_cost_usd"] * 7.2))
    cum["prompt_tokens_sum"] = int(data.get("prompt_tokens_sum", 0))
    cum["cached_prompt_tokens_sum"] = int(data.get("cached_prompt_tokens_sum", 0))
    cum["cache_hit_rate_of_prompt"] = float(data.get("cache_hit_rate_of_prompt", 0))
    return {
        "model": data.get("model", DEFAULT_MODEL),
        "batch_count": 1,
        "cumulative": cum,
        "runs": runs,
    }


def _batch_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok_rows = [r for r in rows if r.get("ok")]
    total_usd = sum(r.get("cost", {}).get("total_usd", 0) for r in ok_rows)
    total_tokens = sum(int(r.get("usage", {}).get("total_tokens", 0)) for r in ok_rows)
    cached_sum = sum(int(r.get("cost", {}).get("cached_prompt_tokens", 0)) for r in ok_rows)
    prompt_sum = sum(int(r.get("usage", {}).get("prompt_tokens", 0)) for r in ok_rows)
    wall = sum(float(r.get("wall_seconds", 0)) for r in ok_rows)
    return {
        "requested": len(rows),
        "succeeded": len(ok_rows),
        "failed": len(rows) - len(ok_rows),
        "total_wall_seconds": wall,
        "avg_wall_seconds_per_ok": (wall / len(ok_rows)) if ok_rows else None,
        "total_tokens": total_tokens,
        "total_cost_usd": total_usd,
        "total_cost_cny_approx": total_usd * 7.2,
        "prompt_tokens_sum": prompt_sum,
        "cached_prompt_tokens_sum": cached_sum,
        "cache_hit_rate_of_prompt": (cached_sum / prompt_sum) if prompt_sum else 0.0,
    }


def _merge_cumulative(cum: dict[str, Any], batch: dict[str, Any]) -> None:
    cum["requested"] += batch["requested"]
    cum["succeeded"] += batch["succeeded"]
    cum["failed"] += batch["failed"]
    cum["total_wall_seconds"] += batch["total_wall_seconds"]
    cum["total_tokens"] += batch["total_tokens"]
    cum["total_cost_usd"] += batch["total_cost_usd"]
    cum["total_cost_cny_approx"] += batch["total_cost_cny_approx"]
    cum["prompt_tokens_sum"] += batch["prompt_tokens_sum"]
    cum["cached_prompt_tokens_sum"] += batch["cached_prompt_tokens_sum"]
    if cum["prompt_tokens_sum"]:
        cum["cache_hit_rate_of_prompt"] = cum["cached_prompt_tokens_sum"] / cum["prompt_tokens_sum"]
    else:
        cum["cache_hit_rate_of_prompt"] = 0.0


def format_run_md_line(r: dict[str, Any]) -> str:
    if r.get("ok"):
        c = r["cost"]
        batch_tag = f" batch={r['batch_index']}" if r.get("batch_index") else ""
        return (
            f"- {r['pr_id']}: {r['wall_seconds']:.1f}s, "
            f"tokens={r['usage'].get('total_tokens')}, "
            f"cache_hit={c['cached_prompt_tokens']}, "
            f"${c['total_usd']:.4f}{batch_tag}"
        )
    return f"- {r['pr_id']}: FAILED — {r.get('error')}"


def write_batch_reports(
    report_path: Path,
    md_path: Path,
    *,
    model: str,
    state: dict[str, Any],
    last_batch: dict[str, Any],
) -> None:
    cum = state["cumulative"]
    avg_ok = (
        cum["total_wall_seconds"] / cum["succeeded"] if cum["succeeded"] else 0.0
    )
    lines = [
        "# PR analysis batch report",
        "",
        f"- Model: `{state.get('model', model)}`",
        f"- Batch runs (cumulative): **{state['batch_count']}**",
        f"- Last batch at: {last_batch.get('finished_at', '—')}",
        "",
        "## Cumulative totals",
        "",
        f"- PRs requested: **{cum['requested']}**",
        f"- Succeeded: **{cum['succeeded']}** / Failed: **{cum['failed']}**",
        f"- Wall time: **{cum['total_wall_seconds']:.1f}s** (avg **{avg_ok:.1f}s**/ok PR)",
        f"- Total tokens: **{cum['total_tokens']:,}**",
        f"- Prompt cache hit rate: **{100 * cum['cache_hit_rate_of_prompt']:.1f}%** "
        f"({cum['cached_prompt_tokens_sum']:,} / {cum['prompt_tokens_sum']:,} prompt tokens)",
        f"- Est. cost: **${cum['total_cost_usd']:.3f}** (~CNY **{cum['total_cost_cny_approx']:.2f}**)",
        "",
        "## Last batch",
        "",
        f"- Requested: {last_batch['requested']} | "
        f"Succeeded: {last_batch['succeeded']} | Failed: {last_batch['failed']}",
        f"- Wall: {last_batch.get('elapsed_seconds', last_batch['total_wall_seconds']):.1f}s "
        f"(sum per-PR {last_batch['total_wall_seconds']:.1f}s) | "
        f"Tokens: {last_batch['total_tokens']:,} | "
        f"Cost: ${last_batch['total_cost_usd']:.3f}",
        "",
        "## Per PR",
        "",
    ]
    for r in state["runs"]:
        lines.append(format_run_md_line(r))
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    out = {
        "model": state.get("model", model),
        "batch_count": state["batch_count"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "cumulative": cum,
        "last_batch": last_batch,
        "runs": state["runs"],
    }
    report_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


def run_batch(
    pr_ids: list[int],
    *,
    model: str = DEFAULT_MODEL,
    save_prompt: bool = False,
    report_path: Path | None = None,
) -> dict[str, Any]:
    report_path = report_path or OUT_ANALYSIS / "batch_run_report.json"
    md_path = OUT_ANALYSIS / "batch_run_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    state = load_cumulative_report(report_path)
    state["model"] = model

    rows: list[dict[str, Any]] = []
    t_batch = time.perf_counter()
    batch_index = state["batch_count"] + 1
    for i, pr_id in enumerate(pr_ids, 1):
        print(f"\n=== [{i}/{len(pr_ids)}] pr_id={pr_id} ===", flush=True)
        _, meta = run_analysis(pr_id, model=model, save_prompt=save_prompt)
        meta["batch_index"] = batch_index
        rows.append(meta)
        if not meta.get("ok"):
            print(f"  FAILED: {meta.get('error')}", flush=True)

    batch_wall = time.perf_counter() - t_batch
    last_batch = _batch_stats(rows)
    last_batch["elapsed_seconds"] = batch_wall
    last_batch["finished_at"] = datetime.now(timezone.utc).isoformat()
    last_batch["batch_index"] = batch_index

    _merge_cumulative(state["cumulative"], last_batch)
    state["runs"].extend(rows)
    state["batch_count"] = batch_index

    write_batch_reports(report_path, md_path, model=model, state=state, last_batch=last_batch)

    cum = state["cumulative"]
    print(f"\nBatch done. Report: {report_path}")
    print(f"  this batch: {last_batch['succeeded']}/{last_batch['requested']} ok, "
          f"USD {last_batch['total_cost_usd']:.3f}, {last_batch['total_wall_seconds']:.1f}s")
    print(f"  cumulative: {cum['succeeded']} ok PRs, cache hit "
          f"{100 * cum['cache_hit_rate_of_prompt']:.1f}%, "
          f"USD {cum['total_cost_usd']:.3f}, wall {cum['total_wall_seconds']:.1f}s")
    return {"cumulative": cum, "last_batch": last_batch, "runs_this_batch": rows}


def main() -> None:
    p = argparse.ArgumentParser(description="Run LLM PR analysis workflow.")
    p.add_argument("--pr-id", type=int, help="Single PR id")
    p.add_argument("--batch", type=int, metavar="N", help="Run N PRs (skip few-shot + existing outputs)")
    p.add_argument("--pr-ids", type=str, help="Comma-separated PR ids for batch")
    p.add_argument("--dry-run", action="store_true", help="Build prompt only, no API call")
    p.add_argument("--save-prompt", action="store_true", help="Also write {pr_id}_workflow_prompt.txt")
    p.add_argument("--model", default=DEFAULT_MODEL)
    args = p.parse_args()

    if args.batch or args.pr_ids:
        if args.pr_ids:
            ids = [int(x.strip()) for x in args.pr_ids.split(",") if x.strip()]
        else:
            ids = pick_batch_pr_ids(args.batch or 10)
        if not ids:
            raise SystemExit("No PR ids to run.")
        if args.dry_run:
            raise SystemExit("--dry-run with batch not supported; use --pr-id --dry-run")
        run_batch(ids, model=args.model, save_prompt=args.save_prompt)
        return

    if not args.pr_id:
        raise SystemExit("Provide --pr-id or --batch N")
    _, meta = run_analysis(args.pr_id, dry_run=args.dry_run, model=args.model, save_prompt=args.save_prompt)
    if not args.dry_run and not meta.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
