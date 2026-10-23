# Phase 2：有性能测试的 PR

文件放在哪、之后怎么接着扩，见 [FILES.md](FILES.md)。随机 6 条的性能测试能不能复现，见 [sample6_repro.md](sample6_repro.md)。

用论文 *How Do Agentic AI Systems Address Performance Optimizations?* 的判定（PR 的主要目的是不是提升性能）筛到 **992** 条时，DeepSeek 返回 402，账户余额用完，判定停在这里。这 992 条是：仓库里有性能测试，并且标题和正文被判为性能优化。名单在 [`../data/prs_performance_and_tests.csv`](../data/prs_performance_and_tests.csv)。

这 992 条目前全是 OpenAI Codex。分类是按数据表里的存放顺序往下走的，Codex 排在前面，余额用完时还没走到 Copilot、Devin、Cursor、Claude Code 和 Jules。已合并 682，关掉未合并 235，仍 open 75。

下面是上一层、更大的集合：仓库里能看到性能测试的 51,141 条，不要求这条 PR 本身是在做性能优化。

仓库里只要能看到性能测试，这个仓库里的 PR 都收进来。这条 PR 自己的 diff 不必改到那个性能测试文件。

数据来自 [AIDev-7.6M](https://huggingface.co/datasets/hao-li/AIDev-7.6M) 的 pop 子集（仓库大于 100 star，且数据集里有 commit SHA）。完整名单在 [`../data/prs_with_perf_tests.csv`](../data/prs_with_perf_tests.csv)。

## 怎么判定

先取有 commit SHA 的 197,335 条 PR。某个仓库只要在这些提交里出现过性能测试路径，就视为这个仓库有性能测试，该仓库下的全部 PR 都列入。

性能测试路径包括：

- `*_benchmark_test.go`、`*_bench_test.go`、`bench_test.go`
- `benches/*.rs`
- `*.bench.ts` / `*.bench.js`
- `*Benchmark.java`、`*PerfTest.java`、`*Macrobenchmark.kt`、`*Benchmark.cs`
- `bench/`、`benchmarks/`、`perf/`、`performance/` 目录下的 `test_*.py` 或 `*_benchmark.py`
- `src/bench/` 下的 C/C++ 基准用例

基准目录里的脚手架（`main.go`、`__init__.py`、`doc.go`、配置和示例程序）没有算进去。

## 规模

| 结局 | PR 数 |
| --- | ---: |
| 已合并 | 37,633 |
| 关掉未合并 | 11,243 |
| 仍 open | 2,265 |
| 合计 | 51,141 |

来自 358 个仓库。有 SHA 的 PR 一共 197,335 条。

按 Agent：

| Agent | PR 数 |
| --- | ---: |
| OpenAI_Codex | 23,613 |
| Copilot | 20,583 |
| Devin | 3,067 |
| Cursor | 1,631 |
| Claude_Code | 1,447 |
| Google_Jules | 800 |

## 仓库

每个仓库下列出看到的性能测试路径，PR 数是该仓库收进这份名单的条数。

| 仓库 | PR 数 | 看到的性能测试 |
| --- | ---: | --- |
| mochilang/mochi | 13,461 | runtime/vm/join_bench_test.go / tests/aster/x/py/bench_block.py / tests/transpiler/x/py/bench_block.py |
| github/gh-aw | 8,566 | pkg/workflow/compiler_benchmark_test.go / pkg/workflow/expressions_benchmark_test.go / pkg/workflow/compiler_performance_benchmark_test.go / pkg/workflow/mcp_benchmark_test.go / pkg/cli/compile_security_benchmark_test.go |
| MontrealAI/AGI-Alpha-Agent-v0 | 4,102 | scripts/run_replay_bench.py |
| openclaw/openclaw | 2,225 | apps/android/benchmark/src/main/java/ai/openclaw/android/benchmark/StartupMacrobenchmark.kt / apps/android/benchmark/src/main/java/ai/openclaw/app/benchmark/StartupMacrobenchmark.kt |
| fastrepl/char | 1,303 | crates/denoise/benches/denoise_bench.rs / crates/aec/benches/aec_bench.rs / crates/cactus/benches/vad.rs / apps/desktop/src/store/tinybase/persister.bench.ts |
| dotnet/runtime | 945 | src/libraries/System.Runtime/tests/PerformanceTests/FileStreamBufferingBenchmark/FileStreamBufferingBenchmark.cs |
| PrefectHQ/prefect | 858 | src/integrations/prefect-dbt/benches/bench_orchestrator.py |
| devantler-tech/ksail | 744 | pkg/client/docker/engine_bench_test.go / pkg/client/docker/registry_bench_test.go / pkg/client/kubectl/client_bench_test.go / pkg/cli/parallel/executor_benchmark_test.go / pkg/client/argocd/manager_bench_test.go |
| fern-api/fern | 721 | generators/typescript/utils/core-utilities/tests/unit/schemas/benchmarks/serialization.bench.ts |
| SkBlaz/py3plex | 686 | tests/test_visualization_benchmark.py / tests/test_benchmark_budget_fairness.py / tests/test_benchmark_dsl_basic.py / tests/test_benchmark_integration.py / gui/ci/api-tests/test_performance_optimizations.py |
| OliverZhaohaibin/iPhotron-LocalPhotoAlbumManager | 660 | tests/test_performance_sorting.py |
| Azure/azure-sdk-for-net | 618 | sdk/tables/Azure.Data.Tables/tests/perf/ModelBindingBenchmark.cs / sdk/core/Azure.Core/perf/FastPropertyBagBenchmark.cs / sdk/core/Azure.Core/perf/Utf8JsonRequestContentBenchmark.cs / sdk/core/Azure.Core/perf/GZipUtf8JsonRequestContentBenchmark.cs |
| Z3Prover/z3 | 513 | src/test/optional_benchmark.cpp |
| github/gh-aw-mcpg | 474 | internal/middleware/jqschema_bench_test.go |
| spellshift/realm | 444 | tavern/internal/cryptocodec/cryptocodec_bench_test.go / tavern/internal/benchmarks/portal_benchmark_test.go / implants/lib/eldritchv2/eldritch-core/benches/interpreter.rs / implants/lib/eldritchv2/eldritch-core/benches/builtins.rs / implants/lib/eldritch/benches/reverse_shell.rs |
| microsoft/typespec | 440 | packages/http-client-csharp/generator/Microsoft.TypeSpec.Generator/perf/CodeWriterBenchmark.cs / packages/http-client-csharp/generator/Microsoft.TypeSpec.Generator/perf/ModelReaderWriterContextDefinitionBenchmark.cs |
| rudrankriyam/App-Store-Connect-CLI | 420 | internal/screenshots/frame_bench_test.go |
| vinhnx/VTCode | 285 | benches/system_benchmarks.rs / benches/search_benchmark.rs / docs/benches/system_benchmarks.rs / docs/benches/search_benchmark.rs / benches/tree_sitter_benchmark.rs |
| microsoft/typescript-go | 280 | _packages/api/test/async/api.bench.ts / _packages/api/test/sync/api.bench.ts / _packages/api/test/api.bench.ts / internal/vfs/vfsmatch/bench_test.go / _packages/api/test/api.async.bench.ts |
| tenstorrent/tt-metal | 278 | models/experimental/tt_dit/tests/models/flux1/test_performance_flux1.py / models/experimental/tt_dit/tests/models/qwenimage/test_performance_qwenimage.py / models/experimental/tt_dit/tests/models/wan2_2/test_performance_wan.py / tests/ttnn/benchmark/cpp/matmul/test_matmul_benchmark.cpp / tests/ttnn/tracy/test_perf_op_report.py |
| getsentry/sentry | 276 | tests/sentry/performance_issues/test_performance_detection.py |
| kubb-labs/kubb | 276 | tests/performance/transformer.bench.ts / e2e/src/__tests__/performance/plugin-generation.bench.ts / packages/core/src/__tests__/performance/plugin-generation.bench.ts |
| dotnet/sdk | 274 | test/benchmarks/StaticWebAssetsSdk/EmptyBenchmark.cs |
| oxc-project/oxc | 262 | tasks/benchmark/benches/lexer.rs / tasks/benchmark/benches/minifier.rs / crates/oxc_parser/benches/lexer_performance.rs / napi/parser/bench.bench.js |
| dotnet/aspnetcore | 255 | src/Http/Http/perf/Microbenchmarks/ValidatableTypesBenchmark.cs |
| OpenMS/OpenMS | 237 | comprehensive_boost_benchmark.cpp |
| Azure/azure-dev | 230 | cli/azd/pkg/containerapps/container_app_benchmark_test.go |
| marin-community/marin | 224 | lib/levanter/scripts/bench/bench_mamba3_mimo_xla.py / lib/levanter/scripts/bench/bench_mamba3_xla.py / lib/dupekit/tests/bench/test_batch_tuning.py / lib/dupekit/tests/bench/test_dedupe.py / lib/dupekit/tests/bench/test_hashing.py |
| asynkron/protoactor-dotnet | 216 | benchmarks/ClusterMicroBenchmarks/ConcurrentSpawnBenchmark.cs / benchmarks/ClusterMicroBenchmarks/InProcessClusterBatchRequestBenchmark.cs / benchmarks/ClusterMicroBenchmarks/InProcessClusterRequestBenchmark.cs |
| OpenRakis/Spice86 | 214 | src/Spice86.MicroBenchmarkTemplate/BreakpointCheckBenchmark.cs / src/Spice86.MicroBenchmarkTemplate/HasActiveBreakpointsBenchmark.cs / tests/Spice86.Tests/BreakpointPerformanceBenchmark.cs / src/Spice86.MicroBenchmarkTemplate/MandelbrotPerformanceBenchmark.cs / src/Spice86.MicroBenchmarkTemplate/MixerChannelIterationBenchmark.cs |
| MudBlazor/MudBlazor | 191 | src/MudBlazor.Benchmarks/IdentifierBenchmark.cs / src/MudBlazor.Benchmarks/BeforeAfterComparisonBenchmark.cs / src/MudBlazor.Benchmarks/DelegateInvocationBenchmark.cs / src/MudBlazor.Benchmarks/ParameterStateBasicOperationsBenchmark.cs / src/MudBlazor.Benchmarks/ParameterStateComparerBenchmark.cs |
| open-metadata/OpenMetadata | 184 | openmetadata-service/src/test/java/org/openmetadata/service/security/CachedPermissionPerformanceTest.java |
| web-infra-dev/rspack | 181 | xtask/benchmark/benches/benches.rs / xtask/benchmark/benches/groups/compilation_stages.rs / tests/bench/module-graph-api.bench.ts / xtask/benchmark/benches/groups/build_chunk_graph.rs / xtask/benchmark/benches/groups/module_graph_api.rs |
| OpenHFT/Chronicle-Wire | 165 | src/test/java/net/openhft/chronicle/wire/BinaryWirePerfTest.java / src/test/java/net/openhft/chronicle/wire/AbstractTimestampLongConverterJLBHBenchmark.java |
| pytorch/pytorch | 157 | benchmarks/diffusion/compile_benchmark.py / benchmarks/distributed/bench_nvshmem_tile_reduce.py / benchmarks/dynamo/microbenchmarks/bench_mm_fusion.py / benchmarks/dynamo/microbenchmarks/tensor_layout_mini_benchmark.py / benchmarks/fastrnns/test_bench.py |
| datahub-project/datahub | 154 | metadata-ingestion/tests/performance/test_graphql_projection_perf.py / metadata-ingestion/tests/performance/sql_parsing/test_sql_aggregator.py |
| aptos-labs/aptos-core | 151 | network/quic-like-udp/benches/transport_bench.rs / network/qnuc/benches/transport_bench.rs / crates/aptos-dkg/benches/pvss.rs / crates/aptos-crypto/benches/ed25519.rs / crates/aptos-crypto/benches/ristretto255.rs |
| SOVEREIGN-NET/The-Sovereign-Network | 147 | lib-crypto/benches/crypto_benchmarks.rs |
| gui-cs/Terminal.Gui | 144 | Tests/Benchmarks/Layout/DimAutoBenchmark.cs / Tests/Benchmarks/ViewBase/ScenarioMemoryBenchmark.cs / Tests/Benchmarks/ViewBase/ViewMemoryBenchmark.cs |
| zeroclaw-labs/zeroclaw | 141 | benches/agent_benchmarks.rs |
| Azure/azure-sdk-for-java | 134 | sdk/cosmos/azure-cosmos-benchmark/src/main/java/com/azure/cosmos/benchmark/AsyncBenchmark.java |
| rmusser01/tldw_server | 133 | tldw_Server_API/tests/Docs/test_benchmark_guide_discoverability.py |
| ROCm/iris | 132 | tests/unittests/test_bench.py |
| ydb-platform/ydb | 129 | ydb/public/lib/ydb_cli/commands/ydb_benchmark.cpp |
| 567-labs/instructor | 128 | accurate_token_benchmark.py |
| Cap-go/capgo | 125 | benches/cloudflare-utils.bench.ts / benches/device-comparison.bench.ts / benches/password-policy.bench.ts |
| vdaas/vald | 125 | internal/core/algorithm/ngt/ngt_bench_test.go / internal/io/copy_bench_test.go / hack/benchmark/core/benchmark/benchmark_test.go / hack/benchmark/core/benchmark/option_test.go / hack/benchmark/core/benchmark/strategy/bulk_insert_commit_test.go |
| StarRocks/starrocks | 124 | be/src/bench/datetime_cast_bench.cpp |
| elsa-workflows/elsa-core | 124 | test/performance/Elsa.Workflows.PerformanceTests/ConsoleActivitiesBenchmark.cs |
| DannyMac180/meta-agent | 122 | tests/test_embedding_benchmark.py / src/meta_agent/cli/embedding_benchmark.py / src/meta_agent/embedding_benchmark.py |
| nearai/ironclaw | 122 | crates/ironclaw_safety/benches/safety_check.rs / crates/ironclaw_safety/benches/safety_pipeline.rs / benches/safety_check.rs / benches/safety_pipeline.rs |
| NethermindEth/nethermind | 118 | src/Nethermind/Nethermind.Evm.Benchmark/BlockProcessingBenchmark.cs / src/Nethermind/Nethermind.Evm.Benchmark/TxProcessingBenchmark.cs / src/Nethermind/Nethermind.Evm.Benchmark/WarmupBenchmark.cs / src/Nethermind/Nethermind.Evm.Benchmark/EvmOpcodesBenchmark.cs / src/Nethermind/Nethermind.Trie.Benchmark/TreeCommitterBenchmark.cs |
| cyw0ng95/sqlvibe | 118 | internal/VM/bench_test.go / internal/TS/Benchmark/benchmark_test.go / internal/TS/Benchmark/benchmark_v0.9.6_test.go / internal/TS/Benchmark/benchmark_v0.8.3_test.go / internal/TS/Benchmark/benchmark_v0.9.16_test.go |
| go-vikunja/vikunja | 118 | pkg/models/task_search_bench_test.go |
| gluesql/gluesql | 116 | storages/sled-storage/benches/sled_benchmark.rs |
| jstime/jstime | 115 | core/benches/runtime_bench.rs / core/benches/crypto_bench.rs / core/benches/module_cache_bench.rs |
| dvlin-dev/moryflow | 110 | apps/moryflow/pc/src/main/skills/builtin/skill-creator/scripts/aggregate_benchmark.py |
| cockroachdb/cockroach | 103 | pkg/backup/bench_test.go |
| microsoft/onnxruntime | 102 | onnxruntime/test/mlas/bench/bench_sconv.cpp / onnxruntime/test/python/transformers/test_gpt2_benchmark.py |
| AstrBotDevs/AstrBot | 101 | tests/performance/test_benchmarks.py |
| scalar/scalar | 101 | packages/helpers/src/markdown/get-markdown-headings.bench.ts |
| 1c-syntax/bsl-language-server | 100 | src/jmh/java/com/github/_1c_syntax/bsl/languageserver/IncrementalTextChangeBenchmark.java |
| vllm-project/vllm | 100 | benchmarks/fused_kernels/silu_mul_block_quant_benchmark.py / tests/benchmarks/test_random_dataset.py / benchmarks/kernels/bench_block_fp8_gemm.py / benchmarks/kernels/bench_per_token_quant_fp8.py / benchmarks/multi_turn/bench_dataset.py |
| PrimeIntellect-ai/verifiers | 98 | environments/terminal_bench/terminal_bench.py / environments/tau2_bench/tau2_bench.py |
| marin-community/levanter | 96 | scripts/tpu_transfer_benchmark.py |
| cloudposse/atmos | 94 | pkg/merge/provenance_benchmark_test.go / internal/exec/describe_affected_benchmark_test.go / internal/exec/yaml_func_resolution_context_bench_test.go / pkg/perf/perf_test.go |
| open-telemetry/opentelemetry-java-instrumentation | 91 | benchmark-overhead-jmh/src/jmh/java/io/opentelemetry/javaagent/benchmark/servlet/ServletBenchmark.java / instrumentation-api/src/jmh/java/io/opentelemetry/instrumentation/api/cache/CacheBenchmark.java / instrumentation-api/src/jmh/java/io/opentelemetry/instrumentation/api/instrumenter/InstrumenterBenchmark.java |
| BoundaryML/baml | 90 | baml_language/crates/baml_vm/benches/fib.rs |
| RocketChat/Rocket.Chat | 88 | packages/message-parser/benchmarks/parser.bench.ts |
| risingwavelabs/risingwave | 88 | src/storage/benches/bench_merge_iter.rs / src/storage/benches/bench_compactor.rs / src/storage/benches/bench_multi_builder.rs / src/storage/benches/bench_block_cache.rs / src/storage/benches/bench_table_watermarks.rs |
| langgenius/dify | 87 | api/tests/integration_tests/vdb/oceanbase/bench_oceanbase.py |
| celestiaorg/celestia-core | 86 | mempool/bench_test.go / mempool/cache_bench_test.go / mempool/cat/pool_bench_test.go / store/bench_test.go |
| frostwire/frostwire | 78 | common/src/test/java/com/frostwire/util/StringSanitizersBenchmark.java / common/src/test/java/com/frostwire/search/PerformersHelperPerformanceTest.java / common/src/test/java/com/frostwire/search/SearchManagerPerformanceTest.java / common/src/test/java/com/frostwire/search/LevenshteinBenchmark.java |
| gastownhall/beads | 78 | internal/storage/sqlite/compact_bench_test.go / internal/storage/sqlite/cycle_bench_test.go / internal/storage/sqlite/sqlite_bench_test.go |
| mediar-ai/terminator | 75 | terminator-observability/benches/overhead.rs |
| vercel/workflow | 74 | packages/core/e2e/bench.bench.ts |
| nevalang/neva | 73 | benchmarks/bench_test.go / internal/runtime/message_bench_test.go / benchmarks/message_passing/bench_test.go |
| vercel/next.js | 72 | crates/next-code-frame/benches/code_frame_bench.rs / turbopack/crates/turbo-tasks-backend/benches/overhead.rs / turbopack/crates/turbo-tasks-backend/benches/scope_stress.rs / turbopack/crates/turbo-tasks-backend/benches/stress.rs / crates/next-api/benches/hmr.rs |
| OrchardCMS/OrchardCore | 71 | test/OrchardCore.Benchmarks/ArgumentsBenchmark.cs / test/OrchardCore.Benchmarks/FlatPositionComparerBenchmark.cs / test/OrchardCore.Benchmarks/ShapeDescriptorIndexBenchmark.cs |
| sqlfluff/sqlfluff | 70 | sqlfluffrs/benches/parser_bench.rs / sqlfluffrs/benches/baseline_phase1.rs / sqlfluffrs/benches/delimited_performance.rs |
| voidzero-dev/vite-plus | 66 | bench/benches/workspace_load.rs |
| jlucaso1/whatsapp-rust | 65 | benches/optimization_bench.rs / wacore/binary/benches/binary_benchmark.rs / benches/encryption_benchmark.rs / wacore/libsignal/benches/libsignal_benchmark.rs |
| valkey-io/valkey-glide | 65 | benchmarks/python/python_async_benchmark.py / benchmarks/python/python_sync_benchmark.py / glide-core/benches/memory_benchmark.rs |
| microsoft/CCF | 64 | src/tasks/test/bench/merge_bench.cpp / src/tasks/test/bench/contention_bench.cpp / src/tasks/test/bench/flush_all_tasks.h / src/tasks/test/bench/merge_sort.h |
| litedb-org/LiteDB | 62 | LiteDB.Benchmarks/Benchmarks/Serialization/BufferSerializationBenchmark.cs / LiteDB.Benchmarks/Benchmarks/Spatial/SpatialNearBenchmark.cs / LiteDB.Benchmarks/Benchmarks/Spatial/SpatialQueryBenchmark.cs |
| Puchaczov/Musoq | 61 | Musoq.Benchmarks/Components/ExtendedExecutionBenchmark.cs / Musoq.Benchmarks/Components/CompilationBenchmark.cs / src/dotnet/Musoq.Benchmarks/CompilationPipelineBenchmark.cs / src/dotnet/Musoq.Benchmarks/CteDependencyGraphBenchmark.cs / src/dotnet/Musoq.Benchmarks/InterpretationBenchmark.cs |
| RailtownAI/railtracks | 58 | scripts/evaluations/sync_async_benchmark.py |
| TanStack/router | 58 | benchmarks/client-nav/react/speed.bench.tsx / benchmarks/client-nav/solid/speed.bench.tsx / benchmarks/client-nav/vue/speed.bench.tsx / benchmarks/ssr/react/speed.bench.ts / benchmarks/ssr/solid/speed.bench.ts |
| pulearn/pulearn | 58 | tests/test_benchmark_datasets.py / tests/test_benchmark_runner.py |
| fighthealthinsurance/fighthealthinsurance | 57 | tests/sync/test_performance_settings.py |
| pingcap/tidb | 57 | pkg/util/topsql/stmtstats/aggregator_bench_test.go |
| Azure/azure-sdk-for-rust | 56 | sdk/core/azure_core/benches/benchmarks.rs / sdk/core/azure_core/benches/deserialization.rs |
| near/nearcore | 56 | core/primitives/benches/serialization.rs / core/store/benches/finalize_bench.rs / core/store/benches/store_bench.rs / core/store/benches/trie_bench.rs |
| grafana/grafana | 55 | pkg/storage/unified/sql/shorturl_benchmark_test.go / pkg/storage/unified/migrations/bulk_client_benchmark_test.go |
| max-sixty/worktrunk | 55 | benches/list.rs / benches/cow_copy.rs / benches/completion.rs |
| mui/mui-x | 55 | test/performance-charts/tests/ScatterChartPro.bench.tsx / packages/x-charts/src/internals/domUtils.bench.ts |
| OpenHFT/Chronicle-Threads | 53 | src/test/java/net/openhft/chronicle/threads/LongPauserBenchmark.java |
| dotnet/dotnet | 51 | src/razor/src/Razor/benchmarks/Microsoft.AspNetCore.Razor.Microbenchmarks/Formatting/DocumentFormattingBenchmark.cs |
| ealush/vest | 51 | packages/vest/bench/granular/enforce.bench.ts / packages/vest/bench/enforce-async.bench.ts / packages/vest/bench/complex-flows.bench.ts / packages/vest/bench/conditional-isolates.bench.ts / packages/vest/bench/dynamic-each-group.bench.ts |
| OpenHFT/Chronicle-Logger | 50 | logger-slf4j-2/src/test/java/net/openhft/chronicle/logger/slf4j2/Slf4jChronicleLoggerPerfTest.java / benchmark/src/main/java/net/openhft/Lo4J2PerfTest.java |
| celestiaorg/celestia-app | 49 | app/benchmarks/benchmark_pfb_test.go / app/benchmarks/gas_estimator_test.go / app/benchmarks/benchmark_ibc_update_client_test.go / app/benchmarks/benchmark_msg_send_test.go |
| dotnet/razor | 49 | src/Razor/benchmarks/Microsoft.AspNetCore.Razor.Microbenchmarks/Serialization/CompletionListSerializationBenchmark.cs |
| projectcalico/calico | 48 | felix/calc/calc_graph_bench_test.go / felix/bpf/proxy/proxy_bench_test.go / goldmane/pkg/storage/add_flow_bench_test.go |
| Protocol-Lattice/go-agent | 47 | pkg/memory/engine/engine_bench_test.go / pkg/memory/engine_bench_test.go |
| netdata/netdata | 46 | src/go/plugin/framework/chartengine/planner_bench_test.go / src/go/pkg/prometheus/assembler_bench_test.go / src/go/pkg/prometheus/promscrapemodel/parse_bench_test.go / src/go/plugin/go.d/collector/prometheus/relabel/relabel_bench_test.go / src/go/pkg/prometheus/promscrapemodel/assembler_bench_test.go |
| microsoft/openvmm | 42 | vm/devices/storage/storvsp/benches/ioperf.rs |
| javalin/javalin | 41 | javalin/src/test/java/io/javalin/performance/PathMatcherBenchmark.java |
| microsoft/FluidFramework | 41 | packages/dds/tree/src/test/shared-tree-core/edit-manager/editManager.bench.ts / packages/dds/tree/src/test/shared-tree/opSize.bench.ts / packages/dds/tree/src/test/domains/json/jsonCursor.bench.ts / packages/dds/tree/src/test/shared-tree/summary.bench.ts |
| tphakala/birdnet-go | 41 | internal/myaudio/audio_conversion_bench_test.go / internal/telemetry/optimized_benchmark_test.go |
| Azure/azure-service-operator | 39 | v2/test/perf/perf_helpers_test.go / v2/test/perf/perf_test.go / v2/test/perf/resource_factories_test.go / v2/test/perf/suite_test.go |
| nexi-lab/nexus | 39 | tests/benchmarks/bench_write_observer.py / tests/benchmarks/bench_factory_boot.py / tests/benchmarks/test_service_delegation.py / tests/e2e/self_contained/test_performance_tuning_e2e.py / tests/unit/core/test_performance_tuning.py |
| EuroEval/EuroEval | 38 | tests/test_benchmark_modules/test_vllm.py / tests/test_speed_benchmark.py / tests/test_benchmark_modules/test_litellm.py |
| gridaco/grida | 38 | crates/grida-canvas/benches/bench_rectangles.rs |
| microsoft/DiskANN | 38 | diskann-providers/benches/benchmarks/copy_aligned_data_bench.rs / diskann-providers/benches/benchmarks_iai/copy_aligned_data_bench_iai.rs |
| roboflow/rf-detr | 38 | tests/benchmarks/test_inference_coco.py / tests/benchmarks/test_training_synthetic.py / tests/benchmarks/test_coco_inference.py / tests/benchmarks/test_coco_inference_ptl.py / tests/benchmarks/test_synthetic_convergence_ptl.py |
| doobidoo/mcp-memory-service | 37 | tests/performance/test_background_sync.py / tests/performance/test_hybrid_live.py |
| roboflow/inference | 37 | tests/benchmarks/core/test_speed_benchmark.py |
| ta4j/ta4j | 37 | ta4j-examples/src/main/java/ta4jexamples/num/DecimalNumPrecisionPerformanceTest.java / ta4j-core/src/test/java/org/ta4j/core/num/DecimalNumPrecisionPerformanceTest.java |
| visgl/loaders.gl | 37 | modules/parquet/test/parquet.bench.ts / modules/shapefile/test/shapefile.bench.ts / modules/shapefile/test/shp.bench.ts / modules/json/test/lib/clarinet/clarinet.bench.js |
| mattermost/mattermost-plugin-agents | 36 | llm/token_tracking_bench_test.go / streaming/streaming_bench_test.go |
| quarylabs/sqruff | 36 | crates/lib/benches/depth_map.rs / crates/lib/benches/fix.rs / crates/lib/benches/parsing.rs / crates/lib/benches/shims/global_alloc_overwrite.rs |
| ruvnet/ruflo | 35 | benchmark/run_swe_bench.py / src/__tests__/benchmarks/performance.bench.ts / benchmark/test_simple_run.py / benchmark/tests/unit/test_benchmark_engine.py / benchmark/tests/unit/test_comprehensive_models.py |
| Azure/azure-cosmos-dotnet-v3 | 34 | Microsoft.Azure.Cosmos.Encryption.Custom/tests/Microsoft.Azure.Cosmos.Encryption.Custom.Performance.Tests/EncryptionBenchmark.cs / Microsoft.Azure.Cosmos/tests/Microsoft.Azure.Cosmos.Performance.Tests/Benchmarks/CollectionRoutingMapBenchmark.cs / Microsoft.Azure.Cosmos/tests/Microsoft.Azure.Cosmos.Performance.Tests/Linq/SubtreeEvaluatorBenchmark.cs |
| dotnet/orleans | 34 | test/Benchmarks.AdoNet/Streaming/MessageDequeueingBenchmark.cs / test/Benchmarks.AdoNet/Streaming/MessageQueueingBenchmark.cs / test/Benchmarks/GrainStorage/GrainStorageBenchmark.cs / test/Benchmarks/MapReduce/MapReduceBenchmark.cs / test/Benchmarks/Ping/FanoutBenchmark.cs |
| mabel-dev/opteryx | 34 | tests/performance/test_regexp_replace_performance.py |
| NousResearch/hermes-agent | 33 | tests/environments/benchmarks/test_terminalbench2_env_security.py |
| denoland/deno | 33 | tests/bench_util/benches/utf8.rs |
| meteostat/meteostat | 33 | benchmarks/interpolation_benchmark.py |
| FirelyTeam/firely-net-sdk | 32 | src/Benchmarks/DateTimeBenchmark.cs / src/Benchmarks/DeserializationBenchmark.cs / src/CrossVersionBenchmarks/FhirPathBenchmark.cs / src/CrossVersionBenchmarks/PocoParserBenchmark.cs |
| kvcache-ai/Mooncake | 32 | mooncake-transfer-engine/example/efa_latency_bench.py |
| leerob/pixo | 32 | benches/comparison.rs / benches/encode_benchmark.rs / benches/decode_benchmark.rs / benches/components.rs / benches/corpus.rs |
| paradigmxyz/reth | 32 | crates/engine/tree/benches/sparse_trie_small_work.rs / crates/chain-state/benches/canonical_hashes_range.rs / crates/engine/tree/benches/state_root_task.rs / crates/engine/tree/benches/validation_parallel.rs |
| runmat-org/runmat | 31 | benchmarks/benchmarks/.harness/run_bench.py |
| sgl-project/sglang | 31 | benchmark/mmmu/bench_sglang.py / sgl-model-gateway/benches/request_processing.rs / sgl-model-gateway/benches/tokenizer_benchmark.rs / sgl-model-gateway/benches/tool_parser_benchmark.rs / benchmark/hf3fs/bench_client.py |
| skypilot-org/skypilot | 31 | rust/skypilot-utils/benches/io_benchmarks.rs / rust/skypilot-utils/benches/string_benchmarks.rs / rust/skypilot-utils/benches/process_benchmarks.rs |
| vllm-project/vllm-omni | 31 | tests/benchmarks/test_serve_cli.py / tests/dfx/perf/scripts/run_benchmark.py / tests/benchmarks/test_video_accuracy_bench_utils.py / benchmarks/accuracy/image_to_image/gedit_bench.py / benchmarks/accuracy/image_to_image/run_gedit_bench.py |
| jhlee0409/claude-code-history-viewer | 30 | src-tauri/benches/performance.rs |
| maplibre/martin | 30 | martin/benches/postgres_discovery.rs |
| sei-protocol/sei-chain | 30 | app/benchmark/logger_test.go |
| tbsalling/aismessages | 30 | src/test/java/dk/tbsalling/aismessages/ais/BitStringPerformanceTest.java / src/test/java/dk/tbsalling/aismessages/ais/RealWorldPerformanceTest.java |
| Southclaws/storyden | 29 | tests/plugin/plugin_rpc_benchmark_test.go |
| eiriktsarpalis/PolyType | 29 | tests/PolyType.Benchmarks/JsonBenchmark.cs / tests/PolyType.Benchmarks/AttributeProviderBenchmark.cs |
| netcorepal/netcorepal-cloud-framework | 29 | test/NetCorePal.Extensions.Performance.Tests/Database/RepositoryBenchmark.cs / test/NetCorePal.Extensions.Performance.Tests/Domain/AggregateRootBenchmark.cs / test/NetCorePal.Extensions.Performance.Tests/Framework/DependencyInjectionBenchmark.cs / test/NetCorePal.Extensions.Performance.Tests/Framework/EntityIdBenchmark.cs / test/NetCorePal.Extensions.Performance.Tests/Framework/JsonSerializationBenchmark.cs |
| oxc-project/tsgolint | 29 | internal/linter/linter_bench_test.go / internal/linter/source_code_fixer_bench_test.go / internal/utils/utils_bench_test.go |
| stackrox/stackrox | 29 | central/processindicator_no_serialized/store/postgres/bench_test.go / central/processindicator_jsonb/store/postgres/bench_test.go |
| zerx-lab/wordZero | 29 | benchmark/golang/benchmark_test.go |
| basicmachines-co/basic-memory | 28 | test-int/test_search_performance_benchmark.py |
| rocicorp/mono | 27 | packages/replicache/src/size-of-value.bench.ts / packages/zql-benchmarks/src/planner-cost.bench.ts / packages/zero-client/src/client/zero.bench.ts / packages/zql-benchmarks/src/chinook-manual-cases.bench.ts / packages/zql-benchmarks/src/planner-hydration.bench.ts |
| NVIDIA/cuda-python | 26 | cuda_bindings/benchmarks/test_launch_latency.py / cuda_bindings/benchmarks/test_pointer_attributes.py |
| OffchainLabs/nitro | 26 | crates/prover/benches/merkle_bench.rs |
| erigontech/erigon | 26 | db/recsplit/eliasfano32/elias_fano_seek_bench_test.go / db/test/domain_shared_bench_test.go / execution/commitment/commitment_bench_test.go / common/log/v3/bench_test.go / db/seg/decompress_bench_test.go |
| lhl/strix-halo-testing | 26 | llm-bench/amd_llm_benchmark.py / llm_bench/amd_llm_benchmark.py |
| zama-ai/fhevm | 26 | coprocessor/fhevm-engine/tfhe-worker/benches/dex.rs / coprocessor/fhevm-engine/tfhe-worker/benches/erc20.rs / coprocessor/fhevm-engine/tfhe-worker/benches/synthetics.rs / coprocessor/fhevm-engine/tfhe-worker/benches/utils.rs |
| Quantco/dataframely | 25 | tests/benches/test_collection.py / tests/benches/test_failure.py / tests/benches/test_schema.py |
| bpwhelan/GameSentenceMiner | 25 | scripts/ocr_metrics_benchmark.py / tests/util/test_benchmark_stats.py |
| commonwarexyz/monorepo | 25 | cryptography/src/kzg/benches/bench.rs / cryptography/src/kzg/benches/commit.rs / cryptography/src/kzg/benches/open.rs / cryptography/src/kzg/benches/verify.rs / stream/src/benches/bench.rs |
| czlonkowski/n8n-mcp | 25 | tests/benchmarks/database-queries.bench.ts / tests/benchmarks/mcp-tools.bench.ts / tests/benchmarks/node-loading.bench.ts / tests/benchmarks/sample.bench.ts / tests/benchmarks/search-operations.bench.ts |
| feast-dev/feast | 25 | sdk/python/tests/benchmarks/test_key_encoding_benchmarks.py |
| flagos-ai/FlagGems | 25 | benchmark/test_reduction_perf.py / benchmark/test_smooth_l1_loss_perf.py / benchmark/test_special_perf.py / benchmark/test_unary_pointwise_perf.py |
| open-telemetry/opentelemetry-rust | 25 | opentelemetry-sdk/benches/batch_span_processor.rs / opentelemetry-sdk/benches/span.rs / opentelemetry-appender-tracing/benches/log-attributes.rs / opentelemetry-appender-tracing/benches/logs.rs / opentelemetry-appender-tracing/benches/span-attributes.rs |
| apache/spark | 24 | python/benchmarks/bench_arrow.py |
| probelabs/probe | 24 | benches/simd_benchmarks.rs |
| samwillis/solidtype | 24 | packages/core/bench/model.bench.ts / packages/core/bench/solver.bench.ts / packages/core/bench/tessellation.bench.ts |
| foxglove/mcap | 23 | rust/mcap/benches/reader.rs |
| ctrlplanedev/ctrlplane | 22 | apps/workspace-engine/pkg/workspace/relationships/compute/incremental_bench_test.go |
| gradle/gradle | 22 | platforms/core-runtime/native/src/jmh/java/org/gradle/internal/nativeintegration/filesystem/FileMetadataAccessorBenchmark.java / platforms/core-runtime/collections/src/jmh/java/org/gradle/internal/collect/bench/PersistentArrayBenchmark.java / platforms/core-runtime/collections/src/jmh/java/org/gradle/internal/collect/bench/PersistentSetBenchmark.java |
| hyperlight-dev/hyperlight | 22 | src/hyperlight_host/benches/benchmarks.rs |
| router-for-me/CLIProxyAPI | 22 | sdk/cliproxy/auth/scheduler_large_benchmark_test.go / internal/translator/codex/openai/responses/codex_openai-responses_request_benchmark_test.go / internal/translator/codex/claude/codex_claude_request_benchmark_test.go / internal/util/gemini_schema_benchmark_test.go / sdk/cliproxy/auth/scheduler_benchmark_test.go |
| sebastienros/jint | 22 | Jint.Benchmark/PreparedScriptBenchmark.cs |
| iree-org/iree | 21 | runtime/src/iree/async/cts/socket/socket_benchmark.cc / runtime/src/iree/async/cts/buffer/pool_benchmark.cc / runtime/src/iree/async/cts/core/dispatch_scalability_benchmark.cc / runtime/src/iree/async/cts/core/sequence_benchmark.cc / runtime/src/iree/async/cts/event/event_benchmark.cc |
| kornia/kornia-rs | 21 | crates/kornia-tensor-ops/benches/bench_dnn.rs / crates/kornia-nn/benches/bench_linear.rs |
| microsoft/amplifier | 21 | tests/terminal_bench/run_terminal_bench.py |
| onflow/flow-go | 21 | consensus/hotstuff/model/timeout_bench_test.go / engine/access/rpc/connection/grpc_compression_benchmark_test.go / engine/execution/computation/manager_benchmark_test.go / integration/benchmark/load/load_type_test.go / fvm/fvm_bench_test.go |
| ray-project/ray | 21 | release/nightly_tests/dataset/multi_node_train_benchmark.py |
| tlepoint/fhe.rs | 21 | crates/fhe-math/benches/ntt.rs / crates/fhe-math/benches/rns.rs / crates/fhe-math/benches/rq.rs / crates/fhe-math/benches/zq.rs / crates/fhe/benches/bfv.rs |
| evmts/guillotine | 20 | bench/official/evms/evmone/runner.cpp |
| shortlink-org/shortlink | 20 | boundaries/link/internal/infrastructure/repository/crud/mongo/mongo_benchmark_test.go / boundaries/link/internal/infrastructure/repository/crud/postgres/postgres_benchmark_test.go / boundaries/link/internal/infrastructure/repository/crud/ram/ram_benchmark_test.go / docs/ADR/decisions/proof/ADR-0007/serialization_bench_test.go / pkg/types/partmap/bench_test.go |
| spiriMirror/libuipc | 20 | apps/tests/sim_case/62_fem_mas_contact_aware_benchmark.cpp / apps/tests/sim_case/59_fem_mas_vs_diag_benchmark.cpp |
| dapplo/Dapplo.Windows | 19 | src/Dapplo.Windows.Tests.Benchmarks/InteropWindowBenchmark.cs |
| erpc/erpc | 19 | erpc/networks_bench_test.go / health/tracker_benchmark_test.go / health/tracker_bench_test.go |
| langchain-ai/deepagents | 19 | libs/cli/tests/integration_tests/benchmarks/test_startup_benchmarks.py |
| agent-sh/agnix | 18 | crates/agnix-core/benches/fixtures.rs |
| anthropics/claude-code | 18 | rust/crates/claude-tests/benches/performance.rs |
| graphql-java/graphql-java | 18 | src/jmh/java/benchmark/BuildSchemaBenchmark.java / src/jmh/java/benchmark/CreateSchemaBenchmark.java / src/jmh/java/benchmark/ExecutionBenchmark.java / src/jmh/java/benchmark/IntrospectionBenchmark.java / src/jmh/java/benchmark/OverlappingFieldValidationBenchmark.java |
| microsoft/debug-gym | 18 | debug_gym/gym/envs/swe_bench.py / tests/gym/envs/test_swe_bench.py |
| nissl-lab/npoi | 18 | benchmarks/NPOI.Benchmarks/AddRowBenchmark.cs / benchmarks/NPOI.Benchmarks/LargeExcelFileBenchmark.cs / benchmarks/NPOI.Benchmarks/LargeStylesBenchmark.cs |
| tempoxyz/tempo | 18 | crates/precompiles/benches/tempo_precompiles.rs |
| elastic/beats | 17 | libbeat/processors/actions/addagentmetadata/add_agent_metadata_bench_test.go |
| goplus/llgo | 17 | test/std/math/math_bench_test.go |
| grafana/grafana-infinity-datasource | 17 | pkg/infinity/backend_bench_test.go / pkg/infinity/client_bench_test.go / pkg/infinity/headers_bench_test.go / pkg/infinity/remote_bench_test.go |
| juspay/hyperswitch | 17 | crates/euclid/benches/backends.rs |
| microsoft/go-mssqldb | 17 | messages_benchmark_test.go |
| open-policy-agent/gatekeeper | 17 | pkg/gator/bench/bench_test.go / pkg/gator/bench/compare_test.go / pkg/gator/bench/metrics_test.go / pkg/gator/bench/output_test.go / pkg/mutation/system_benchmark_test.go |
| AMICI-dev/AMICI | 16 | tests/benchmark-models/test_petab_benchmark.py / tests/benchmark-models/test_petab_benchmark_jax.py / tests/benchmark_models/evaluate_benchmark.py / tests/benchmark_models/test_petab_benchmark.py / tests/benchmark_models/test_petab_benchmark_jax.py |
| ROCm/rocm-libraries | 16 | projects/hipblaslt/clients/bench/src/client.cpp / projects/composablekernel/tile_engine/ops/gemm/grouped_gemm/grouped_gemm_benchmark.py |
| proffesor-for-testing/agentic-qe | 16 | v3/tests/benchmarks/coherence-performance.bench.ts |
| waditu/czsc | 16 | test/test_weights_convert_benchmark.py |
| btraceio/btrace | 15 | btrace-core/src/jmh/java/org/openjdk/btrace/core/comm/v2/BinaryProtocolBenchmark.java / btrace-core/src/test/java/org/openjdk/btrace/core/comm/v2/BinaryProtocolPerformanceTest.java |
| lance-format/lance | 15 | rust/lance-encoding/benches/decoder.rs / rust/lance-index/benches/find_partitions.rs / rust/lance-index/benches/kmeans.rs / rust/lance-index/benches/sq.rs / rust/lance-io/benches/scheduler.rs |
| tun-rs/tun-rs | 15 | benches/bytescodec_decode.rs / benches/bytescodec_memory.rs / benches/bytescodec_reuse.rs / benches/bytescodec_reserve.rs |
| wasmerio/wasmer | 15 | lib/cache/benches/bench_filesystem_cache.rs |
| cberner/raptorq | 14 | benches/codec_benchmark.rs / benches/decode_benchmark.rs / benches/encode_benchmark.rs / benches/matrix_sparsity.rs |
| equationzhao/g | 14 | internal/cli/adaptive_bench_test.go / internal/cli/dive_bench_test.go |
| evenfurther/pathfinding | 14 | benches/algos.rs / benches/iai_kuhn_munkres.rs / benches/iai_separate_components.rs / benches/kuhn_munkres.rs / benches/separate_components.rs |
| joamag/boytacean | 14 | benches/cpu.rs |
| neondatabase/neon | 14 | test_runner/performance/test_physical_replication.py / pageserver/benches/bench_ingest.rs / storage_broker/benches/rps.rs / test_runner/performance/pageserver/interactive/test_many_small_tenants.py / test_runner/performance/pageserver/pagebench/test_large_slru_basebackup.py |
| strawberry-graphql/strawberry | 14 | tests/benchmarks/test_parse_execute_large_query.py |
| Chia-Network/chia-blockchain | 13 | benchmarks/dict_fromkeys_dedup_benchmark.py |
| Cosmian/kms | 13 | crate/test_kms_server/benches/rsa_benches.rs |
| Kocoro-lab/Shannon | 13 | go/orchestrator/internal/activities/memory_bench_test.go |
| NVIDIA/cccl | 13 | python/cuda_cccl/benchmarks/parallel/bench_merge_sort.py / python/cuda_cccl/benchmarks/parallel/bench_reduce.py / python/cuda_cccl/benchmarks/parallel/bench_zip_iterator.py / python/cuda_cccl/benchmarks/parallel/bench_transform.py / cub/benchmarks/bench/transform/common.h |
| getzep/graphiti | 13 | mcp_server/tests/test_benchmark_mcp.py |
| hoprnet/hoprnet | 13 | impls/graph/benches/traverse.rs / protocols/hopr/benches/codec.rs / transport/protocol/benches/protocol_throughput_emulated.rs / transport/session/benches/session_bench.rs |
| netease-youdao/LobsterAI | 13 | SKILLs/skill-creator/scripts/aggregate_benchmark.py |
| open-telemetry/otel-arrow | 13 | rust/experimental/query_engine/engine-recordset-otlp-bridge/benches/extend.rs / rust/otap-dataflow/crates/contrib-nodes/benches/exporters/azure_monitor_exporter/transformer.rs / rust/otap-dataflow/crates/pdata/benches/concatenate.rs |
| pastas/pastas | 13 | tests/test_notebooks_bench.py |
| thinking-machines-lab/tinker-cookbook | 13 | tinker_cookbook/recipes/harbor_rl/launch_terminal_bench.py |
| ProvableHQ/snarkVM | 12 | algorithms/benches/crypto_hash/poseidon.rs / algorithms/benches/fft/fft.rs / algorithms/benches/msm/variable_base.rs / algorithms/benches/snark/varuna.rs / circuit/environment/benches/linear_combination.rs |
| getsentry/relay | 12 | relay-server/benches/benches.rs |
| lee101/stock-prediction | 12 | bench_chronos2_compile.py / pufferlib_market/bench_obs_encode.py / cutechronos/tests/test_benchmark_optimized.py |
| reubeno/brush | 12 | brush-shell/benches/shell.rs |
| tonybaloney/CSnakes | 12 | src/Profile/BaseBenchmark.cs |
| torchgeo/torchgeo | 12 | torchgeo/datasets/ssl4eo_benchmark.py |
| vaadin/flow | 12 | flow-server/src/test/java/com/vaadin/flow/ComponentTrackerPerformanceTest.java |
| Activiti/Activiti | 11 | activiti-core/activiti-engine/src/test/java/org/activiti/engine/test/api/task/SubTaskPerformanceTest.java |
| GoogleCloudPlatform/gcsfuse | 11 | perfmetrics/scripts/ls_metrics/stat_benchmark.py |
| PlayFab/thundernetes | 11 | pkg/operator/controllers/gameserverqueue_benchmark_test.go / pkg/operator/controllers/port_registry_benchmark_test.go |
| ROCm/TheRock | 11 | gpu_comprehensive_benchmark.py / gpu_quick_benchmark.py |
| feldera/feldera | 11 | crates/dbsp/benches/column_layer.rs / crates/dbsp/benches/galen.rs / crates/dbsp/benches/path.rs |
| intel/intel-xpu-backend-for-triton | 11 | benchmarks/triton_kernels_benchmark/gemm_benchmark.py / benchmarks/vllm/unified_attention/unified_attention_benchmark.py |
| llamastack/llama-stack | 11 | src/llama_stack/distributions/open-benchmark/open_benchmark.py |
| microsoft/PyRIT | 11 | doc/code/executor/benchmark/2_bias_benchmark.py |
| omerbenamram/evtx | 11 | src/benches/dups.rs / src/benches/escape.rs / src/benches/expander.rs |
| pdpipe/pdpipe | 11 | tests/performance/test_issue_29.py |
| starkware-libs/stwo | 11 | crates/stwo/benches/pcs.rs |
| ai-dynamo/dynamo | 10 | benchmarks/router/prefix_ratio_benchmark.py / benchmarks/router/real_data_benchmark.py |
| feichai0017/QuillSQL | 10 | benches/storage_bench.rs |
| loro-dev/loro | 10 | crates/loro-internal/benches/list.rs / crates/loro-internal/benches/pending.rs / crates/loro/benches/merge_baseline.rs / crates/loro-internal/benches/encode.rs / crates/loro-internal/benches/text_r.rs |
| openvm-org/openvm | 10 | benchmarks/execute/benches/execute.rs / benchmarks/execute/benches/fibonacci_execute.rs / benchmarks/execute/benches/regex_execute.rs |
| projectdiscovery/nuclei | 10 | pkg/catalog/loader/loader_bench_test.go |
| rafaelkallis/adaptive-radix-tree | 10 | bench/memory.cpp |
| ruvnet/agentic-flow | 10 | packages/agentic-jujutsu/benches/operations.rs / packages/agentic-jujutsu/tests/benchmarks/performance.bench.js / packages/agentdb/benchmarks/memory.bench.ts / packages/agentdb/benchmarks/vector-search.bench.ts |
| useblocks/sphinx-needs | 10 | tests/benchmarks/test_constrained_links_benchmark.py / tests/benchmarks/test_querying.py |
| wshobson/maverick-mcp | 10 | tests/performance/test_benchmarks.py / tests/performance/test_load.py / tests/performance/test_profiling.py / tests/performance/test_stress.py |
| Azure/karpenter-provider-azure | 9 | vendor-local/karpenter/pkg/controllers/provisioning/scheduling/scheduling_benchmark_test.go |
| EFNext/EntityFrameworkCore.Projectables | 9 | benchmarks/EntityFrameworkCore.Projectables.Benchmarks/ExpressionResolverBenchmark.cs |
| OpenCoreMMO/OpenCoreMMO | 9 | benchmarks/NeoServer.Benchmarks/Tasks/SchedulerBenchmark.cs / benchmarks/NeoServer.Benchmarks/Hashing/TileHashBenchmark.cs |
| atopile/atopile | 9 | test/core/performance/test_performance_graph.py / test/core/performance/test_performance_pick.py |
| dubzzz/pure-rand | 9 | src/distribution/distribution.bench.ts / src/generator/generator.bench.ts |
| gogf/gf | 9 | contrib/drivers/mysql/mysql_z_unit_core_bench_test.go / os/gcache/gcache_z_bench_test.go / os/gstructs/gstructs_z_bench_test.go |
| maplibre/maplibre-tile-spec | 9 | java/src/jmh/java/org/maplibre/mlt/BingMapsDecoderBenchmark.java / java/src/jmh/java/org/maplibre/mlt/OmtDecoderBenchmark.java / java/src/jmh/java/org/maplibre/mlt/converter/encodings/fsst/FsstBenchmark.java / java/src/test/java/org/maplibre/mlt/benchmarks/MltDecoderBenchmark.java |
| natnew/Awesome-Data-Science | 9 | benchmarks/prompting/run_benchmark.py |
| rtk-ai/rtk | 9 | benchmarks/tests/test_analyze_code.py |
| yansongda/pay | 9 | rust-pay/benches/crypto_bench.rs |
| YuminosukeSato/pyproc | 8 | bench/observability_benchmark_test.go |
| hishamco/My.Extensions.Localization.Json | 8 | test/My.Extensions.Localization.Json.Benchmarks/JsonResourceManagerBenchmark.cs |
| lightly-ai/lightly-studio | 8 | lightly_studio/tests/performance/test_annotation_index_benchmark.py / lightly_studio/tests/performance/test_annotation_payload_n1_benchmark.py / lightly_studio/tests/performance/test_sample_collection_id_index_benchmark.py / lightly_studio/tests/performance/test_video_frame_n1_benchmark.py |
| matrixorigin/matrixone | 8 | pkg/objectio/ioutil/writer_bench_test.go / pkg/vectorindex/ivfflat/kmeans/elkans/clusterer_bench_test.go |
| microsoft/mssql-python | 8 | benchmarks/bench_mssql.py |
| mycrl/turn-rs | 8 | benches/service.rs |
| oxc-project/oxc-resolver | 8 | benches/path_operations.rs |
| ra1nty/DXcam | 8 | benchmarks/timer_benchmark.py / tests/benchmarks/test_processor_microbenchmark.py |
| ruvnet/RuVector | 8 | crates/ruvector-graph/benches/cypher_parser.rs / crates/ruvector-graph/benches/distributed_query.rs / crates/ruvector-graph/benches/graph_bench.rs / crates/ruvector-graph/benches/graph_traversal.rs / crates/ruvector-graph/benches/hybrid_vector_graph.rs |
| sarchlab/mgpusim | 8 | nvidia/benchmark/benchmark_test.go |
| smart-mcp-proxy/mcpproxy-go | 8 | internal/upstream/manager_bench_test.go |
| Arron196/CLIProxyAPI | 7 | sdk/cliproxy/auth/ttft_benchmark_test.go / sdk/cliproxy/auth/scheduler_benchmark_test.go |
| DataDog/dd-trace-go | 7 | ddtrace/tracer/transport_bench_test.go / ddtrace/tracer/writer_bench_test.go |
| ROCm/aiter | 7 | op_tests/op_benchmarks/triton/bench_batch_prefill.py / op_tests/op_benchmarks/triton/bench_gmm.py / op_tests/op_benchmarks/triton/bench_mha.py / op_tests/op_benchmarks/triton/bench_fav3_sage_mxfp4.py / op_tests/op_benchmarks/triton/bench_moe_gemm_a4w4.py |
| SurgeDM/Surge | 7 | internal/engine/concurrent/task_queue_benchmark_test.go |
| ava-labs/avalanchego | 7 | snow/networking/benchlist/benchlist_test.go |
| bzsanti/oxidizePdf | 7 | test-suite/benches/core_benchmarks.rs / oxidize-pdf-core/benches/ai_chunking.rs / oxidize-pdf-core/benches/batch_processing_benchmark.rs / oxidize-pdf-core/benches/image_extraction_benchmark.rs / oxidize-pdf-core/benches/parsing_benchmark.rs |
| mdit-plugins/mdit-plugins | 7 | packages/attrs/__tests__/performance.bench.ts / packages/img-size/__tests__/performance.bench.ts / packages/alert/__tests__/performance.bench.ts / packages/container/__tests__/performance.bench.ts / packages/demo/__tests__/performance.bench.ts |
| pytorch/ao | 7 | benchmarks/microbenchmarks/test/test_benchmark_inference.py |
| xhluca/bm25s | 7 | tests/core/test_performance_optimizations.py |
| Devolutions/IronRDP | 6 | crates/ironrdp-bulk/benches/bulk_compression.rs |
| FLOX-Foundation/flox | 6 | benchmarks/position_manager_benchmark.cpp / benchmarks/candle_aggregator_benchmark.cpp / benchmarks/full_order_book_benchmark.cpp / benchmarks/windowed_order_book_benchmark.cpp |
| NewLifeX/X | 6 | Benchmark/PacketBenchmarks/ArrayPacketBenchmark.cs / Benchmark/PacketBenchmarks/MemoryPacketBenchmark.cs / Benchmark/PacketBenchmarks/OwnerPacketBenchmark.cs / Benchmark/PacketBenchmarks/PacketComparisonBenchmark.cs / Benchmark/PacketBenchmarks/PacketConcurrencyBenchmark.cs |
| cordx56/rustowl | 6 | benches/rustowl_bench_simple.rs |
| eXist-db/exist | 6 | exist-core/src/test/java/org/exist/xquery/xquf/XQUFBenchmark.java / exist-core/src/test/java/org/exist/xquery/lock/ConcurrencyBenchmark.java |
| feichai0017/NoKV | 6 | benchmark/ycsb_test.go |
| goravel/goravel | 6 | tests/performance/advanced_benchmark_test.go / tests/performance/db_orm_benchmark_test.go / tests/performance/performance_test.go |
| huggingface/tokenizers | 6 | tokenizers/benches/added_vocab_deserialize.rs / tokenizers/benches/llama3.rs / bindings/python/benches/test_deserialize.py / tokenizers/benches/bert_benchmark.rs / tokenizers/benches/bpe_benchmark.rs |
| langchain-ai/langsmith-sdk | 6 | rust/crates/langsmith-tracing-client/benches/json_serialization_benchmark.rs / rust/crates/langsmith-tracing-client/benches/tracing_client_benchmark.rs / python/bench/upload_examples_bench.py |
| lemony-ai/cascadeflow | 6 | tests/benchmarks/banking77_benchmark.py |
| llgcode/draw2d | 6 | performance_bench_test.go |
| open-telemetry/opentelemetry-cpp | 6 | sdk/test/metrics/histogram_aggregation_benchmark.cc |
| ruvnet/ruv-FANN | 6 | benches/neural_network.rs |
| DeepLabCut/DeepLabCut-live | 5 | tests/test_benchmark_script.py |
| Lightning-AI/lightning-thunder | 5 | thunder/benchmarks/layers_for_inference_benchmark.py |
| bitcoin/bitcoin | 5 | src/bench/addrman.cpp / src/bench/base58.cpp / src/bench/bech32.cpp / src/bench/bench.cpp / src/bench/bench.h |
| hiero-ledger/hiero-consensus-node | 5 | hedera-node/hedera-app/src/jmh/java/com/hedera/node/app/signature/impl/Secp256k1InteropBenchmark.java |
| interpretml/interpret | 5 | python/powerlift/tests/powerlift/bench/test_experiment.py |
| rjdellecese/confect | 5 | packages/server/test/ValidatorToSchema.bench.ts |
| 1yefuwang1/vectorlite | 4 | vectorlite/ops/ops_benchmark.cpp |
| NVIDIA/Fuser | 4 | benchmarks/python/host/test_many_pointwise_ops_host.py / benchmarks/python/layers_for_inference_benchmark.py / benchmarks/python/test_cross_entropy_loss.py / benchmarks/python/test_rmsnorm_add_fwd.py / benchmarks/python/test_rope.py |
| Skidamek/AutoModpack | 4 | core/src/test/java/pl/skidam/automodpack_core/utils/WildCardsPerformanceTest.java |
| UKGovernmentBEIS/inspect_evals | 4 | src/inspect_evals/mle_bench/mle_bench.py |
| ZcashFoundation/zebra | 4 | zebra-chain/benches/block.rs |
| ZimoLiao/scholaraio | 4 | scholaraio/ingest/parser_matrix_benchmark.py / tests/test_parser_matrix_benchmark.py |
| facioquo/stock-indicators-python | 4 | benchmarks/test_benchmark_indicators.py / benchmarks/test_decimal_conversion_performance.py |
| melix/jmh-gradle-plugin | 4 | src/funcTest/resources/java-project-with-failing-benchmark/src/jmh/java/me/champeau/gradle/jmh/FailingBenchmark.java |
| ml-explore/mlx-lm | 4 | bench/bench_continuous_vs_static.py / tests/bench/test_bench_continuous_vs_static.py |
| tahoebio/tahoe-x1 | 4 | scripts/msigdb/run_benchmark.py |
| wilsonzlin/fastrender | 4 | benches/comprehensive.rs / benches/layout_benches.rs / benches/paint_benches.rs / benches/render_benchmark.rs |
| NVIDIA/TensorRT-LLM | 3 | tests/integration/defs/perf/test_perf.py / tests/unittest/llmapi/apps/_test_trtllm_serve_benchmark.py |
| Netflix/hollow | 3 | hollow-perf/src/jmh/java/com/netflix/hollow/core/read/engine/object/HollowObjectTypeReadStateDeltaTransitionBenchmark.java |
| beowolx/rensa | 3 | benchmarks/advanced_benchmark.py / benchmarks/simple_benchmark.py |
| dial9-rs/dial9-tokio-telemetry | 3 | dial9-tokio-telemetry/benches/poll_overhead.rs |
| huggingface/candle | 3 | candle-nn/benches/benchmarks/layer_norm.rs |
| ipsilon/evmone | 3 | _codeql_build_dir/deps/src/blst/bindings/rust/benches/blst_benches.rs |
| logos-blockchain/logos-blockchain | 3 | core/benches/mantle_tx_components.rs |
| questdb/questdb | 3 | benchmarks/src/main/java/org/questdb/GroupByCharSequenceLongHashMapBenchmark.java / benchmarks/src/main/java/org/questdb/GroupByLong128HashSetBenchmark.java / benchmarks/src/main/java/org/questdb/GroupByLong256HashSetBenchmark.java / benchmarks/src/main/java/org/questdb/GroupByLongHashSetBenchmark.java / benchmarks/src/main/java/org/questdb/GroupByLongLongHashMapBenchmark.java |
| ratatui/ratatui | 3 | ratatui/benches/main/barchart.rs / ratatui/benches/main/block.rs / ratatui/benches/main/gauge.rs / ratatui/benches/main/list.rs / ratatui/benches/main/paragraph.rs |
| relf/EGObox | 3 | crates/gp/benches/correlation_models.rs |
| surrealdb/surrealdb | 3 | crates/sdk/benches/array_complement.rs / crates/sdk/benches/array_difference.rs / crates/sdk/benches/array_intersect.rs / crates/sdk/benches/array_uniq.rs |
| trufflesecurity/trufflehog | 3 | pkg/decoders/escaped_unicode_bench_test.go |
| KentBeck/BPlusTree3 | 2 | python/tests/test_performance_benchmarks.py |
| NVlabs/GEM | 2 | benches/event_buffer.rs |
| SylphxAI/pdf-reader-mcp | 2 | test/benchmark/readPdf.bench.ts |
| a16z/jolt | 2 | jolt-core/benches/e2e_profiling.rs |
| apache/arrow | 2 | cpp/src/parquet/arrow/reader_writer_benchmark.cc |
| apache/pulsar | 2 | microbench/src/main/java/org/apache/pulsar/broker/delayed/bucket/BucketDelayedDeliveryTrackerSimpleBenchmark.java |
| cosmos/evm | 2 | evmd/ante/evm_antehandler_benchmark_test.go |
| deepseek-ai/DeepSeek-V3 | 2 | inference/bench_sparse_projection.py |
| dromara/mica-mqtt | 2 | example/mica-mqtt-example/src/main/java/org/dromara/mica/mqtt/benchmark/MqttBenchmark.java |
| frappe/bench | 2 | bench/tests/test_utils.py / bench/tests/test_app_discovery.py |
| georust/geo-index | 2 | benches/rtree.rs |
| joi-lab/ouroboros | 2 | scripts/run_vfriday_benchmark.py |
| martabal/qbittorrent-exporter | 2 | internal/internal_bench_test.go / prometheus/prometheus_bench_test.go / qbit/qbit_bench_test.go |
| ml-explore/mlx | 2 | benchmarks/python/paged_attention_bench.py / python/tests/test_paged_attention_bench.py |
| open-telemetry/opentelemetry-java | 2 | sdk/trace/src/jmh/java/io/opentelemetry/sdk/trace/export/BatchSpanProcessorBurstyLoadBenchmark.java |
| poteto/noodle | 2 | loop/bench_test.go |
| quinlan-lab/bedder-rs | 2 | benches/random_intervals.rs |
| readmeio/oas | 2 | packages/oas/test/bench/dereference.bench.ts / packages/parser/test/bench/dereference.bench.ts / packages/oas/test/benchmarks/dereference.bench.ts / packages/parser/test/benchmarks/bundle.bench.ts / packages/parser/test/benchmarks/dereference.bench.ts |
| vllm-project/router | 2 | benches/request_processing.rs |
| AddictedCS/soundfingerprinting | 1 | src/SoundFingerprinting.Tests/Unit/Utils/FingerprintDescriptorBenchmark.cs |
| apache/mahout | 1 | testing/qdp/test_benchmark_api.py |
| asg017/sqlite-vec | 1 | benchmarks-ann/bench-delete/bench_delete.py / benchmarks-ann/bench-delete/test_smoke.py |
| aws/aws-cli | 1 | tests/unit/test_benchmark_utils.py |
| besu-eth/besu | 1 | ethereum/core/src/jmh/java/org/hyperledger/besu/ethereum/vm/operations/OneMillionCountLeadingZerosOperationBenchmark.java / ethereum/core/src/jmh/java/org/hyperledger/besu/ethereum/vm/operations/Hashing20kKeccak256Benchmark.java |
| bevyengine/bevy | 1 | benches/benches/bevy_ecs/scheduling/schedule.rs |
| clockworklabs/SpacetimeDB | 1 | crates/bench/benches/index.rs |
| cmu-pasta/fray | 1 | benchmark/src/jmh/kotlin/org/pastalab/fray/benchmark/FrayBenchmark.kt |
| dmmulroy/jj-starship | 1 | benches/prefix_benchmark.rs |
| fancy-regex/fancy-regex | 1 | benches/bench.rs |
| gomate-community/TrustRAG | 1 | tests/test_performance_improvements.py |
| haasonsaas/ocode | 1 | tests/performance/test_performance.py |
| jito-foundation/jito-solana | 1 | precompiles/benches/ed25519_instructions.rs / precompiles/benches/secp256k1_instructions.rs / precompiles/benches/secp256r1_instructions.rs |
| odvcencio/gotreesitter | 1 | grammargen/lr_bench_test.go |
| pest-parser/pest | 1 | pest/benches/stack.rs |
| speaches-ai/speaches | 1 | scripts/performance_benchmark.py |
| tensorflow/tensorboard | 1 | tensorbored/encode_png_benchmark.py |
| uutils/coreutils | 1 | src/uu/cat/benches/cat_bench.rs |
| vendurehq/vendure | 1 | packages/core/e2e/default-search-plugin.bench.ts |
| visualHFT/VisualHFT | 1 | VisualHFT.Benchmarks/HelperOrderBookBenchmark.cs / VisualHFT.Commons.Benchmarks/HelperOrderBookBenchmark.cs |
| wasm-bindgen/wasm-bindgen | 1 | crates/test/benches/headless_output.rs |
| wikimedia/sentencex | 1 | benches/comprehensive_benchmark.rs |
| wilsonzlin/CoreNN | 1 | libcorenn/benches/distance.rs / libcorenn/benches/query.rs |

## 边界

这份名单用的是数据集里出现过的文件路径。仓库里有性能测试，但这批提交从来没碰到那个文件时，这里还看不到。普通 `*_test.go` 里只有 `func Benchmark`、文件名不带 bench 的，也没有算进去。
