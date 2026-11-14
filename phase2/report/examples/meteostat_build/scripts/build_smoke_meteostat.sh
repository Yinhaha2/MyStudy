#!/usr/bin/env bash
set -euo pipefail
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890
ROOT=/downloads/yzy/build_smoke
mkdir -p "$ROOT"
cd "$ROOT"
rm -rf meteostat
git clone --depth 1 https://github.com/meteostat/meteostat.git
cd meteostat
python3.11 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python -V
pip install -U pip
pip install -e .
python -c 'import meteostat; print("import_ok", meteostat.__file__)'
echo "--- benchmarks ---"
ls -la benchmarks || true
python -m py_compile benchmarks/interpolation_benchmark.py
echo "py_compile_ok"
# install light test deps if listed; otherwise stop at import
if [[ -f requirements.txt ]]; then pip install -r requirements.txt || true; fi
if [[ -f requirements-dev.txt ]]; then pip install -r requirements-dev.txt || true; fi
pip install pytest || true
# run a tiny non-network unit if any; don't fail whole smoke on missing tests
pytest -q --collect-only 2>/dev/null | head -20 || true
echo DONE
