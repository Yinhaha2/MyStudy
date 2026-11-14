#!/usr/bin/env bash
set -euo pipefail
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890
LOGDIR=/downloads/yzy/build_smoke/meteostat_logs
{
  echo "==== files in commit d0166c51 (PR 217 merge) matching bench ===="
  curl -sL 'https://api.github.com/repos/meteostat/meteostat/commits/d0166c51fa5a4201117496faac68ae84ae9483c7' \
    | python3 -c 'import sys,json; j=json.load(sys.stdin);
files=j.get("files") or []
for f in files:
  if "bench" in f["filename"].lower() or "interp" in f["filename"].lower():
    print(f["status"], f["filename"], "patch_len", len(f.get("patch") or ""))'
  echo "==== raw interpolation_benchmark at that commit ===="
  curl -sL 'https://raw.githubusercontent.com/meteostat/meteostat/d0166c51fa5a4201117496faac68ae84ae9483c7/benchmarks/interpolation_benchmark.py' | head -80
  echo
  echo "==== search when benchmarks dir disappeared ===="
  curl -sL 'https://api.github.com/search/commits?q=repo:meteostat/meteostat+Remove+benchmark' | python3 -c 'import sys,json; j=json.load(sys.stdin); print("count", j.get("total_count"));
[print(i["sha"][:8], i["commit"]["message"].splitlines()[0]) for i in j.get("items",[])[:10]]'
  echo "==== PR 269 files ===="
  curl -sL 'https://api.github.com/repos/meteostat/meteostat/pulls/269/files?per_page=100' \
    | python3 -c 'import sys,json; d=json.load(sys.stdin); print("\n".join(f["filename"] for f in d) if isinstance(d,list) else d)'
  echo "==== PR 293 files ===="
  curl -sL 'https://api.github.com/repos/meteostat/meteostat/pulls/293/files?per_page=100' \
    | python3 -c 'import sys,json; d=json.load(sys.stdin); print("\n".join(f["filename"] for f in d) if isinstance(d,list) else d)'
} | tee "$LOGDIR/07_benchmark_history.log"

# try checkout old file into a side dir and py_compile only (may need deps)
mkdir -p /downloads/yzy/build_smoke/old_bench
curl -sL 'https://raw.githubusercontent.com/meteostat/meteostat/d0166c51fa5a4201117496faac68ae84ae9483c7/benchmarks/interpolation_benchmark.py' \
  -o /downloads/yzy/build_smoke/old_bench/interpolation_benchmark.py
wc -l /downloads/yzy/build_smoke/old_bench/interpolation_benchmark.py | tee -a "$LOGDIR/07_benchmark_history.log"
ls /downloads/yzy/build_smoke/meteostat_clean/.venv/bin/python
# syntax check only against current package API may fail; still record
cd /downloads/yzy/build_smoke/meteostat_clean
source .venv/bin/activate
{
  echo "==== py_compile historical benchmark file (syntax only) ===="
  python -m py_compile /downloads/yzy/build_smoke/old_bench/interpolation_benchmark.py && echo SYNTAX_OK
  echo "==== try running historical benchmark (expect import/API drift) ===="
  # copy into package tree temporarily for a real run attempt
  mkdir -p /tmp/meteostat_bench_run/benchmarks
  cp /downloads/yzy/build_smoke/old_bench/interpolation_benchmark.py /tmp/meteostat_bench_run/benchmarks/
  PYTHONPATH=/downloads/yzy/build_smoke/meteostat_clean timeout 60 python /tmp/meteostat_bench_run/benchmarks/interpolation_benchmark.py 2>&1 || echo RUN_EXIT:$?
} 2>&1 | tee "$LOGDIR/08_historical_benchmark_run.log"
