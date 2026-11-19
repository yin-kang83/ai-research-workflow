"""把中文研究需求扩展为可审计的中英检索计划（不调用 LLM、可复现）。

用法：
    python build_query_plan.py --concept "大语言模型 合规" -o query_plan.json
    python build_query_plan.py --concept "AI 学习路径" --synonyms synonyms.json -o plan.json

输出：{concept, terms, openalex_search, crossref_query, arxiv_query, notes}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# 可审计的默认同义词表（可按项目扩展；不是穷举）
DEFAULT_SYNONYMS: dict[str, list[str]] = {
    "大语言模型": ["大语言模型", "large language model", "LLM", "生成式人工智能", "generative AI"],
    "人工智能": ["人工智能", "artificial intelligence", "AI"],
    "合规": ["合规", "compliance", "监管", "regulation", "治理", "governance"],
    "会计": ["会计", "accounting", "财务报告", "financial reporting"],
    "会计准则": ["会计准则", "accounting standards", "企业会计准则", "CAS"],
    "审计": ["审计", "audit", "审计准则", "auditing standards"],
    "学习": ["学习", "learning", "学习方法", "learning strategy"],
    "学习路径": ["学习路径", "learning path", "学习路线", "curriculum"],
    "证据": ["证据", "evidence", "证据分级", "evidence grading"],
    "可验证": ["可验证", "verifiable", "可复现", "reproducible", "可证伪", "falsifiable"],
    "财务": ["财务", "finance", "财务分析", "financial analysis"],
    "税务": ["税务", "tax", "税收", "taxation"],
}


def expand(concept: str, synonyms: dict[str, list[str]] | None = None) -> list[str]:
    """按概念包含关系扩展关键词；保持原始 concept + 去重。"""
    concept = concept.strip()
    if not concept:
        raise ValueError("concept 不能为空")
    table = dict(DEFAULT_SYNONYMS)
    if synonyms:
        if not isinstance(synonyms, dict):
            raise ValueError("synonyms 必须是 {键: [词...]} 对象")
        for key, values in synonyms.items():
            if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
                raise ValueError(f"synonyms[{key!r}] 必须是字符串数组")
            table[str(key)] = list(values)
    terms: list[str] = [concept]
    for key, values in table.items():
        if key in concept or any(word in concept for word in values):
            for word in values:
                if word and word not in terms:
                    terms.append(word)
    return terms


def build_plan(concept: str, synonyms: dict[str, list[str]] | None = None) -> dict[str, Any]:
    terms = expand(concept, synonyms)
    joined = " OR ".join(f'"{term}"' for term in terms)
    return {
        "concept": concept,
        "terms": terms,
        "openalex_search": " OR ".join(terms),
        "crossref_query": " ".join(terms),
        "arxiv_query": joined,
        "notes": [
            "关键词扩展为规则表 + 可选自定义同义词，可审计、可复现；",
            "检索结果仍需按 L1/L2/L3 证据分级并核对原文；",
            "不检索/不下载非 OA 全文；arXiv 为预印本，引用需注明未同行评审。",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检索计划/关键词扩展（规则化、可审计）")
    parser.add_argument("--concept", required=True, help="中文研究概念，如：大语言模型 合规")
    parser.add_argument("--synonyms", default=None, help="可选：自定义同义词 JSON 文件")
    parser.add_argument("-o", "--output", default="query_plan.json")
    args = parser.parse_args(argv)
    synonyms = None
    if args.synonyms:
        try:
            synonyms = json.loads(Path(args.synonyms).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"读取同义词文件失败：{exc}", file=sys.stderr)
            return 1
    try:
        plan = build_plan(args.concept, synonyms)
    except ValueError as exc:
        print(f"参数错误：{exc}", file=sys.stderr)
        return 1
    Path(args.output).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.output}: {len(plan['terms'])} terms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
