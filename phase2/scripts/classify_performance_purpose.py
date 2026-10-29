"""Classify phase2 PRs with the paper's performance-purpose prompt.

The detector is the LLM step in AIDevPerf/LLM-performance/filter.py:
the primary purpose of the pull request is to improve performance.
Replies are one word, performance or non-performance.
"""

from __future__ import annotations

import csv
import json
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pyarrow.parquet as pq

HF = "hf://datasets/hao-li/AIDev-7.6M/pull_request.parquet"
PHASE = Path(__file__).resolve().parents[1]
DATA = PHASE / "data"
SOURCE = DATA / "prs_with_perf_tests.csv"
LABELS = DATA / "llm_labels.jsonl"
KEY_PATH = PHASE.parent / ".deepseekToken"
WORKERS = 8
BODY_LIMIT = 2500
TARGET_PERFORMANCE = 1000
MAX_NEW_CALLS = 20000


class PaymentRequired(RuntimeError):
    pass

PROMPT = (
    "You are a GitHub Pull Request Classification Agent. Given a text combining the title and body "
    "of a pull request, determine whether the primary purpose of the pull request is to improve "
    "performance. Classify each pull request as either 'performance' or 'non-performance'. "
    "Performance-related pull requests may contain keywords such as performance, compile-time-hog, "
    "perf, hang, optimization, responsive, slow, speed, latency, throughput, wait, fast, lag, tim, "
    "minor, stuck, instant, respons, react, latenc, perform, throughput, hang, memory, leak, or any "
    "other terms referring to how faster and efficiently software runs. "
    "Reply with exactly one word: performance or non-performance."
)


def verdict_of(text: str) -> str | None:
    word = (text or "").strip().lower().split(" ", 1)[0].strip(".,:;\"'")
    if word.startswith("non-performance") or word.startswith("nonperformance"):
        return "non-performance"
    if word.startswith("performance"):
        return "performance"
    return None


def load_texts() -> list[dict]:
    wanted = {}
    with SOURCE.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            wanted[int(row["pr_id"])] = row
    table = pq.read_table(HF, columns=["id", "title", "body"])
    meta = table.to_pydict()
    rows = []
    for pr_id, title, body in zip(meta["id"], meta["title"], meta["body"]):
        if pr_id is None or int(pr_id) not in wanted:
            continue
        info = wanted[int(pr_id)]
        title = title or ""
        body = body or ""
        if len(body) > BODY_LIMIT:
            body = body[:BODY_LIMIT]
        rows.append(
            {
                "pr_id": int(pr_id),
                "number": info["number"],
                "outcome": info["outcome"],
                "agent": info["agent"],
                "repo": info["repo"],
                "html_url": info["html_url"],
                "perf_files": info["perf_files"],
                "title": title,
                "text": f"{title}\n{body}".strip(),
            }
        )
    return rows


def done_ids() -> set[int]:
    if not LABELS.exists():
        return set()
    found = set()
    with LABELS.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if item.get("verdict") in {"performance", "non-performance"}:
                    found.add(int(item["pr_id"]))
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    return found


def classify_one(key: str, row: dict) -> dict:
    if not row["text"]:
        return {"pr_id": row["pr_id"], "verdict": "non-performance", "raw": ""}
    payload = {
        "model": "deepseek-chat",
        "temperature": 0,
        "max_tokens": 8,
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": row["text"]},
        ],
    }
    request = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    last_error = ""
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode())
            raw = data["choices"][0]["message"]["content"]
            verdict = verdict_of(raw)
            if verdict is None:
                last_error = raw
                time.sleep(1)
                continue
            return {"pr_id": row["pr_id"], "verdict": verdict, "raw": raw}
        except urllib.error.HTTPError as exc:
            if exc.code == 402:
                raise PaymentRequired("DeepSeek returned 402") from exc
            last_error = f"http {exc.code}"
            time.sleep(2 + attempt * 3)
        except Exception as exc:  # noqa: BLE001
            last_error = type(exc).__name__
            time.sleep(1 + attempt)
    return {"pr_id": row["pr_id"], "verdict": "error", "raw": last_error}


def write_outputs(rows: list[dict]) -> None:
    labels: dict[int, str] = {}
    with LABELS.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            verdict = item.get("verdict")
            if verdict in {"performance", "non-performance"}:
                labels[int(item["pr_id"])] = verdict
    kept = [row for row in rows if labels.get(row["pr_id"]) == "performance"]
    out = DATA / "prs_performance_and_tests.csv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["pr_id", "number", "outcome", "agent", "repo", "html_url", "title", "perf_files"],
        )
        writer.writeheader()
        for row in kept:
            writer.writerow({key: row[key] for key in writer.fieldnames})
    from collections import Counter

    counts = Counter(labels.values())
    summary = {
        "input_prs_with_perf_tests": len(rows),
        "labeled_success": len(labels),
        "verdicts": dict(counts),
        "performance_purpose": counts.get("performance", 0),
        "stopped_at": TARGET_PERFORMANCE,
        "csv": "prs_performance_and_tests.csv",
        "prompt": "AIDevPerf filter.py primary-purpose performance classifier",
    }
    (DATA / "llm_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def performance_count() -> int:
    verdicts: dict[int, str] = {}
    if not LABELS.exists():
        return 0
    with LABELS.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            verdict = item.get("verdict")
            if verdict in {"performance", "non-performance"}:
                verdicts[int(item["pr_id"])] = verdict
    return sum(verdict == "performance" for verdict in verdicts.values())


def main() -> None:
    raise SystemExit(
        "Use phase2/scripts/run_offpeak_classify.py. "
        "deepseek-chat is retired, thinking is on by default, and this entry would ignore the half-price window."
    )
    key = KEY_PATH.read_text(encoding="utf-8").strip()
    rows = load_texts()
    finished = done_ids()
    pending = [row for row in rows if row["pr_id"] not in finished]
    found = performance_count()
    print(
        f"rows={len(rows)} done={len(finished)} pending={len(pending)} performance={found}",
        flush=True,
    )
    if found >= TARGET_PERFORMANCE:
        write_outputs(rows)
        return
    lock = threading.Lock()
    completed = 0
    stopped = "finished"
    with LABELS.open("a", encoding="utf-8") as handle:
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = [pool.submit(classify_one, key, row) for row in pending]
            try:
                for future in as_completed(futures):
                    try:
                        item = future.result()
                    except PaymentRequired as exc:
                        stopped = str(exc)
                        break
                    handle.write(json.dumps(item, ensure_ascii=False) + "\n")
                    handle.flush()
                    completed += 1
                    if item.get("verdict") == "performance":
                        found += 1
                    if completed % 200 == 0:
                        print(
                            f"classified {completed} performance={found}/{TARGET_PERFORMANCE}",
                            flush=True,
                        )
                    if found >= TARGET_PERFORMANCE or completed >= MAX_NEW_CALLS:
                        stopped = "target" if found >= TARGET_PERFORMANCE else "call_cap"
                        break
            finally:
                for future in futures:
                    future.cancel()
    print(f"stop={stopped} classified_now={completed} performance={found}", flush=True)
    write_outputs(rows)


if __name__ == "__main__":
    main()
