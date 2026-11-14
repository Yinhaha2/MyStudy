#!/usr/bin/env bash
set -euo pipefail
cd /downloads/yzy/build_smoke/meteostat_clean
source .venv/bin/activate
wc -l /downloads/yzy/build_smoke/meteostat_logs/*
echo '---10---'
cat /downloads/yzy/build_smoke/meteostat_logs/10_run_historical_interpolation_bench.log
python <<'PY'
import meteostat as ms
names = [x for x in dir(ms) if any(k in x.lower() for k in ("interp", "hour", "station", "point"))]
print("attrs", names[:40])
print("has interpolate", hasattr(ms, "interpolate"))
print("has hourly", hasattr(ms, "hourly"))
print("has stations", hasattr(ms, "stations"))
PY
