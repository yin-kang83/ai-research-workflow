# 示例数据（仅演示，非真实文献）

本目录数据用于跑通命令，**不是真实论文**：

- `query_plan_sample.json`：`build_query_plan.py` 输出示例；
- `openalex_sample.json`：`search_openalex.py` 结果结构示例（占位 DOI）；
- `verify_sample.json`：`verify_metadata.py` 输出示例；
- `literature_ledger_sample.jsonl`：`ingest_literature.py` 入账后的账本示例。

跑一遍：

```powershell
$py = "python"
& $py skills/literature-retrieval/scripts/build_query_plan.py --concept "大语言模型 合规" -o examples/query_plan_sample.json
& $py scripts/ingest_literature.py --input examples/openalex_sample.json --verify examples/verify_sample.json --ledger .tmp/ledger.jsonl
```

真实检索时把 `examples/openalex_sample.json` 换成 `search_openalex.py` 的输出即可。
