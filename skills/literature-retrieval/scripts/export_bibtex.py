"""把检索结果 JSON 导出为 BibTeX（只导出元数据，不含全文）。

用法：
    python export_bibtex.py --input openalex.json -o refs.bib
    python export_bibtex.py --input a.json --input b.json -o refs.bib
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def _result_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        results = data.get("results")
        if isinstance(results, list):
            return [item for item in results if isinstance(item, dict)]
    raise ValueError("输入 JSON 必须是结果数组或包含 results 数组的对象")


def _first_author_key(record: dict[str, Any]) -> str:
    authors = record.get("authors") or []
    if authors:
        name = str(authors[0])
        parts = [part for part in re.split(r"[\s,]+", name) if part]
        if parts:
            return re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]", "", parts[-1]) or "anon"
    return "anon"


def _key(record: dict[str, Any], used: set[str]) -> str:
    year = record.get("year") or "nd"
    base = f"{_first_author_key(record)}{year}"
    title = str(record.get("title") or "").lower()
    words = re.findall(r"[a-z]{3,}", title)
    candidate = base + (words[0] if words else "ref")
    key, index = candidate, 2
    while key in used:
        key = f"{candidate}{index}"
        index += 1
    used.add(key)
    return key


def _escape(value: Any) -> str:
    text = str(value or "")
    text = text.replace("{", "\\{").replace("}", "\\}")
    return " ".join(text.split())


def to_bibtex(records: list[dict[str, Any]]) -> str:
    used: set[str] = set()
    entries: list[str] = []
    for record in records:
        title = _escape(record.get("title"))
        if not title:
            continue
        authors = " and ".join(_escape(name) for name in (record.get("authors") or [])) or "Unknown"
        entry_type = "misc" if record.get("source") == "arxiv" else "article"
        fields = [
            f"  title = {{{title}}}",
            f"  author = {{{authors}}}",
        ]
        if record.get("year"):
            fields.append(f"  year = {{{record['year']}}}")
        if record.get("venue"):
            fields.append(f"  journal = {{{_escape(record['venue'])}}}")
        if record.get("doi"):
            fields.append(f"  doi = {{{_escape(record['doi'])}}}")
        if record.get("landing_page"):
            fields.append(f"  url = {{{_escape(record['landing_page'])}}}")
        if record.get("source") == "arxiv":
            fields.append("  note = {预印本（arXiv），未同行评审}")
        key = _key(record, used)
        entries.append(f"@{entry_type}{{{key},\n" + ",\n".join(fields) + "\n}")
    return "\n".join(entries) + ("\n" if entries else "")


def collect(paths: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        records.extend(_result_list(data))
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检索结果 → BibTeX")
    parser.add_argument("--input", action="append", required=True, help="可多次传入")
    parser.add_argument("-o", "--output", default="refs.bib")
    args = parser.parse_args(argv)
    try:
        records = collect(args.input)
        bibtex = to_bibtex(records)
    except Exception as exc:  # noqa: BLE001
        print(f"导出失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    Path(args.output).write_text(bibtex, encoding="utf-8")
    print(f"wrote {args.output}: {len(records)} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
