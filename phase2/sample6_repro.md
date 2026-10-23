# 随机 6 条的性能测试能不能复现

种子 20，从 992 条里抽了 6 条。仓库只有 3 个：rspack 1 条，OpenClaw 2 条，mochi 3 条。这 6 条 PR 自己的 diff 都没有改到下面这些性能测试。复现的是仓库里现成的测试，不是这几条 PR 引入的测试。下面说的是按仓库当前文档和源码判断的难度，没有在本机把测试跑起来。

## rspack #13024：难，但仓库把步骤写清楚了

测试在 `xtask/benchmark/benches/benches.rs`，用 Criterion，里面有 `build_chunk_graph`、`module_graph_api`、`bundle_threejs` 等。仓库 README 要求先 `pnpm run bench:prepare` 拉 fixture，再 `pnpm run bench:rust:local`。本地要有 pnpm、Rust、cargo-codspeed，测量走 CodSpeed 的 CPU simulation，依赖 Valgrind。不在 CodSpeed 环境里跑，`cargo codspeed` 往往只做检查、不给出时间。编整个 rspack 再跑这一套，机器和时间成本都高。名单里另一个路径 `tests/bench/module-graph-api.bench.ts` 在默认分支上已经是 404，不能按 HEAD 复现。

## OpenClaw #30516、#44678：难，而且 CI 里的性能流水线不是这个测试

测试是 `apps/android/benchmark/.../StartupMacrobenchmark.kt`。`coldStartup` 用 `StartupTimingMetric`，冷启动 10 次；`startupAndScrollFrameTiming` 用 `FrameTimingMetric`，还要 UiAutomator 滑动。`compileSdk` 是 37，`minSdk` 是 31，依赖 Android Macrobenchmark 和一台模拟器或真机。脚本里对“确认不了 Activity 启动”“没有 renderthread”会直接跳过。仓库的 `openclaw-performance.yml` 跑的是 Kova / vitest，不是这个 Android 宏基准。要复现数字，得单独搭 Android 基准环境，结果也随设备和编译模式变。

## mochi #52、#8628、#9446：脚本能跑，当性能结果不稳定

默认分支上还在的是 `tests/aster/x/py/bench_block.py`。它是生成出来的 Python：设了 `MOCHI_NOW_SEED` 就用固定的伪时钟，不设就用 `time.time_ns()`，循环 1000 次后打印 `duration_us`，没有断言。单跑这个文件很容易，但循环太短，墙钟结果噪声大；设了种子之后打出来的又不是真实耗时。名单里的 `runtime/vm/join_bench_test.go` 和另一份 `bench_block.py` 在默认分支上是 404。#52 的标题是修 Go benchmark 编译，那个文件现在不在默认分支上，按 HEAD 复现不了。
