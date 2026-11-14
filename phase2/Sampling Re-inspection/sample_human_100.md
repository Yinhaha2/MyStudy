# Human re-inspection sample (n=100)

Seed `20261114`；总体 = 4,146 条性能目的 PR；与 DeepSeek 样本无交集。

**判定口径**（与初筛及论文 filter 一致）：依据标题与正文，判断该 PR 的**主要目的**是否为提升性能。`1` = 是；`0` = 否。

人工独立复检结果见 `human_reinspection_report.md`。

| # | repo | PR | outcome | original | title | link | 标注(0/1) | 备注 |
| ---: | --- | ---: | --- | --- | --- | --- | :---: | --- |
| 1 | asynkron/protoactor-dotnet | 2367 | merged | performance | Fix Gossip composite consensus test timing | [open](https://github.com/asynkron/protoactor-dotnet/pull/2367) | 1 |  |
| 2 | readmeio/oas | 1064 | merged | performance | perf(parser): dereferencing benchmarks | [open](https://github.com/readmeio/oas/pull/1064) | 1 | 建立 dereferencing 性能基准，属性能相关工作 |
| 3 | OliverZhaohaibin/iPhotron-LocalPhotoAlbumManager | 135 | merged | performance | Refactor edit workflow to reuse shared GL viewer | [open](https://github.com/OliverZhaohaibin/iPhotron-LocalPhotoAlbumManager/pull/135) | 0 | 重构编辑工作流复用 GL viewer，无性能主张 |
| 4 | OliverZhaohaibin/iPhotron-LocalPhotoAlbumManager | 462 | closed_unmerged | performance | Optimize All Photos loading with cursor-based SQL pagination | [open](https://github.com/OliverZhaohaibin/iPhotron-LocalPhotoAlbumManager/pull/462) | 1 |  |
| 5 | Cap-go/capgo | 1042 | closed_unmerged | performance | fix: display API key start and linkages to orgs/apps | [open](https://github.com/Cap-go/capgo/pull/1042) | 0 | 展示 API key / org 关联，功能修复 |
| 6 | openclaw/openclaw | 47533 | merged | performance | CLI: respect full timeout for loopback gateway probes | [open](https://github.com/openclaw/openclaw/pull/47533) | 1 |  |
| 7 | oxc-project/oxc | 13031 | closed_unmerged | performance | refactor(transformer): Move TransformCtx into TraverseCtx state to eliminate Ref | [open](https://github.com/oxc-project/oxc/pull/13031) | 1 |  |
| 8 | vercel/workflow | 560 | merged | performance | fix: compare benchmarks against PR base branch instead of main | [open](https://github.com/vercel/workflow/pull/560) | 1 | 修正 benchmark 对比基线，性能评测流水线 |
| 9 | openclaw/openclaw | 36668 | closed_unmerged | performance | perf(telegram): memoize sticker cache disk loads | [open](https://github.com/openclaw/openclaw/pull/36668) | 1 |  |
| 10 | mochilang/mochi | 19285 | merged | performance | go transpiler: fold pow10 to reduce float error | [open](https://github.com/mochilang/mochi/pull/19285) | 0 | fold pow10 降低浮点误差，正确性而非加速 |
| 11 | MontrealAI/AGI-Alpha-Agent-v0 | 2708 | merged | performance | [alpha_factory] open gallery links in new tab | [open](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/2708) | 0 | 画廊链接新标签打开，UI 功能 |
| 12 | mochilang/mochi | 5053 | merged | performance | Improve Clojure type inference | [open](https://github.com/mochilang/mochi/pull/5053) | 0 | Clojure 类型推断，无性能主张 |
| 13 | fastrepl/char | 2772 | closed_unmerged | performance | feat(persister): add per-path content hashing to reduce unnecessary file writes | [open](https://github.com/fastrepl/char/pull/2772) | 1 | 页面 404；缓存正文为 hashing 减少无意义写盘 |
| 14 | MontrealAI/AGI-Alpha-Agent-v0 | 1934 | merged | performance | [alpha_factory] Fix A2ABus publish lock timing | [open](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/1934) | 1 |  |
| 15 | SOVEREIGN-NET/The-Sovereign-Network | 705 | merged | performance | Standardize sled insert API usage to avoid unnecessary allocation | [open](https://github.com/SOVEREIGN-NET/The-Sovereign-Network/pull/705) | 1 |  |
| 16 | zeroclaw-labs/zeroclaw | 1851 | closed_unmerged | performance | perf(agent): reduce string clones in run_tool_call_loop | [open](https://github.com/zeroclaw-labs/zeroclaw/pull/1851) | 1 |  |
| 17 | github/gh-aw | 803 | merged | performance | Fix compiler to only generate task job when required for checks | [open](https://github.com/github/gh-aw/pull/803) | 1 |  |
| 18 | OpenRakis/Spice86 | 1759 | merged | performance | Fix critical channel feature deviations from DOSBox Staging audio implementation | [open](https://github.com/OpenRakis/Spice86/pull/1759) | 0 | DOSBox 音频功能对齐，非性能优化 |
| 19 | doobidoo/mcp-memory-service | 227 | merged | performance | perf: Global caching for 411,457x MCP performance improvement | [open](https://github.com/doobidoo/mcp-memory-service/pull/227) | 1 |  |
| 20 | mochilang/mochi | 6126 | merged | performance | Add typed var support and cleanup Java compiler | [open](https://github.com/mochilang/mochi/pull/6126) | 1 |  |
| 21 | NVIDIA/cuda-python | 872 | merged | performance | CI: Enable proxy cache in test and build-docs pipelines | [open](https://github.com/NVIDIA/cuda-python/pull/872) | 1 | CI proxy cache，流水线性能 |
| 22 | github/gh-aw | 14547 | closed_unmerged | performance | Replace permissions factory explosion with builder pattern | [open](https://github.com/github/gh-aw/pull/14547) | 1 |  |
| 23 | NethermindEth/nethermind | 10858 | merged | performance | FlatDB dictionary lookup optimization | [open](https://github.com/NethermindEth/nethermind/pull/10858) | 1 |  |
| 24 | Azure/azure-sdk-for-net | 50357 | closed_unmerged | performance | [ServiceBus] Consider retry attempts with ServerBusy exit logic | [open](https://github.com/Azure/azure-sdk-for-net/pull/50357) | 1 |  |
| 25 | NethermindEth/nethermind | 10580 | merged | performance | Add reproducible EXPB benchmark workflow with baseline PR comparison | [open](https://github.com/NethermindEth/nethermind/pull/10580) | 1 | 可复现 benchmark 工作流，性能评测基建 |
| 26 | github/gh-aw | 3658 | merged | performance | Standardize repository slug retrieval on single cached implementation | [open](https://github.com/github/gh-aw/pull/3658) | 1 |  |
| 27 | erigontech/erigon | 20148 | open | performance | log: replace SyncHandler with AsyncStreamHandler to fix goroutine contention | [open](https://github.com/erigontech/erigon/pull/20148) | 1 |  |
| 28 | rocicorp/mono | 5104 | closed_unmerged | performance | chore: Shard tests by engine instead of numerically | [open](https://github.com/rocicorp/mono/pull/5104) | 1 | 测试分片加速 CI |
| 29 | openclaw/openclaw | 46594 | closed_unmerged | performance | fix(ui): stop chat auto-follow from fighting manual scroll | [open](https://github.com/openclaw/openclaw/pull/46594) | 0 | 聊天滚动 UX bugfix |
| 30 | mochilang/mochi | 19331 | merged | performance | cs: handle zero minus unary form | [open](https://github.com/mochilang/mochi/pull/19331) | 1 |  |
| 31 | jstime/jstime | 406 | merged | performance | Reduce console benchmark iterations from 100k to 10k | [open](https://github.com/jstime/jstime/pull/406) | 1 | 减少 bench 迭代以加速评测套件 |
| 32 | sebastienros/jint | 2298 | merged | performance | Add `UnwrapIfPromiseAsync` extension method for non-blocking promise resolution | [open](https://github.com/sebastienros/jint/pull/2298) | 1 |  |
| 33 | Chia-Network/chia-blockchain | 20663 | closed_unmerged | performance | Dict fromkeys performance test | [open](https://github.com/Chia-Network/chia-blockchain/pull/20663) | 1 | 新增 dict.fromkeys 性能测试 |
| 34 | marin-community/levanter | 1056 | closed_unmerged | performance | Improve sample_lm generation | [open](https://github.com/marin-community/levanter/pull/1056) | 1 |  |
| 35 | Skidamek/AutoModpack | 434 | closed_unmerged | performance | Optimize file I/O, eliminate redundant operations, and improve algorithmic compl | [open](https://github.com/Skidamek/AutoModpack/pull/434) | 1 |  |
| 36 | mochilang/mochi | 15766 | merged | performance | scala: benchmark chowla-numbers | [open](https://github.com/mochilang/mochi/pull/15766) | 1 | 生成/记录 Scala benchmark |
| 37 | Z3Prover/z3 | 8729 | merged | performance | Convert `bvarray2uf` tactic to a dependent_expr_simplifier | [open](https://github.com/Z3Prover/z3/pull/8729) | 0 | tactic→simplifier 架构迁移，非性能主叙事 |
| 38 | spellshift/realm | 1167 | merged | performance | Throttle pivot.port_scan to prevent FD exhaustion | [open](https://github.com/spellshift/realm/pull/1167) | 1 |  |
| 39 | mycrl/turn-rs | 152 | closed_unmerged | performance | Add service benchmarks for STUN/TURN message processing | [open](https://github.com/mycrl/turn-rs/pull/152) | 1 | 新增 service 性能 benches |
| 40 | fern-api/fern | 11167 | merged | performance | fix(csharp): remove blocking .Result calls on async tasks in generated code | [open](https://github.com/fern-api/fern/pull/11167) | 1 |  |
| 41 | RocketChat/Rocket.Chat | 38998 | closed_unmerged | performance | Fix: Members List not refreshed when users join or leave a channel | [open](https://github.com/RocketChat/Rocket.Chat/pull/38998) | 0 | 成员列表刷新 bugfix |
| 42 | oxc-project/oxc | 12944 | closed_unmerged | performance | Implement object comparison folding in minifier constant folding pass | [open](https://github.com/oxc-project/oxc/pull/12944) | 1 |  |
| 43 | oxc-project/oxc | 12709 | closed_unmerged | performance | Add comprehensive binary size analysis tooling and size optimizations | [open](https://github.com/oxc-project/oxc/pull/12709) | 1 |  |
| 44 | ROCm/iris | 400 | closed_unmerged | performance | Report 07_gemm_all_scatter benchmark results from CI | [open](https://github.com/ROCm/iris/pull/400) | 1 | 汇报 CI 性能数字（analytics） |
| 45 | omerbenamram/evtx | 255 | closed_unmerged | performance | Optimize evtx parsing with per-chunk arena and zero-copy tokens | [open](https://github.com/omerbenamram/evtx/pull/255) | 1 |  |
| 46 | mochilang/mochi | 11655 | merged | performance | Improve Java transpiler avg support | [open](https://github.com/mochilang/mochi/pull/11655) | 1 |  |
| 47 | cyw0ng95/sqlvibe | 112 | merged | performance | v0.11.1: Fix CG_OP_* opcode constants + wire CGOptimizeProgram + remove Go engin | [open](https://github.com/cyw0ng95/sqlvibe/pull/112) | 1 |  |
| 48 | langchain-ai/langsmith-sdk | 1781 | closed_unmerged | performance | Relax async test timing | [open](https://github.com/langchain-ai/langsmith-sdk/pull/1781) | 0 | 放宽异步测试时间阈值，测试稳定性/flaky |
| 49 | torchgeo/torchgeo | 2973 | open | performance | Refactor remote downloads to use fsspec with unified cloud API | [open](https://github.com/torchgeo/torchgeo/pull/2973) | 0 | fsspec 统一云下载 API 重构，功能/工程 |
| 50 | ydb-platform/ydb | 34740 | open | performance | Fix WaitForAcks race condition and move slow topic tests to SIZE(LARGE) | [open](https://github.com/ydb-platform/ydb/pull/34740) | 1 |  |
| 51 | jstime/jstime | 321 | closed_unmerged | performance | [WIP] Investigate opportunities for runtime performance improvement | [open](https://github.com/jstime/jstime/pull/321) | 1 |  |
| 52 | MontrealAI/AGI-Alpha-Agent-v0 | 3430 | merged | performance | Improve docs asset caching and lint | [open](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/3430) | 1 |  |
| 53 | elastic/beats | 49588 | open | performance | Optimize Network.Check single-IP path to reduce allocations | [open](https://github.com/elastic/beats/pull/49588) | 1 |  |
| 54 | open-metadata/OpenMetadata | 25242 | merged | performance | Add exponential backoff retry for index deletion during snapshot operations | [open](https://github.com/open-metadata/OpenMetadata/pull/25242) | 1 |  |
| 55 | OliverZhaohaibin/iPhotron-LocalPhotoAlbumManager | 471 | closed_unmerged | performance | ⚡ Bolt: Optimize glob expansion in file scanning | [open](https://github.com/OliverZhaohaibin/iPhotron-LocalPhotoAlbumManager/pull/471) | 1 |  |
| 56 | MontrealAI/AGI-Alpha-Agent-v0 | 1035 | merged | performance | [alpha_factory] improve rate limiter cleanup | [open](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/1035) | 1 |  |
| 57 | dotnet/runtime | 122956 | closed_unmerged | performance | Partial Chase-Lev work-stealing deque implementation for ConcurrentBag<T> | [open](https://github.com/dotnet/runtime/pull/122956) | 1 |  |
| 58 | dotnet/runtime | 124280 | merged | performance | Fix missing early returns in TensorPrimitives.Round.cs | [open](https://github.com/dotnet/runtime/pull/124280) | 1 |  |
| 59 | OliverZhaohaibin/iPhotron-LocalPhotoAlbumManager | 377 | merged | performance | Pre-sort assets in worker to prevent UI flash | [open](https://github.com/OliverZhaohaibin/iPhotron-LocalPhotoAlbumManager/pull/377) | 1 |  |
| 60 | OpenCoreMMO/OpenCoreMMO | 955 | closed_unmerged | performance | [WIP] Delegate request to PR #954 | [open](https://github.com/OpenCoreMMO/OpenCoreMMO/pull/955) | 1 |  |
| 61 | github/gh-aw | 22675 | merged | performance | docs: fix homepage title duplication and disable glow animation on mobile for al | [open](https://github.com/github/gh-aw/pull/22675) | 0 | 文档主页标题与动画，非性能 |
| 62 | mochilang/mochi | 5001 | merged | performance | Improve Python compiler first() handling | [open](https://github.com/mochilang/mochi/pull/5001) | 1 |  |
| 63 | asynkron/protoactor-dotnet | 2212 | merged | performance | feat: cache build outputs | [open](https://github.com/asynkron/protoactor-dotnet/pull/2212) | 1 | 缓存 CI build 输出 |
| 64 | github/gh-aw | 8940 | merged | performance | Add dispatch-workflow safe output type with dynamic per-workflow tools | [open](https://github.com/github/gh-aw/pull/8940) | 0 | 新增 dispatch-workflow 能力，功能 |
| 65 | mochilang/mochi | 2772 | closed_unmerged | performance | Add tail call optimization to VM | [open](https://github.com/mochilang/mochi/pull/2772) | 1 |  |
| 66 | openclaw/openclaw | 32847 | closed_unmerged | performance | Slack: avoid socket-mode restart loops on transient disconnects | [open](https://github.com/openclaw/openclaw/pull/32847) | 1 |  |
| 67 | github/gh-aw | 11958 | closed_unmerged | performance | [WIP] Optimize MCP tool response payloads to reduce token usage | [open](https://github.com/github/gh-aw/pull/11958) | 1 |  |
| 68 | erpc/erpc | 692 | closed_unmerged | performance | test: speed up test ci | [open](https://github.com/erpc/erpc/pull/692) | 1 | 加速 test CI |
| 69 | marin-community/marin | 3248 | merged | performance | [levanter] Default fused CE TPU path to XLA and retune v4 huge-batch blocks | [open](https://github.com/marin-community/marin/pull/3248) | 1 |  |
| 70 | btraceio/btrace | 744 | merged | performance | feat: Implement Binary Protocol v2 with comprehensive testing infrastructure | [open](https://github.com/btraceio/btrace/pull/744) | 0 | Binary Protocol v2 功能与测试基建 |
| 71 | ava-labs/avalanchego | 5005 | closed_unmerged | performance | Prevent deadlock in benchlist using dedicated notification worker goroutine | [open](https://github.com/ava-labs/avalanchego/pull/5005) | 1 |  |
| 72 | OrchardCMS/OrchardCore | 18642 | merged | performance | Replace dynamic ContentCard shapes with strongly typed shapes | [open](https://github.com/OrchardCMS/OrchardCore/pull/18642) | 1 |  |
| 73 | oxc-project/oxc | 12730 | closed_unmerged | performance | Add `RUN_RAW_TESTS` environment variable to disable slow raw transfer tests loca | [open](https://github.com/oxc-project/oxc/pull/12730) | 1 | 本地关闭慢测试，开发/CI 时间 |
| 74 | wikimedia/sentencex | 20 | closed_unmerged | performance | Performance analysis and optimizations for large text processing | [open](https://github.com/wikimedia/sentencex/pull/20) | 1 |  |
| 75 | mochilang/mochi | 17904 | closed_unmerged | performance | swift: improve int casting and bool map lookups | [open](https://github.com/mochilang/mochi/pull/17904) | 1 |  |
| 76 | openclaw/openclaw | 32092 | closed_unmerged | performance | Telegram: skip deleteMyCommands before non-empty command sync | [open](https://github.com/openclaw/openclaw/pull/32092) | 1 |  |
| 77 | mochilang/mochi | 9244 | merged | performance | Improve C# list indexing | [open](https://github.com/mochilang/mochi/pull/9244) | 1 |  |
| 78 | dotnet/runtime | 119210 | merged | performance | Fix LDAP network timeout not being honored on Linux | [open](https://github.com/dotnet/runtime/pull/119210) | 0 | LDAP 超时未生效，正确性修复 |
| 79 | OliverZhaohaibin/iPhotron-LocalPhotoAlbumManager | 438 | merged | performance | Improve initial scan persistence and UI responsiveness | [open](https://github.com/OliverZhaohaibin/iPhotron-LocalPhotoAlbumManager/pull/438) | 1 |  |
| 80 | aptos-labs/aptos-core | 18838 | merged | performance | [Storage] Reduce RocksDB property reporter overhead | [open](https://github.com/aptos-labs/aptos-core/pull/18838) | 1 |  |
| 81 | paradigmxyz/reth | 22361 | closed_unmerged | performance | feat(engine): add sub-phase timing histograms for sparse trie update | [open](https://github.com/paradigmxyz/reth/pull/22361) | 1 | 性能子阶段计时直方图（analytics） |
| 82 | dotnet/runtime | 123074 | merged | performance | Refactor process.cpp to eliminate vector dependency and shutdown race conditions | [open](https://github.com/dotnet/runtime/pull/123074) | 1 |  |
| 83 | github/gh-aw | 9016 | merged | performance | Optimize action pinning and caching: eliminate redundant JSON parsing and I/O | [open](https://github.com/github/gh-aw/pull/9016) | 1 |  |
| 84 | devantler-tech/ksail | 2803 | merged | performance | feat: add `ksail workload watch` command for inner-loop development | [open](https://github.com/devantler-tech/ksail/pull/2803) | 0 | 新增 ksail workload watch，功能 |
| 85 | btraceio/btrace | 769 | merged | performance | instr: performance and correctness improvements | [open](https://github.com/btraceio/btrace/pull/769) | 1 |  |
| 86 | mochilang/mochi | 8113 | merged | performance | Add OCaml TPCH q1 compile test | [open](https://github.com/mochilang/mochi/pull/8113) | 0 | 添加 OCaml TPCH 编译测试，测试覆盖 |
| 87 | web-infra-dev/rspack | 13545 | merged | performance | perf(javascript): cache non-nested export target lookups | [open](https://github.com/web-infra-dev/rspack/pull/13545) | 1 |  |
| 88 | Z3Prover/z3 | 9099 | merged | performance | ZIPT benchmark: scale to 500 files, fix seq timeout to 5s | [open](https://github.com/Z3Prover/z3/pull/9099) | 1 | 扩大/校正 ZIPT benchmark 配置 |
| 89 | ROCm/iris | 441 | open | performance | Implement power-of-two VMem allocator | [open](https://github.com/ROCm/iris/pull/441) | 1 |  |
| 90 | openclaw/openclaw | 46850 | merged | performance | fix(release): block oversized npm packs that regress low-memory startup | [open](https://github.com/openclaw/openclaw/pull/46850) | 1 |  |
| 91 | OpenMS/OpenMS | 8407 | merged | performance | Merge compatible variable modifications in CometAdapter for improved performance | [open](https://github.com/OpenMS/OpenMS/pull/8407) | 1 |  |
| 92 | openclaw/openclaw | 42821 | closed_unmerged | performance | Installer: retry killed npm/pnpm installs with low-memory settings | [open](https://github.com/openclaw/openclaw/pull/42821) | 1 |  |
| 93 | mochilang/mochi | 17569 | merged | performance | feat(rs): improve algorithms transpilation | [open](https://github.com/mochilang/mochi/pull/17569) | 1 |  |
| 94 | Azure/azure-dev | 6852 | merged | performance | Add opt-out for ARM preflight validation during `azd provision` | [open](https://github.com/Azure/azure-dev/pull/6852) | 1 | 跳过 ARM preflight 以降低 provision 时间开销 |
| 95 | cloudposse/atmos | 2152 | open | performance | fix: suppress incomplete provider lock file warning for ephemeral workdirs | [open](https://github.com/cloudposse/atmos/pull/2152) | 1 |  |
| 96 | pytorch/pytorch | 175499 | closed_unmerged | performance | [MPS] Reimplement torch.linalg.cross as a native Metal kernel | [open](https://github.com/pytorch/pytorch/pull/175499) | 1 |  |
| 97 | dotnet/runtime | 118629 | merged | performance | Remove ZipHelper.ReadBytes wrapper methods and use Stream.ReadAtLeast directly | [open](https://github.com/dotnet/runtime/pull/118629) | 1 |  |
| 98 | dotnet/runtime | 123674 | closed_unmerged | performance | Add fast path to SpanHelpers.SequenceEqual using Unsafe.AreSame | [open](https://github.com/dotnet/runtime/pull/123674) | 1 |  |
| 99 | vdaas/vald | 3421 | closed_unmerged | performance | Refactor gRPC stream and pool for performance | [open](https://github.com/vdaas/vald/pull/3421) | 1 |  |
| 100 | pytorch/pytorch | 161074 | closed_unmerged | performance | Add optional metrics to operator benchmarks | [open](https://github.com/pytorch/pytorch/pull/161074) | 1 | benchmark 增加可选性能 metrics 输出 |
