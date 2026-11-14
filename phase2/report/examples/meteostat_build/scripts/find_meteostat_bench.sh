#!/usr/bin/env bash
set -euo pipefail
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890
LOG=/downloads/yzy/build_smoke/meteostat_logs/07_github_commits_search.log
{
  echo "==== search commits API for interpolation_benchmark ===="
  curl -sL 'https://api.github.com/search/commits?q=repo:meteostat/meteostat+interpolation_benchmark' | head -c 4000
  echo
  echo "==== search commits API for path benchmarks ===="
  curl -sL 'https://api.github.com/search/commits?q=repo:meteostat/meteostat+filename:interpolation_benchmark.py' | head -c 4000
  echo
  echo "==== list open/closed PRs 269 293 files ===="
  for n in 269 293; do
    echo "-- PR $n files --"
    curl -sL "https://api.github.com/repos/meteostat/meteostat/pulls/$n/files" \
      | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d if isinstance(d,dict) else "\n".join(f["filename"] for f in d))'
  done
} | tee "$LOG"
