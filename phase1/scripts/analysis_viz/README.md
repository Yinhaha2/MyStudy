# analysis_viz

Jupyter 可视化笔记本，基于 `phase1/data/full_analysis_distilled.csv`。

## 文件

| 文件 | 说明 |
|------|------|
| `perf_pr_visualization.ipynb` | 主笔记本：规模/存活/评论 vs 合并率，反模式、识别方式、优化层级、退化处置等 |
| `figures/` | 运行后生成的 PNG（已 gitignore） |

## 运行

```bash
pip install -r requirements.txt jupyter
python3 phase1/scripts/generate_full_analysis.py
jupyter notebook phase1/scripts/analysis_viz/perf_pr_visualization.ipynb
```

打开后：菜单 Run → Run All。

| 报错 | 怎么办 |
|------|--------|
| `NameError: df is not defined` | 没跑初始化。Run All，或先跑第一格代码直到看到初始化完成 |
| `FileNotFoundError` ... `full_analysis_distilled.csv` | 在仓库根目录执行 `python3 phase1/scripts/generate_full_analysis.py` |
| `ModuleNotFoundError: pandas` 等 | `pip install -r requirements.txt` |

## 图表一览（18 张）

1. 代码行数箱线图 + 堆叠条形（合并/未合并）+ 合并率折线
2. 文件数箱线图 + 堆叠条形 + 合并率折线
3. 存活时间箱线图 + 堆叠条形 + 合并率折线
4. 评论数箱线图 + 分箱合并率
5. 反模式 / 识别方式 / 优化层级 / 退化处置 条形图
6. 修复引入新问题（`antipattern_in_fix`）
7. 终态占比、Agent 合并率、可复现性×结果、边界类型、review 数分箱
