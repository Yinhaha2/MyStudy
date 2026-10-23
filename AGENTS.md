# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is
Standalone `MyStudy` research project. Python scripts analyze agent-authored performance
pull requests. There is no web/GUI app. Layout and file roles are in `README.md`
(Chinese). Papers and datasets are in `REFERENCES.md`.

### Runnable application (verified working)
Run from the repository root:

- `python phase1/scripts/performance_pr_analysis.py` — streams parquet from
  `hf://datasets/hao-li/AIDev`, computes perf-PR merge rates, and writes
  `phase1/output/` (parquet, `all_perfPR.json`, `summary_metrics.json`,
  `SUMMARY_zh.md`, `figures/performance_pr_dashboard.png`). Fast (~10s).
- `python phase1/scripts/performance_pr_analysis_all.py` — same idea over
  `all_pull_request.parquet`; writes `phase1/output_all/`. Slow (~2–3 min)
  because it streams the full ~930k-row table.
- Both accept `--local` to read parquet from a sibling `../AIDev/` directory
  (the parent of this repo) instead of Hugging Face.

### Non-obvious caveats
- **Network required by default.** Scripts read from Hugging Face over the network.
  This repo does not bundle the AIDev parquet files. Without network, the default
  path cannot fetch data.
- **`--local` mode needs a sibling checkout.** The scripts set the external root to
  this repo's parent and look for `../AIDev/*.parquet`. That directory is not part
  of this repo. Use the default Hugging Face mode here.
- **`phase1/scripts/extract_databasephase1.py` and `phase1/scripts/build_finaldatabase.py`
  are not runnable standalone.** They require external paper-source data at
  `../AIDev/` and `../AIDevPerf/LLM-performance/Outputs/`. They produced the
  committed `phase1/data/finaldatabase/` tree; do not expect to regenerate it here.
- **Generated outputs are not tracked.** `output/`, `output_all/`,
  `output_pr_analysis/`, `output_workflow_size/`, and `__pycache__/` are created
  at runtime (Phase 1 scripts write the first four under `phase1/`). Do not commit them.
- **Phase 2 classification** continues with
  `python phase2/scripts/classify_performance_purpose.py`. It reads
  `phase2/data/` and a local `.deepseekToken` at the repo root. It stops on HTTP 402.

### Lint / test
There is no test suite and no linter config. As a smoke check,
`python -m py_compile phase1/scripts/*.py phase2/scripts/*.py` confirms the
maintained scripts parse.
