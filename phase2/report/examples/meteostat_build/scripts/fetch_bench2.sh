#!/usr/bin/env bash
set -euo pipefail
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890
LOGDIR=/downloads/yzy/build_smoke/meteostat_logs
{
  echo "==== raw benchmarks/interpolation.py at d0166c51 ===="
  curl -sL 'https://raw.githubusercontent.com/meteostat/meteostat/d0166c51fa5a4201117496faac68ae84ae9483c7/benchmarks/interpolation.py' | tee /downloads/yzy/build_smoke/old_bench/interpolation.py | head -100
  echo
  echo "==== does HEAD still have benchmarks/interpolation.py? ===="
  curl -sL -o /dev/null -w '%{http_code}\n' 'https://raw.githubusercontent.com/meteostat/meteostat/main/benchmarks/interpolation.py'
  echo "==== search commits for interpolation_benchmark.py filename ===="
  curl -sL 'https://api.github.com/search/commits?q=repo:meteostat/meteostat+interpolation_benchmark.py' | python3 -c 'import sys,json; j=json.load(sys.stdin); print("count", j.get("total_count"));
[print(i["sha"][:10], i["commit"]["message"].splitlines()[0][:120]) for i in j.get("items",[])[:15]]'
  echo "==== tree at d0166c51 under benchmarks/ ===="
  curl -sL 'https://api.github.com/repos/meteostat/meteostat/contents/benchmarks?ref=d0166c51fa5a4201117496faac68ae84ae9483c7' \
    | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d if isinstance(d,dict) else "\n".join(f["name"]+" "+f["path"] for f in d))'
} | tee "$LOGDIR/09_benchmark_file_resolve.log"

cd /downloads/yzy/build_smoke/meteostat_clean
source .venv/bin/activate
{
  echo "==== py_compile historical benchmarks/interpolation.py ===="
  python -m py_compile /downloads/yzy/build_smoke/old_bench/interpolation.py && echo SYNTAX_OK
  echo "==== run historical benchmarks/interpolation.py (60s cap) ===="
  timeout 90 python /downloads/yzy/build_smoke/old_bench/interpolation.py 2>&1 || echo RUN_EXIT:$?
} 2>&1 | tee "$LOGDIR/10_run_historical_interpolation_bench.log"
