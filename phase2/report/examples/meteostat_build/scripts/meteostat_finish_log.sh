#!/usr/bin/env bash
set -euo pipefail
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890

LOGDIR=/downloads/yzy/build_smoke/meteostat_logs
cd /downloads/yzy/build_smoke/meteostat_clean
# shellcheck disable=SC1091
source .venv/bin/activate

{
  echo "==== unit tests (ignore missing optional deps) ===="
  pytest -q tests/unit --import-mode=importlib \
    --ignore=tests/unit/test_user_agent.py \
    --ignore=tests/unit/test_era5_hourly.py
  echo EXIT:$?
} 2>&1 | tee "$LOGDIR/04_unittest.log"

{
  echo "==== search bench/perf in working tree ===="
  find . -iname '*bench*' -o -iname '*perf*' 2>/dev/null | grep -vE '\.git|\.venv' || echo NONE
  echo "==== unshallow + history search ===="
  git fetch --unshallow 2>&1 | tail -3 || true
  echo "-- log path benchmarks --"
  git log --all --oneline -- benchmarks 2>&1 | head -30 || true
  echo "-- log path interpolation_benchmark --"
  git log --all --oneline -- '*interpolation_benchmark*' 2>&1 | head -30 || true
  echo "-- pickaxe --"
  git log --all --oneline -S 'interpolation_benchmark' 2>&1 | head -30 || true
  echo "==== GitHub recursive tree API ===="
  curl -sL 'https://api.github.com/repos/meteostat/meteostat/git/trees/HEAD?recursive=1' \
    | python3 -c 'import sys,json
j=json.load(sys.stdin)
tree=j.get("tree") or []
paths=[t["path"] for t in tree if ("bench" in t["path"].lower() or "perf" in t["path"].lower())]
print("matched", len(paths))
print("\n".join(paths) if paths else "NO_BENCH_OR_PERF_PATHS_ON_HEAD")
print("total_files", len(tree))'
} 2>&1 | tee "$LOGDIR/05_benchmark_search.log"

{
  echo "==== note on dataset path ===="
  echo "AIDev/Phase2 listed benchmarks/interpolation_benchmark.py as a repo-level perf_files hit."
  echo "That means some historical commit in the AIDev scan contained the path;"
  echo "it does NOT mean current HEAD still has the file, nor that PR #269/#293 edited it."
} | tee "$LOGDIR/06_benchmark_note.txt"

ls -la "$LOGDIR"
echo DONE > "$LOGDIR/DONE"
