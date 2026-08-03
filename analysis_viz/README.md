# analysis_viz

Jupyter 可视化笔记本，基于根目录 `full_analysis_distilled.csv`。

## 文件

| 文件 | 说明 |
|------|------|
| `perf_pr_visualization.ipynb` | 主笔记本：规模/存活/评论 vs 合并率，反模式、识别方式、优化层级、退化处置等 |
| `figures/` | 运行后生成的 PNG（已 gitignore） |

## 运行

```bash
# 在仓库根目录刷新 CSV（可选）
python3 generate_full_analysis.py

# 启动笔记本（需安装 jupyter）
cd analysis_viz
jupyter notebook perf_pr_visualization.ipynb
```

或在 VS Code / Cursor 中直接打开 `.ipynb` 逐格运行。

## 图表一览（18 张）

1. 代码行数箱线图 + 分箱合并率
2. 文件数箱线图 + 分箱合并率
3. 存活时间箱线图 + 分箱合并率
4. 评论数箱线图 + 分箱合并率
5. 反模式 / 识别方式 / 优化层级 / 退化处置 条形图
6. 修复引入新问题（`antipattern_in_fix`）
7. 终态占比、Agent 合并率、可复现性×结果、边界类型、review 数分箱
