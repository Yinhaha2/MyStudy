# analysis_viz

Jupyter 可视化笔记本，基于根目录 `full_analysis_distilled.csv`。

## 文件

| 文件 | 说明 |
|------|------|
| `perf_pr_visualization.ipynb` | 主笔记本：规模/存活/评论 vs 合并率，反模式、识别方式、优化层级、退化处置等 |
| `figures/` | 运行后生成的 PNG（已 gitignore） |

## 运行（Jupyter 新手）

### 第一次用？按这个来

```bash
# 1. 安装依赖（只需一次）
pip install -r requirements.txt jupyter

# 2. （可选）生成/刷新 CSV
python3 generate_full_analysis.py

# 3. 启动笔记本（在仓库根目录或 analysis_viz/ 里打开都行）
jupyter notebook analysis_viz/perf_pr_visualization.ipynb
```

打开后：**菜单 Run → Run All**，等跑完即可。

### 常见报错

| 报错 | 怎么办 |
|------|--------|
| `NameError: df is not defined` 或 `❌ 还没加载数据` | 没跑初始化。Run All，或先跑第一格代码直到看到 `✅ 初始化完成` |
| `FileNotFoundError` ... `full_analysis_distilled.csv` | 在仓库根目录执行 `python3 generate_full_analysis.py` |
| `ModuleNotFoundError: pandas` 等 | `pip install -r requirements.txt` |

**提示**：Jupyter 里每个格子要按顺序跑；重启内核（Restart）之后也要重新 Run All。

## 图表一览（18 张）

1. 代码行数箱线图 + 分箱合并率
2. 文件数箱线图 + 分箱合并率
3. 存活时间箱线图 + 分箱合并率
4. 评论数箱线图 + 分箱合并率
5. 反模式 / 识别方式 / 优化层级 / 退化处置 条形图
6. 修复引入新问题（`antipattern_in_fix`）
7. 终态占比、Agent 合并率、可复现性×结果、边界类型、review 数分箱
