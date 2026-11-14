# meteostat/meteostat 试编与执行日志

本目录是 Phase 2 报告下的**试编示例**（`phase2/report/examples/meteostat_build/`）：日志与历史 bench 源码在根下，一次性服务器脚本在 `scripts/`。

机器：`yzy@10.131.191.2`（dellserver），Python **3.11**，代理 `127.0.0.1:7890`。  
时间：2026-11-11。仓库检出：GitHub `main` 当时 HEAD（`c2f4c94`，含 #323）。

## 一句话结论

| 问题 | 答案 |
| --- | --- |
| 编出来了吗？ | **是。** `pip install -e .` 成功，`import meteostat` 成功 |
| 有 benchmark 吗？ | **历史上有，当前默认分支没有。** 真实文件名是 `benchmarks/interpolation.py`（PR #217 / commit `d0166c51`），不是名单里的 `interpolation_benchmark.py` |
| 今天跑通 benchmark 了吗？ | **没有。** 历史脚本语法通过；按当前包 API 去跑时在拉气象数据阶段 **90s 超时**（`RUN_EXIT:124`），没有打出计时结果 |
| 单元测试？ | **306 passed**（约 0.35s；跳过了缺可选依赖 `metar` / `numcodecs` 的少数用例） |

## 日志文件

| 文件 | 内容 |
| --- | --- |
| `00_env.txt` | 主机、时间、Python 路径 |
| `01_tree.txt` | clone 后的 git 信息与顶层目录（当时无 bench 路径） |
| `02_python_venv.txt` | venv 内 Python 版本 |
| `03_install.log` | **`pip install -e .` 完整输出** + `import_ok` |
| `04_unittest.log` | **`pytest tests/unit`：306 passed** |
| `05_benchmark_search.log` | 工作树 / HEAD tree API：无 bench/perf 路径 |
| `06_benchmark_note.txt` | 对 Phase2 `perf_files` 字段含义的说明 |
| `07_benchmark_history.log` / `07_github_commits_search.log` | GitHub 提交搜索；定位到 #217 |
| `08_historical_benchmark_run.log` | 早期误下 `interpolation_benchmark.py`（404）的记录 |
| `09_benchmark_file_resolve.log` | 确认真实文件为 `benchmarks/interpolation.py`；`main` 上 404 |
| `10_run_historical_interpolation_bench.log` | 历史脚本 `py_compile` 成功；执行 **超时 124** |
| `11_api_check.txt` | 当前包仍有 `interpolate` / `hourly` / `stations` |
| `historical_benchmarks_interpolation.py` | 从 commit `d0166c51` 拉下来的历史 benchmark 源码副本 |
| `scripts/` | 当时在服务器上用的 smoke / 拉 bench / 比对 PR 脚本（一次性） |

## Benchmark 说明（重要）

Phase2 名单给这条仓库挂的是：

`benchmarks/interpolation_benchmark.py`

这是**仓库级**命中：AIDev 扫描里该仓某次提交出现过性能测试路径，因此该仓下的 PR（含 #269、#293）都会带上这个 `perf_files`。  
核对 GitHub 后：

1. **实际出现过的文件**是 `benchmarks/interpolation.py`（#217 合入），不是 `*_benchmark.py` 这个文件名。
2. **当前 `main` 已删除** `benchmarks/` 目录（raw URL 404）。
3. 我们两条性能 PR 自己的 diff **都没改**这个文件：#269 只动 `.github/workflows/tests.yml`；#293 只动 MOSMIX 配置/provider。

因此：报告里先前只写 unittest，是因为**按 HEAD 根本编不出/跑不了名单上的那条 benchmark 路径**；历史脚本可以找回，但要外网拉站点与小时数据，这次试跑卡在网络取数上。

## 和「编出来了」的关系

- **安装/编译（Python 包）**：成功，见 `03_install.log`
- **正确性冒烟（unit）**：成功，见 `04_unittest.log`
- **名单上的性能测试复现**：当前不可按 HEAD 复现；历史脚本有源码（本目录已存），完整计时跑通还要再处理数据拉取/超时
