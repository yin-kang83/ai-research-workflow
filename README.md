# AI 研究工作流 · 可验证的检索、证据与归档

> 目标：把"AI 辅助研究"从"看课/刷帖"变成**可复现、可审计、可证伪**的工作流。
> 仓库只包含**方法与通用工具**，不包含明细数据、客户信息、评分参数或投资结论。

## 这是什么

- **合规文献检索**：OpenAlex / Crossref / arXiv 元数据检索、DOI 核验、BibTeX 导出；
- **文献 → 证据账本**：检索结果去重入账，标注 `L3_METADATA`（线索，不是结论）；
- **三处一致性检查**：本地 / Gitee / GitHub / Zenodo 的版本、tree、文件校验和；
- **方法论文章**：证据分级、证伪账本、可验证学习路径；
- **系列大纲**：知乎/公众号《我的 AI 研究工作流》5 篇（见 `series/OUTLINE.md`）。

## 不包含什么

- ❌ 付费墙/非 OA 全文下载、转存、分发；
- ❌ 明细 claim / 证伪账本、标的评分参数、客户/隐私数据、投资结论；
- ❌ "一键生成论文/报告"式黑盒（本仓库强调可核验流程）。

## 快速开始

```powershell
$py = "python"  # 建议 3.11+
# 1) 关键词扩展
& $py skills/literature-retrieval/scripts/build_query_plan.py --concept "大语言模型 合规" -o .tmp/plan.json
# 2) 检索元数据（无需 key；OpenAlex 可能 429，可加 --mailto）
& $py skills/literature-retrieval/scripts/search_arxiv.py --query "large language model compliance" --max-results 5 -o .tmp/arxiv.json
& $py skills/literature-retrieval/scripts/search_openalex.py --query "large language model compliance" --limit 5 -o .tmp/openalex.json
# 3) DOI 核验（可选）
& $py skills/literature-retrieval/scripts/verify_metadata.py --doi 10.1000/xyz -o .tmp/verify.json
# 4) 入证据账本（L3 元数据）
& $py scripts/ingest_literature.py --input .tmp/arxiv.json --ledger .tmp/literature_ledger.jsonl
# 5) 导出 BibTeX
& $py skills/literature-retrieval/scripts/export_bibtex.py --input .tmp/arxiv.json -o .tmp/refs.bib
```

## 证据标准

| 等级 | 含义 | 本仓库处理 |
|---|---|---|
| L1 | 一手原文（公告/财报/论文原文） | 必须带 source/locator，人工核对 |
| L2 | 原文计算/扫描 | 保留计算口径与原始字段 |
| L3 | 文献元数据/媒体/研报线索 | 只能作为线索，不得直接作为结论 |

- 先写 **falsify 条件** 再下结论；负结果保留；
- 不写无来源数字；AI 辅助内容主动声明。

## 目录

```
skills/literature-retrieval/   # 合规文献检索技能（6 脚本 + 5 离线测试）
scripts/ingest_literature.py   # 检索结果 → 证据账本（L3 元数据，去重）
scripts/check_consistency.py   # Gitee/GitHub/Zenodo 一致性检查
examples/                      # 最小示例（脱敏）
methodology/                   # 方法论文章入口（完整版在 cn-us-ai-compare）
series/OUTLINE.md              # 知乎/公众号 5 篇系列大纲
```

## 相关项目

- 中美 AI 对比研究（报告 + 聚合数据 + 论文）：https://gitee.com/yin-kang83/cn-us-ai-compare ｜ https://github.com/yin-kang83/cn-us-ai-compare
- 报告归档 DOI：https://doi.org/10.5281/zenodo.24374262 ｜ 代码 DOI：https://doi.org/10.5281/zenodo.24374363
- 方法论文章：《AI 学习的四种路径与可验证性标准》在 `cn-us-ai-compare/methodology/`。

## 许可

- 代码（`skills/`、`scripts/`）：MIT；
- 文档（`README.md`、`methodology/`、`series/`）：CC BY 4.0；
- 示例数据仅用于演示，不含第三方全文。

## 免责声明

研究材料，不构成投资建议、法律或税务意见；引用请以原文/DOI 为准。
