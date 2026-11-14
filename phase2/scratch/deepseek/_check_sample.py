import json
import urllib.request
from pathlib import Path

token = (Path(__file__).resolve().parents[2] / ".github_token").read_text(encoding="utf-8").strip()


def get(url: str, accept: str = "application/vnd.github+json"):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": accept,
            "User-Agent": "mystudy-perf-check",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            return resp.status, resp.read()
    except Exception as exc:
        raw = exc.read() if hasattr(exc, "read") else b""
        return getattr(exc, "code", None), raw


checks = [
    ("web-infra-dev/rspack", "tests/bench/module-graph-api.bench.ts", 13024),
    ("mochilang/mochi", "runtime/vm/join_bench_test.go", 9446),
    ("openclaw/openclaw", "apps/android/benchmark/src/main/java/ai/openclaw/app/benchmark/StartupMacrobenchmark.kt", 30516),
    ("TanStack/router", "benchmarks/client-nav/react/speed.bench.tsx", 6737),
    ("ra1nty/DXcam", "tests/benchmarks/test_processor_microbenchmark.py", 116),
]

for repo, path, number in checks:
    status, body = get(
        f"https://api.github.com/repos/{repo}/contents/{path}",
        "application/vnd.github.raw",
    )
    text = body.decode("utf-8", "replace")
    print("=" * 60)
    print(repo, status, path, "chars", len(text))
    print(text[:700].replace("\r", ""))
    st2, body2 = get(f"https://api.github.com/repos/{repo}/pulls/{number}/files?per_page=100")
    if st2 == 200:
        files = json.loads(body2)
        names = [item["filename"] for item in files]
        hit = [name for name in names if any(k in name.lower() for k in ("bench", "perf", "benchmark"))]
        print("PR files", len(names), "bench-like", hit[:8])
    else:
        print("PR files status", st2)
