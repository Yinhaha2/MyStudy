# Phase 2 报告：仓库–PR 分布与可编译性粗分

数据来源：`phase2/data/curated/prs_master.csv`（性能目的 PR，共 **4,146** 条，**289** 个仓库）。  
本目录图表与表格可用 `python phase2/report/build_repo_distribution_report.py` 重跑生成。

## 目录

| 路径 | 内容 |
| --- | --- |
| `build_repo_distribution_report.py` | 生成脚本 |
| `repo_pr_distribution.csv` 等 CSV / `summary_stats.json` | 全量分布结果 |
| `build_checklist.csv` / `build_checklist.md` | 289 仓构建清单（含 `human_buildable`） |
| `figures/` | 图（`fig_*.png`） |
| `examples/meteostat_build/` | meteostat 试编日志与相关脚本 |

## 结论先行

1. **高度集中**：Top 10 仓库约占全部 PR 的 **51%**；Top 3（`mochilang/mochi`、`github/gh-aw`、`dotnet/runtime`）约占 **34%**；约 **55** 个仓库就覆盖 **80%** PR。
2. **重型仓主导**：按启发式分层后，**heavy ≈ 105 仓 / 3,437 PR（约 83%）**。这类仓（runtime、Android、Rust 单仓、CUDA/加速器、大型 Go/C# 平台等）本地系统化编译成本高。
3. **轻量走量池不大但存在**：与昨天试编成功的 `meteostat/meteostat` 同类的 **轻量 Python 候选约 43 仓 / 113 PR**；再加上小 Go 候选约 **35 仓 / 125 PR**。两者合计约 **78 仓 / 238 PR（约 5.7%）**——可以走量试编，但撑不起「覆盖全量 4,146」的叙事。
4. **语言代理（按 `perf_files` 主扩展名）**：`.py` 1566，`.go` 847，`.rs` 667，`.cs` 511；其余为 Kotlin / C++ / TS / Java 等。注意：扩展名是性能测试文件的语言，不一定等于仓库主语言（例如 mochi 的 AIDev `language=Go`，但名单里大量 `.py` bench）。

## 详细数字表

### 集中度

| 指标 | 数字 |
| --- | ---: |
| 性能 PR 总数 | 4,146 |
| 仓库数 | 289 |
| Top 3 占比 | 34.1% |
| Top 10 占比 | 51.5% |
| 覆盖 50% PR 所需仓库数 | 10 |
| 覆盖 80% PR 所需仓库数 | 55 |

### Top 15 仓库

| 排名 | 仓库 | PR 数 | 占比 | 合并 | 关闭未合 | open | 主扩展名 | 分层 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | mochilang/mochi | 805 | 19.4% | 674 | 113 | 18 | .py | heavy |
| 2 | github/gh-aw | 432 | 10.4% | 339 | 93 | 0 | .go | heavy |
| 3 | dotnet/runtime | 177 | 4.3% | 116 | 53 | 8 | .cs | heavy |
| 4 | openclaw/openclaw | 170 | 4.1% | 41 | 100 | 29 | .kt | heavy |
| 5 | OliverZhaohaibin/iPhotron-LocalPhotoAlbumManager | 163 | 3.9% | 93 | 70 | 0 | .py | heavy |
| 6 | MontrealAI/AGI-Alpha-Agent-v0 | 103 | 2.5% | 79 | 0 | 24 | .py | heavy |
| 7 | web-infra-dev/rspack | 79 | 1.9% | 30 | 48 | 1 | .rs | heavy |
| 8 | Z3Prover/z3 | 72 | 1.7% | 48 | 22 | 2 | .cpp | heavy |
| 9 | PrefectHQ/prefect | 67 | 1.6% | 56 | 11 | 0 | .py | heavy |
| 10 | oxc-project/oxc | 66 | 1.6% | 25 | 41 | 0 | .rs | heavy |
| 11 | fastrepl/char | 61 | 1.5% | 34 | 27 | 0 | .rs | heavy |
| 12 | devantler-tech/ksail | 61 | 1.5% | 57 | 4 | 0 | .go | heavy |
| 13 | aptos-labs/aptos-core | 56 | 1.4% | 24 | 23 | 9 | .rs | heavy |
| 14 | OpenRakis/Spice86 | 50 | 1.2% | 37 | 12 | 1 | .cs | heavy |
| 15 | jstime/jstime | 49 | 1.2% | 41 | 8 | 0 | .rs | heavy |

完整 289 行见 [`repo_pr_distribution.csv`](repo_pr_distribution.csv)。

### 按性能测试文件扩展名（PR 级）

| 扩展名 | PR 数 | 占比 |
| --- | ---: | ---: |
| .py | 1,566 | 37.8% |
| .go | 847 | 20.4% |
| .rs | 667 | 16.1% |
| .cs | 511 | 12.3% |
| .kt | 171 | 4.1% |
| .cpp | 150 | 3.6% |
| .ts | 135 | 3.3% |
| .java | 93 | 2.2% |
| 其他 | 其余 | — |

### 可编译性粗分（启发式，供讨论）

| 分层 | 仓库数 | PR 数 | PR 占比 | 含义 |
| --- | ---: | ---: | ---: | --- |
| heavy | 105 | 3,437 | 82.9% | 已知或明显重型：runtime / Android / 大型 Rust·C#·加速器仓等 |
| mid | 106 | 471 | 11.4% | 未判轻也未列入重名单 |
| light_py | 43 | 113 | 2.7% | 小体量、主扩展名为 `.py`、且不在重型排除名单（走量试编主候选） |
| light_go | 35 | 125 | 3.0% | 小体量 Go 候选（依赖版本仍可能卡住，如系统 Go 偏旧） |

分层规则写在 `build_repo_distribution_report.py` 的 `HEAVY_REPOS` / `classify_row`。这是**便于排期的粗筛**，不是严格的「一定编得过 / 编不过」。

## 图

| 文件 | 内容 |
| --- | --- |
| [`figures/fig_repo_pr_top40.png`](figures/fig_repo_pr_top40.png) | Top 40 仓库横向条形图（按 PR 数递减；红=heavy，蓝=mid，绿=light） |
| [`figures/fig_repo_pr_all289.png`](figures/fig_repo_pr_all289.png) | 全部 289 仓纵向条形图，横轴按 PR 数从左到右递减 |
| [`figures/fig_repo_pr_cumulative.png`](figures/fig_repo_pr_cumulative.png) | 累积占比曲线（50% / 80% 标注） |
| [`figures/fig_lang_ext_by_pr.png`](figures/fig_lang_ext_by_pr.png) | 性能测试文件扩展名条形图 |

## 关于「刚编过的轻量项目」

| 问题 | 答案 |
| --- | --- |
| 在 3090 上编的是什么？ | `meteostat/meteostat`：Python 天气库；**安装成功**，unit **306 passed** |
| 算轻量吗？ | **算。** 无原生大编译；依赖以 pandas/requests 为主 |
| 有没有对应 benchmark？ | 历史上有 `benchmarks/interpolation.py`（#217）；**当前 main 已删**。名单写的 `interpolation_benchmark.py` 文件名不准确 |
| 安装/测试日志在哪？ | [`examples/meteostat_build/`](examples/meteostat_build/)（含 `03_install.log`、`04_unittest.log`、历史 bench 源码与超时跑分日志；试编脚本在其 `scripts/`） |
| 它对应多少条性能 PR？ | **2** 条（#269、#293），都在 `light_py` |
| 像这样的轻量 Python 仓大概多少？ | 粗筛 **约 43 个仓库 / 113 条 PR**（见 [`light_repo_candidates.csv`](light_repo_candidates.csv) 中 `tier=light_py`） |
| 若加上小 Go？ | 再 **约 35 仓 / 125 PR**；轻量合计约 **238 PR** |

因此：若重型仓短期不好编，**「小项目走量」可行，但体量大约是全量的 3%–6% 量级**（只看 light_py，或 light_py+light_go）。要显著扩大可编集合，需要单独攻几类「半轻」仓（例如纯 Go 工具、中等 Python 库），或接受只验证构建/单测、不复现完整 perf harness。

## 产物清单

- `repo_pr_distribution.csv` — 289 仓明细（PR 数、结局、扩展名、stars、分层、累积份额）
- `perf_file_language_by_pr.csv` — 扩展名汇总
- `build_tier_summary.csv` — 分层汇总
- `light_repo_candidates.csv` — light_py + light_go 候选名单
- `build_checklist.csv` — 构建清单（人工 `human_buildable`）
- `summary_stats.json` — 机器可读摘要
- `build_repo_distribution_report.py` — 生成脚本（图写入 `figures/`）
- `examples/meteostat_build/` — 试编示例

## 和此前 sample6 的关系

`phase2/docs/examples/sample6_repro.md` 谈的是**随机 6 条的性能测试复现难度**（多数难）。本报告谈的是**全量 4,146 在仓库维度的分布**，以及「先编小仓走量」的池子有多大。两者互补：分布说明为什么随机抽样容易抽到难仓；轻量名单说明若改成定向抽样，仍有一小撮可先动手。
