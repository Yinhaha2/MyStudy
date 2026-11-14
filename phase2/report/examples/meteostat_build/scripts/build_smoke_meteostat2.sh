#!/usr/bin/env bash
set -euo pipefail
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890
cd /downloads/yzy/build_smoke/meteostat
source .venv/bin/activate
echo "HEAD files with bench:"
find . -iname '*bench*' -not -path './.venv/*' -not -path './.git/*' | head -50
echo "--- try PR 269 head via gh api ---"
# list remote branches and fetch PR merge refs if present
git fetch --depth 1 origin pull/269/head:pr-269 || true
if git rev-parse pr-269 >/dev/null 2>&1; then
  git checkout pr-269
  find . -iname '*bench*' -not -path './.venv/*' -not -path './.git/*' | head -50
  if [[ -f benchmarks/interpolation_benchmark.py ]]; then
    python -m py_compile benchmarks/interpolation_benchmark.py
    echo py_compile_benchmark_ok
  fi
fi
python -c 'from meteostat import Point, Hourly; print("api_ok", Point, Hourly)'
echo DONE
