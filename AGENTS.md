# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is
This is the standalone `MyStudy` research project: Python scripts that analyze performance
(`perf`) Pull Requests from the HuggingFace dataset `hao-li/AIDev`. There is no web/GUI app —
the "application" is a set of data-analysis scripts run from the repo root. See `README.md`
(Chinese) for metric definitions and dataset join keys.

### Runnable application (verified working)
- `python performance_pr_analysis.py` — streams parquet from `hf://datasets/hao-li/AIDev`,
  computes perf-PR merge rates, and writes `output/` (parquet, `all_perfPR.json`,
  `summary_metrics.json`, `SUMMARY_zh.md`, `figures/performance_pr_dashboard.png`). Fast (~10s).
- `python performance_pr_analysis_all.py` — same idea over the full `all_pull_request.parquet`;
  writes `output_all/`. Slow (~2–3 min) because it streams the full ~930k-row table.
- Both accept `--local` to read parquet from a sibling `../AIDev/` directory instead of HF.

### Non-obvious caveats
- **Network required by default.** Scripts read from HuggingFace over the network; there is no
  bundled copy of the AIDev parquet files. If the environment lacks network access, these
  scripts cannot fetch data (the `--local` path below is not available in this standalone repo).
- **`--local` mode does NOT work in this repo.** The scripts compute `ROOT = parents[1]` and look
  for `../AIDev/*.parquet`. This repo is the `MyStudy` subfolder extracted on its own, so the
  sibling `AIDev/` directory is absent. Use the default (HF streaming) mode.
- **`extract_databasephase1.py` and `build_finaldatabase.py` are NOT runnable standalone.** They
  require external paper-source data at `../AIDev/` and `../AIDevPerf/LLM-performance/Outputs/`
  that is not part of this repo. They were used to produce the already-committed `finaldatabase/`
  directory (a pre-built artifact); do not expect to regenerate it here.
- **Generated outputs are not tracked.** `output/`, `output_all/`, and `__pycache__/` are created
  at runtime. Do not commit them.

### Lint / test
- There is no test suite and no linter config. As a smoke check, `python -m py_compile *.py`
  confirms all scripts parse.
