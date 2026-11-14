"""DeepSeek 0/1 re-inspection for the 100-PR machine sample.

Assembles title + body for each PR in sample_deepseek_100.csv and asks the
model to reply with exactly 0 or 1:

  0 = not a performance-related / performance-primary PR
  1 = performance is the primary purpose of the PR

By default the script refuses to call the API during Beijing peak hours
(Mon–Fri 09:00–12:00 and 14:00–18:00). Pass --force only if you deliberately
want to spend at peak rates. Prefer --status / --dry-run first.

Outputs (under ../deepseek_recheck/):
  deepseek_recheck_labels.jsonl   one JSON object per finished PR (append-safe)
  deepseek_recheck_results.csv    merged sample + recheck columns
  deepseek_recheck_summary.json   counts and agreement vs original_verdict
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
PHASE = BASE.parent
ROOT = PHASE.parent
SAMPLES = BASE / "samples"
OUT = BASE / "deepseek_recheck"
SAMPLE_CSV = SAMPLES / "sample_deepseek_100.csv"
CACHE = PHASE / "data" / "pr_texts_cache.jsonl"
KEY_PATH = ROOT / ".deepseekToken"

LABELS_JSONL = OUT / "deepseek_recheck_labels.jsonl"
RESULTS_CSV = OUT / "deepseek_recheck_results.csv"
SUMMARY_JSON = OUT / "deepseek_recheck_summary.json"
LOG = OUT / "deepseek_recheck.log"

MODEL = "deepseek-flash"
BODY_LIMIT = 2500
CST = timezone(timedelta(hours=8))

# Same peak window as phase2/scripts/run_offpeak_classify.py
HOLIDAYS = {
    datetime(2026, 1, 1).date(),
    datetime(2026, 1, 2).date(),
    datetime(2026, 1, 3).date(),
    datetime(2026, 2, 15).date(),
    datetime(2026, 2, 16).date(),
    datetime(2026, 2, 17).date(),
    datetime(2026, 2, 18).date(),
    datetime(2026, 2, 19).date(),
    datetime(2026, 2, 20).date(),
    datetime(2026, 2, 21).date(),
    datetime(2026, 2, 22).date(),
    datetime(2026, 2, 23).date(),
    datetime(2026, 4, 4).date(),
    datetime(2026, 4, 5).date(),
    datetime(2026, 4, 6).date(),
    datetime(2026, 5, 1).date(),
    datetime(2026, 5, 2).date(),
    datetime(2026, 5, 3).date(),
    datetime(2026, 5, 4).date(),
    datetime(2026, 5, 5).date(),
    datetime(2026, 6, 19).date(),
    datetime(2026, 6, 20).date(),
    datetime(2026, 6, 21).date(),
    datetime(2026, 9, 25).date(),
    datetime(2026, 9, 26).date(),
    datetime(2026, 9, 27).date(),
    datetime(2026, 10, 1).date(),
    datetime(2026, 10, 2).date(),
    datetime(2026, 10, 3).date(),
    datetime(2026, 10, 4).date(),
    datetime(2026, 10, 5).date(),
    datetime(2026, 10, 6).date(),
    datetime(2026, 10, 7).date(),
}

SYSTEM_PROMPT = (
    "You are a GitHub Pull Request Classification Agent. "
    "Given a text combining the title and body of a pull request, decide whether "
    "the primary purpose of the pull request is to improve performance. "
    "Performance-related pull requests may contain keywords such as performance, "
    "compile-time-hog, perf, hang, optimization, responsive, slow, speed, latency, "
    "throughput, wait, fast, lag, stuck, instant, memory, leak, or any other terms "
    "referring to how faster and efficiently software runs. "
    "Reply with exactly one character: 1 if the primary purpose is performance, "
    "or 0 if it is not."
)


def now_cst() -> datetime:
    return datetime.now(CST)


def is_peak(moment: datetime) -> bool:
    local = moment.astimezone(CST)
    if local.weekday() >= 5 or local.date() in HOLIDAYS:
        return False
    minutes = local.hour * 60 + local.minute
    return (9 * 60 <= minutes < 12 * 60) or (14 * 60 <= minutes < 18 * 60)


def ensure_out_dir() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def log(message: str) -> None:
    line = f"{now_cst().isoformat(timespec='seconds')} {message}"
    print(line, flush=True)
    ensure_out_dir()
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def load_key() -> str:
    if not KEY_PATH.exists():
        raise SystemExit(f"missing API token file: {KEY_PATH}")
    return KEY_PATH.read_text(encoding="utf-8").strip()


def api_json(key: str, method: str, url: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode())


def balance_cny(key: str) -> float:
    data = api_json(key, "GET", "https://api.deepseek.com/user/balance")
    for item in data.get("balance_infos") or []:
        if item.get("currency") == "CNY":
            return float(item["total_balance"])
    raise RuntimeError(f"no CNY balance in {data}")


def parse_label(raw: str) -> int | None:
    text = (raw or "").strip()
    if not text:
        return None
    # Take first token; allow "1", "0", "1.", "label: 0", etc.
    token = text.replace("\n", " ").split()[0].strip(".,:;\"'`()[]{}")
    if token in {"0", "1"}:
        return int(token)
    if token.lower() in {"performance", "yes", "true"}:
        return 1
    if token.lower() in {"non-performance", "nonperformance", "no", "false"}:
        return 0
    return None


def load_sample() -> list[dict]:
    with SAMPLE_CSV.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_texts() -> dict[int, str]:
    texts: dict[int, str] = {}
    if not CACHE.exists():
        return texts
    with CACHE.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            pr_id = int(item["pr_id"])
            text = (item.get("text") or "").strip()
            if text:
                texts[pr_id] = text
    return texts


def assemble_text(row: dict, texts: dict[int, str]) -> str:
    pr_id = int(row["pr_id"])
    if pr_id in texts:
        text = texts[pr_id]
    else:
        title = row.get("title") or ""
        body = row.get("body_preview") or ""
        text = f"{title}\n{body}".strip()
    if len(text) > BODY_LIMIT + 200:
        # Keep title; truncate body side of combined text.
        lines = text.split("\n", 1)
        title = lines[0]
        body = lines[1] if len(lines) > 1 else ""
        if len(body) > BODY_LIMIT:
            body = body[:BODY_LIMIT]
        text = f"{title}\n{body}".strip()
    return text


def done_labels() -> dict[int, dict]:
    found: dict[int, dict] = {}
    if not LABELS_JSONL.exists():
        return found
    with LABELS_JSONL.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("label") in {0, 1}:
                found[int(item["pr_id"])] = item
    return found


def classify_one(key: str, pr_id: int, text: str) -> dict:
    payload = {
        "model": MODEL,
        "temperature": 0,
        "max_tokens": 8,
        "thinking": {"type": "disabled"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    }
    last_error = ""
    for attempt in range(4):
        try:
            data = api_json(key, "POST", "https://api.deepseek.com/chat/completions", payload)
            message = data["choices"][0]["message"]
            raw = message.get("content") or ""
            reasoning = message.get("reasoning_content") or ""
            usage = data.get("usage") or {}
            details = usage.get("completion_tokens_details") or {}
            reasoning_tokens = int(details.get("reasoning_tokens") or 0) if isinstance(details, dict) else 0
            if reasoning or reasoning_tokens:
                raise RuntimeError(
                    f"thinking was billed (reasoning_tokens={reasoning_tokens}); refusing to continue"
                )
            label = parse_label(raw)
            if label is None:
                last_error = raw
                time.sleep(1)
                continue
            return {
                "pr_id": pr_id,
                "label": label,
                "raw": raw.strip(),
                "model": MODEL,
                "usage": usage,
                "billed": True,
                "at": now_cst().isoformat(timespec="seconds"),
            }
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            if exc.code == 402:
                raise RuntimeError("DeepSeek returned 402 Payment Required") from exc
            last_error = f"http {exc.code} {body}"
            time.sleep(2 + attempt * 3)
        except Exception as exc:  # noqa: BLE001
            if "thinking was billed" in str(exc):
                raise
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(1 + attempt)
    return {
        "pr_id": pr_id,
        "label": None,
        "raw": last_error,
        "model": MODEL,
        "billed": False,
        "at": now_cst().isoformat(timespec="seconds"),
        "error": True,
    }


def write_results(sample: list[dict], labels: dict[int, dict]) -> dict:
    ensure_out_dir()
    fieldnames = list(sample[0].keys())
    for extra in ("recheck_label", "recheck_raw", "recheck_model", "recheck_at", "agree_with_original"):
        if extra not in fieldnames:
            fieldnames.append(extra)

    rows_out = []
    agree = 0
    labeled = 0
    for row in sample:
        pr_id = int(row["pr_id"])
        item = labels.get(pr_id)
        out = dict(row)
        if item and item.get("label") in {0, 1}:
            labeled += 1
            label = int(item["label"])
            out["recheck_label"] = label
            out["recheck_verdict"] = "performance" if label == 1 else "non-performance"
            out["recheck_raw"] = item.get("raw", "")
            out["recheck_model"] = item.get("model", MODEL)
            out["recheck_by"] = "deepseek-recheck"
            out["recheck_at"] = item.get("at", "")
            original = (row.get("original_verdict") or "").strip()
            # Original sample is drawn from performance-purpose set.
            expected_one = 1 if original == "performance" else (0 if original == "non-performance" else None)
            if expected_one is None:
                out["agree_with_original"] = ""
            else:
                same = int(label == expected_one)
                out["agree_with_original"] = same
                agree += same
        else:
            out.setdefault("recheck_label", "")
            out.setdefault("agree_with_original", "")
        rows_out.append(out)

    with RESULTS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows_out)

    label_counts = Counter(
        int(labels[pid]["label"]) for pid in labels if labels[pid].get("label") in {0, 1}
    )
    summary = {
        "sample_csv": str(SAMPLE_CSV.relative_to(ROOT)).replace("\\", "/"),
        "n_sample": len(sample),
        "n_labeled": labeled,
        "n_pending": len(sample) - labeled,
        "label_counts": {"0": label_counts.get(0, 0), "1": label_counts.get(1, 0)},
        "agree_with_original": agree,
        "agreement_rate": round(agree / labeled, 4) if labeled else None,
        "model": MODEL,
        "prompt_reply_format": "0_or_1",
        "results_csv": RESULTS_CSV.name,
        "labels_jsonl": LABELS_JSONL.name,
        "updated_at": now_cst().isoformat(timespec="seconds"),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def cmd_status() -> int:
    sample = load_sample()
    labels = done_labels()
    peak = is_peak(now_cst())
    print(f"sample={len(sample)} labeled={len(labels)} pending={len(sample) - len(labels)}")
    print(f"peak={peak} model={MODEL}")
    print(f"sample_csv={SAMPLE_CSV}")
    print(f"labels={LABELS_JSONL}")
    if KEY_PATH.exists():
        try:
            bal = balance_cny(load_key())
            print(f"balance_cny={bal}")
        except Exception as exc:  # noqa: BLE001
            print(f"balance_error={exc}")
    else:
        print(f"token_missing={KEY_PATH}")
    if RESULTS_CSV.exists():
        print(f"results_csv_exists={RESULTS_CSV.name}")
    return 0


def cmd_dry_run() -> int:
    sample = load_sample()
    texts = load_texts()
    labels = done_labels()
    pending = [row for row in sample if int(row["pr_id"]) not in labels]
    print(f"would_classify={len(pending)} already_done={len(labels)}")
    for row in pending[:3]:
        text = assemble_text(row, texts)
        print("---")
        print(f"pr_id={row['pr_id']} repo={row['repo']} #{row['number']}")
        print(text[:400].replace("\n", " | "))
        print(f"... chars={len(text)}")
    return 0


def cmd_run(*, force: bool) -> int:
    moment = now_cst()
    if is_peak(moment) and not force:
        log("peak hours; refusing to call API (pass --force to override)")
        return 2
    if force and is_peak(moment):
        log("WARNING: --force during peak hours; calls will be billed at peak rates")

    key = load_key()
    sample = load_sample()
    texts = load_texts()
    labels = done_labels()
    pending = [row for row in sample if int(row["pr_id"]) not in labels]
    log(f"start recheck pending={len(pending)} done={len(labels)} balance={balance_cny(key):.4f}")

    for row in pending:
        if is_peak(now_cst()) and not force:
            log("entered peak during run; stopping")
            break
        pr_id = int(row["pr_id"])
        text = assemble_text(row, texts)
        if not text:
            item = {
                "pr_id": pr_id,
                "label": 0,
                "raw": "",
                "model": MODEL,
                "billed": False,
                "at": now_cst().isoformat(timespec="seconds"),
                "note": "empty_text",
            }
        else:
            item = classify_one(key, pr_id, text)
        with LABELS_JSONL.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        if item.get("label") in {0, 1}:
            labels[pr_id] = item
            log(f"ok pr_id={pr_id} label={item['label']} raw={item.get('raw')!r}")
        else:
            log(f"fail pr_id={pr_id} raw={item.get('raw')!r}")
        time.sleep(0.15)

    summary = write_results(sample, labels)
    log(
        "done "
        f"labeled={summary['n_labeled']} "
        f"pending={summary['n_pending']} "
        f"label_counts={summary['label_counts']} "
        f"agree={summary['agree_with_original']}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DeepSeek 0/1 re-inspection for sample_deepseek_100.csv")
    parser.add_argument("--status", action="store_true", help="show progress and balance; no chat calls")
    parser.add_argument("--dry-run", action="store_true", help="show a few assembled prompts; no API calls")
    parser.add_argument(
        "--force",
        action="store_true",
        help="allow API calls even during Beijing peak hours",
    )
    parser.add_argument(
        "--write-results-only",
        action="store_true",
        help="rebuild CSV/summary from existing jsonl; no API calls",
    )
    args = parser.parse_args(argv)

    if args.status:
        return cmd_status()
    if args.dry_run:
        return cmd_dry_run()
    if args.write_results_only:
        summary = write_results(load_sample(), done_labels())
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    return cmd_run(force=args.force)


if __name__ == "__main__":
    sys.exit(main())
