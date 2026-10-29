"""Continue phase-2 labels during DeepSeek off-peak hours only.

Off-peak is half price. Beijing time, Monday–Friday 09:00–12:00 and
14:00–18:00 are peak. Weekends are off-peak all day. Chinese statutory
holidays below are off-peak all day. Thinking is disabled: a reasoning
trace is billed as output and would spend the balance on chain-of-thought
instead of labels.

The run stops at the next peak boundary, when the topped-up balance is
almost gone, or on HTTP 402. A lock keeps two schedules from calling at once.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

PHASE = Path(__file__).resolve().parents[1]
ROOT = PHASE.parent
DATA = PHASE / "data"
SOURCE = DATA / "prs_with_perf_tests.csv"
CACHE = DATA / "pr_texts_cache.jsonl"
LABELS = DATA / "llm_labels.jsonl"
SUMMARY = DATA / "llm_summary.json"
OUT_CSV = DATA / "prs_performance_and_tests.csv"
STATE = DATA / "offpeak_state.json"
LOG = DATA / "offpeak.log"
LOCK = DATA / "offpeak.lock"
KEY_PATH = ROOT / ".deepseekToken"

MODEL = "deepseek-flash"
BUDGET_CNY = 20.0
STOP_BALANCE_CNY = 0.03
WORKERS = 6
BODY_LIMIT = 2500
PEAK_BUFFER = timedelta(minutes=2)
CST = timezone(timedelta(hours=8))
TASK_NAME = "MyStudy-Phase2-Offpeak"

# Flash off-peak, yuan per token. Peak is exactly double; this script never calls then.
PRICE_HIT = 0.02 / 1_000_000
PRICE_MISS = 1.0 / 1_000_000
PRICE_OUT = 4.0 / 1_000_000

# 2026 State Council holidays. Weekends are already off-peak, including make-up weekends.
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


class PaymentRequired(RuntimeError):
    pass


class FatalAPI(RuntimeError):
    pass


def now_cst() -> datetime:
    return datetime.now(CST)


def is_peak(moment: datetime) -> bool:
    local = moment.astimezone(CST)
    if local.weekday() >= 5 or local.date() in HOLIDAYS:
        return False
    minutes = local.hour * 60 + local.minute
    return (9 * 60 <= minutes < 12 * 60) or (14 * 60 <= minutes < 18 * 60)


def next_peak(moment: datetime) -> datetime | None:
    local = moment.astimezone(CST).replace(second=0, microsecond=0)
    for step in range(1, 16 * 24 * 60):
        candidate = local + timedelta(minutes=step)
        previous = candidate - timedelta(minutes=1)
        if is_peak(candidate) and not is_peak(previous):
            return candidate
    return None


def log(message: str) -> None:
    line = f"{now_cst().isoformat(timespec='seconds')} {message}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def verdict_of(text: str) -> str | None:
    word = (text or "").strip().lower().split(" ", 1)[0].strip(".,:;\"'")
    if word.startswith("non-performance") or word.startswith("nonperformance"):
        return "non-performance"
    if word.startswith("performance"):
        return "performance"
    return None


def load_key() -> str:
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


def load_state() -> dict:
    if not STATE.exists():
        return {}
    return json.loads(STATE.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def done_ids() -> set[int]:
    found = set()
    if not LABELS.exists():
        return found
    with LABELS.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("verdict") in {"performance", "non-performance"}:
                found.add(int(item["pr_id"]))
    return found


def load_rows() -> list[dict]:
    if not CACHE.exists():
        raise SystemExit(f"missing {CACHE.name}; run with --build-cache first")
    rows = []
    with CACHE.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def build_cache() -> None:
    from classify_performance_purpose import load_texts

    rows = load_texts()
    with CACHE.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    log(f"cached {len(rows)} PR texts -> {CACHE.name}")


def cost_of(usage: dict) -> tuple[float, int]:
    hit = int(usage.get("prompt_cache_hit_tokens") or 0)
    miss = int(usage.get("prompt_cache_miss_tokens") or 0)
    if hit == 0 and miss == 0:
        miss = int(usage.get("prompt_tokens") or 0)
    completion = int(usage.get("completion_tokens") or 0)
    reasoning = 0
    details = usage.get("completion_tokens_details") or {}
    if isinstance(details, dict):
        reasoning = int(details.get("reasoning_tokens") or 0)
    cost = hit * PRICE_HIT + miss * PRICE_MISS + completion * PRICE_OUT
    return cost, reasoning


def classify_one(key: str, row: dict) -> dict:
    if not row.get("text"):
        return {"pr_id": row["pr_id"], "verdict": "non-performance", "raw": "", "model": MODEL, "billed": False}
    payload = {
        "model": MODEL,
        "temperature": 0,
        "max_tokens": 16,
        "thinking": {"type": "disabled"},
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": row["text"]},
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
            cost, reasoning_tokens = cost_of(usage)
            if reasoning or reasoning_tokens:
                raise FatalAPI(
                    f"thinking was billed (reasoning_tokens={reasoning_tokens}); stopped before spending further"
                )
            verdict = verdict_of(raw)
            if verdict is None:
                last_error = raw
                time.sleep(1)
                continue
            return {
                "pr_id": row["pr_id"],
                "verdict": verdict,
                "raw": raw,
                "model": MODEL,
                "usage": usage,
                "cost_cny": round(cost, 8),
                "billed": True,
            }
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            if exc.code == 402:
                raise PaymentRequired("DeepSeek returned 402") from exc
            if exc.code == 400:
                raise FatalAPI(f"HTTP 400 {body}") from exc
            last_error = f"http {exc.code} {body}"
            time.sleep(2 + attempt * 3)
        except FatalAPI:
            raise
        except Exception as exc:  # noqa: BLE001
            last_error = type(exc).__name__
            time.sleep(1 + attempt)
    return {"pr_id": row["pr_id"], "verdict": "error", "raw": last_error, "model": MODEL, "billed": False}


def write_outputs(rows: list[dict], state: dict) -> None:
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
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["pr_id", "number", "outcome", "agent", "repo", "html_url", "title", "perf_files"],
        )
        writer.writeheader()
        for row in kept:
            writer.writerow({key: row[key] for key in writer.fieldnames})
    counts = Counter(labels.values())
    summary = {
        "input_prs_with_perf_tests": len(rows),
        "labeled_success": len(labels),
        "verdicts": dict(counts),
        "performance_purpose": counts.get("performance", 0),
        "model": MODEL,
        "thinking": "disabled",
        "budget_cny": state.get("budget_cny"),
        "start_balance_cny": state.get("start_balance_cny"),
        "csv": OUT_CSV.name,
        "prompt": "AIDevPerf filter.py primary-purpose performance classifier",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")


class FileLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle = None

    def acquire(self) -> bool:
        self.handle = self.path.open("a+")
        if self.handle.seek(0, os.SEEK_END) == 0:
            self.handle.write(" ")
            self.handle.flush()
        try:
            if os.name == "nt":
                import msvcrt

                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.handle.close()
            self.handle = None
            return False
        return True

    def release(self) -> None:
        if self.handle is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None


def disable_local_task() -> None:
    if os.name != "nt":
        return
    import subprocess

    subprocess.run(
        ["schtasks", "/Change", "/TN", TASK_NAME, "/DISABLE"],
        check=False,
        capture_output=True,
        text=True,
    )


def status_line(key: str | None) -> None:
    moment = now_cst()
    peak = is_peak(moment)
    boundary = next_peak(moment)
    log(f"beijing={moment.isoformat(timespec='minutes')} peak={peak} next_peak_boundary={boundary}")
    if key is None:
        return
    try:
        log(f"balance_cny={balance_cny(key):.4f}")
    except Exception as exc:  # noqa: BLE001
        log(f"balance_check_failed {type(exc).__name__}")


def run() -> None:
    moment = now_cst()
    if is_peak(moment):
        nxt = None
        local = moment.astimezone(CST)
        # next off-peak start is the end of this peak block
        if local.hour < 12:
            nxt = local.replace(hour=12, minute=0, second=0, microsecond=0)
        elif local.hour < 18:
            nxt = local.replace(hour=18, minute=0, second=0, microsecond=0)
        log(f"peak window, not calling the API; next off-peak {nxt}")
        return
    deadline = next_peak(moment)
    if deadline is not None and deadline - moment <= PEAK_BUFFER:
        log(f"inside the {PEAK_BUFFER} buffer before peak at {deadline}, not starting")
        return

    lock = FileLock(LOCK)
    if not lock.acquire():
        log("another off-peak run is already holding the lock")
        return
    try:
        key = load_key()
        state = load_state()
        current = balance_cny(key)
        if "start_balance_cny" not in state:
            state = {
                "start_balance_cny": current,
                "budget_cny": min(BUDGET_CNY, current),
                "started_at": moment.isoformat(timespec="seconds"),
                "model": MODEL,
                "thinking": "disabled",
                "calls": 0,
                "estimated_cost_cny": 0.0,
            }
            save_state(state)
            log(f"snapshot balance={current:.4f} budget={state['budget_cny']:.4f}")
        spent = float(state["start_balance_cny"]) - current
        if current <= STOP_BALANCE_CNY or spent >= float(state["budget_cny"]):
            log(f"budget exhausted balance={current:.4f} spent={spent:.4f}")
            disable_local_task()
            return

        rows = load_rows()
        finished = done_ids()
        pending = [row for row in rows if int(row["pr_id"]) not in finished]
        log(
            f"rows={len(rows)} done={len(finished)} pending={len(pending)} "
            f"balance={current:.4f} deadline={deadline}"
        )
        if not pending:
            log("nothing left to label")
            disable_local_task()
            return

        classified = 0
        new_performance = 0
        estimated = float(state.get("estimated_cost_cny") or 0)
        stopped = "finished"
        with LABELS.open("a", encoding="utf-8") as handle:
            with ThreadPoolExecutor(max_workers=WORKERS) as pool:
                index = 0
                while index < len(pending):
                    moment = now_cst()
                    if deadline is not None and moment >= deadline - PEAK_BUFFER:
                        stopped = "window"
                        break
                    if is_peak(moment):
                        stopped = "peak"
                        break
                    batch = pending[index : index + WORKERS]
                    index += len(batch)
                    futures = [pool.submit(classify_one, key, row) for row in batch]
                    halt = False
                    try:
                        for future in as_completed(futures):
                            item = future.result()
                            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
                            handle.flush()
                            classified += 1
                            if item.get("verdict") == "performance":
                                new_performance += 1
                            estimated += float(item.get("cost_cny") or 0)
                    except PaymentRequired:
                        stopped = "402"
                        halt = True
                    except FatalAPI as exc:
                        stopped = str(exc)
                        halt = True
                    if halt:
                        break
                    if classified % 60 == 0:
                        current = balance_cny(key)
                        spent = float(state["start_balance_cny"]) - current
                        log(
                            f"classified {classified} new_performance={new_performance} "
                            f"balance={current:.4f} spent={spent:.4f} estimated={estimated:.4f}"
                        )
                        if current <= STOP_BALANCE_CNY or spent >= float(state["budget_cny"]):
                            stopped = "budget"
                            break
        current = balance_cny(key)
        spent = float(state["start_balance_cny"]) - current
        state["calls"] = int(state.get("calls") or 0) + classified
        state["estimated_cost_cny"] = round(estimated, 6)
        state["last_balance_cny"] = current
        state["last_stop"] = stopped
        state["updated_at"] = now_cst().isoformat(timespec="seconds")
        save_state(state)
        write_outputs(rows, state)
        log(
            f"stop={stopped} classified_now={classified} new_performance={new_performance} "
            f"balance={current:.4f} spent={spent:.4f}"
        )
        if current <= STOP_BALANCE_CNY or spent >= float(state["budget_cny"]) or stopped == "402":
            disable_local_task()
    finally:
        lock.release()


def main() -> None:
    if "--build-cache" in sys.argv:
        build_cache()
        return
    if "--status" in sys.argv:
        key = load_key() if KEY_PATH.exists() else None
        status_line(key)
        if CACHE.exists():
            done = done_ids()
            total = sum(1 for line in CACHE.open(encoding="utf-8") if line.strip())
            log(f"cache={total} labeled={len(done)} pending={total - len(done)}")
        else:
            log("cache missing")
        return
    run()


if __name__ == "__main__":
    main()
