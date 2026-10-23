# PR 分析工作流 — 预检报告

生成时间 (UTC): 2026-07-25T06:50:23.595006+00:00

## 总体结论

- **是否建议进入下一步**: 是
- **说明**: 预检通过：DeepSeek API 可用，六份样例 JSON 结构与模板一致，格式正确；prompt 与 schema 仅有文档级软差异（见第 3 节），可进入工作流脚本开发与试跑。
- **警告**:
  - Exemplars contain 2 strict-enum deviations (mostly custom snake_case tags allowed by prompt).
  - prompt/schema soft documentation gaps — see section 3.

## 1. DeepSeek API Key

- 状态: **PASS**
- 结果: API key accepted (GET /models 200)
- 可用模型样例: deepseek-v4-flash, deepseek-v4-pro

## 2. JSON 与 schema.json 字段对应

- 分析样例数量: 6
- 全部可解析: True
- 相对模板缺失路径总数: 0
- 相对模板多余路径总数: 0
- 类型/布尔格式问题: 0
- 一致性规则问题: 0
- 受控词表严格枚举偏离: 2

### 逐文件摘要
#### 3228424652_analysis.json
- pr_id 与文件名一致: True
- 缺失字段: 无
- 多余字段: 无

#### 3194284966_analysis.json
- pr_id 与文件名一致: True
- 缺失字段: 无
- 多余字段: 无

#### 3145702280_analysis.json
- pr_id 与文件名一致: True
- 缺失字段: 无
- 多余字段: 无

#### 3125029980_analysis.json
- pr_id 与文件名一致: True
- 缺失字段: 无
- 多余字段: 无
- 词表: perf_labels.evidence_type: non-enum "maintainer_manual_test" (allowed: ['benchmark', 'ci_task_eval', 'narrative', 'profiling', 'unknown'])

#### 3074351366_analysis.json
- pr_id 与文件名一致: True
- 缺失字段: 无
- 多余字段: 无
- 词表: perf_labels.evidence_type: non-enum "unit_test" (allowed: ['benchmark', 'ci_task_eval', 'narrative', 'profiling', 'unknown'])

#### 3022909076_analysis.json
- pr_id 与文件名一致: True
- 缺失字段: 无
- 多余字段: 无

## 3. prompt.md 与 schema.json

- 评估: **WARN**
- 文档/样例软差异:
  - prompt.md lists detection_detail keys code_reading/profiler/load_test/ci_auto; schema.json template only documents code_reading and ci_auto (template doc gap).
  - schema meta.status includes open; prompt merge_outcome_context.outcome is merged/closed only — for still-open PRs, workflow should map status explicitly.
  - Gold JSON 3194284966 uses files_by_status.removed; prompt examples say deleted — naming drift only.
  - Exemplars use custom perf_focus / outcome_reason / evidence_type labels beyond strict enums; consistent with prompt rule allowing new snake_case when needed.

## 4. 安全提醒

- 请勿将 `.deepseekToken` 提交到 Git；推送前确认已在 `.gitignore` 中。
