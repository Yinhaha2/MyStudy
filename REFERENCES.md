# 参考文献与数据集

## 论文

- Md Nahidul Islam Opu, Shahidul Islam, Muhammad Asaduzzaman, Shaiful Chowdhury. *How Do Agentic AI Systems Address Performance Optimizations? A BERTopic-Based Analysis of Pull Requests.* [arXiv:2512.24630](https://arxiv.org/abs/2512.24630).

  Phase 1 的性能 PR 扩容集和 BERTopic 标签来自这篇论文。Phase 2 判断「PR 的主要目的是不是提升性能」时，用的是文中同一套分类标准。

- Hao Li, Haoxiang Zhang, Ahmed E. Hassan. *The Rise of AI Teammates in Software Engineering (SE) 3.0: How Autonomous Coding Agents Are Reshaping Software Engineering.* [arXiv:2507.15003](https://arxiv.org/abs/2507.15003).

- Hao Li, Haoxiang Zhang, Ahmed E. Hassan. *AIDev: Studying AI Coding Agents on GitHub.* [arXiv:2602.09185](https://arxiv.org/abs/2602.09185).

## 数据集

- [hao-li/AIDev](https://huggingface.co/datasets/hao-li/AIDev). Phase 1 的 `performance_pr_analysis.py` 读取其中的官方 `pr_task_type`。
- [hao-li/AIDev-7.6M](https://huggingface.co/datasets/hao-li/AIDev-7.6M). Phase 2 从 pop 子集（仓库大于 100 star，且表里有 commit SHA）抽取含性能测试的 PR。
- [Yinhaha2/beyond-merge-rate](https://github.com/Yinhaha2/beyond-merge-rate). Phase 1 终态语料的配套仓库。
- 本仓库 `phase1/data/finaldatabase/`. 1219 条 Agent 性能 PR 的主表、GitHub 附属表、BERTopic 分类，以及逐 PR 分析 JSON。
