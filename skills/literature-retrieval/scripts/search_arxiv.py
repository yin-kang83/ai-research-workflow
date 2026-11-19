"""arXiv 预印本检索（合法 OA；只取元数据与 PDF 链接，不下载 PDF）。

用法：
    python search_arxiv.py --query "large language model compliance" \
        --max-results 10 -o arxiv.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

API = "https://export.arxiv.org/api/query"
USER_AGENT = "literature-retrieval-skill/0.1"
NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _get_text(url: str, *, timeout: int = 30, retries: int = 2) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8", "replace")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"arXiv 请求失败：{last_error}")


def _text(node: ET.Element, path: str) -> str:
    found = node.find(path, NS)
    return (found.text or "").strip() if found is not None else ""


def parse_feed(xml_text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    results: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", NS):
        entry_id = _text(entry, "atom:id")
        pdf_url = ""
        for link in entry.findall("atom:link", NS):
            if link.get("title") == "pdf" or link.get("type") == "application/pdf":
                pdf_url = link.get("href") or ""
                break
        categories = [item.get("term") for item in entry.findall("atom:category", NS) if item.get("term")]
        results.append({
            "source": "arxiv",
            "id": entry_id,
            "doi": _text(entry, "arxiv:doi"),
            "title": " ".join(_text(entry, "atom:title").split()),
            "year": int(_text(entry, "atom:published")[:4]) if _text(entry, "atom:published")[:4].isdigit() else None,
            "published": _text(entry, "atom:published"),
            "authors": [name for name in (_text(author, "atom:name") for author in entry.findall("atom:author", NS)) if name],
            "venue": "arXiv",
            "type": "preprint",
            "summary": " ".join(_text(entry, "atom:summary").split()),
            "categories": categories,
            "pdf_url": pdf_url,
            "landing_page": entry_id,
            "note": "预印本，未同行评审，引用需注明",
        })
    return results


def build_url(query: str, *, max_results: int, category: str | None = None) -> str:
    search = f'all:"{query}"'
    if category:
        search = f"cat:{category} AND {search}"
    params = {
        "search_query": search,
        "start": "0",
        "max_results": str(max_results),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    return f"{API}?{urllib.parse.urlencode(params)}"


def search(query: str, *, max_results: int = 20, category: str | None = None) -> list[dict[str, Any]]:
    if not query.strip():
        raise ValueError("query 不能为空")
    if not (1 <= max_results <= 50):
        raise ValueError("max_results 必须在 1..50")
    return parse_feed(_get_text(build_url(query, max_results=max_results, category=category)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="arXiv 预印本检索（只取元数据）")
    parser.add_argument("--query", required=True)
    parser.add_argument("--max-results", type=int, default=20, help="1..50")
    parser.add_argument("--category", default=None, help="如 cs.CL / cs.AI / cs.LG")
    parser.add_argument("-o", "--output", default="arxiv_results.json")
    args = parser.parse_args(argv)
    try:
        results = search(args.query, max_results=args.max_results, category=args.category)
    except Exception as exc:  # noqa: BLE001
        print(f"检索失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    payload = {
        "source": "arxiv",
        "query": args.query,
        "retrieved_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "count": len(results),
        "results": results,
    }
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.output}: {len(results)} results")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
