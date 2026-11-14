#!/usr/bin/env bash
set -euo pipefail
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890

LOGDIR=/downloads/yzy/build_smoke/meteostat_logs
ROOT=/downloads/yzy/build_smoke
mkdir -p "$LOGDIR"
cd "$ROOT"

{
  echo "==== host ===="
  hostname
  date -Is
  whoami
  echo "==== python ===="
  python3.11 -V
  which python3.11
} | tee "$LOGDIR/00_env.txt"

# Fresh shallow clone of default branch for a clean install log
rm -rf meteostat_clean
git clone --depth 1 https://github.com/meteostat/meteostat.git meteostat_clean
cd meteostat_clean

{
  echo "==== git ===="
  git remote -v
  git log -1 --format=fuller
  echo "==== top-level ===="
  ls -la
  echo "==== search bench/perf paths ===="
  find . -iname '*bench*' -o -iname '*perf*' | grep -v '.git' || true
} | tee "$LOGDIR/01_tree.txt"

python3.11 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -V | tee "$LOGDIR/02_python_venv.txt"

{
  echo "==== pip install -e . ===="
  pip install -U pip
  pip install -e .
  echo "==== import ===="
  python -c 'import meteostat,sys; print("import_ok", meteostat.__file__); print(sys.version)'
} 2>&1 | tee "$LOGDIR/03_install.log"

{
  echo "==== pip install pytest pytest-mock ===="
  pip install pytest pytest-mock
  echo "==== unit tests ===="
  pytest -q tests/unit --import-mode=importlib --ignore=tests/unit/test_user_agent.py
} 2>&1 | tee "$LOGDIR/04_unittest.log"

{
  echo "==== look for benchmarks in git history (unshallow) ===="
  git fetch --unshallow || true
  git log --all --oneline -- 'benchmarks' '**/interpolation_benchmark.py' | head -50 || true
  git log --all --diff-filter=A --summary | rg -i 'benchmark' | head -50 || true
  echo "==== github contents via api ===="
  curl -sL https://api.github.com/repos/meteostat/meteostat/git/trees/HEAD?recursive=1 \
    | python3 -c 'import sys,json; j=json.load(sys.stdin); paths=[t["path"] for t in j.get("tree",[]) if "bench" in t["path"].lower() or "perf" in t["path"].lower()]; print("\n".join(paths) if paths else "NO_BENCH_OR_PERF_PATHS")'
} 2>&1 | tee "$LOGDIR/05_benchmark_search.log"

echo DONE > "$LOGDIR/DONE"
ls -la "$LOGDIR"
