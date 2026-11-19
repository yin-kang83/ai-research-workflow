"""Crossref 文献元数据检索（DOI 权威元数据；不下载全文）。

用法：
    python search_crossref.py --query "large language model compliance" \
        --from-date 2023-01-01 --limit 20 -o crossref.json
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
from pathlib import Path
from typing import Any

API = "https://api.crossref.org/works"
USER_AGENT = "literature-retrieval-skill/0.1 (mailto: local)"


def _get_json(url: str, *, timeout: int = 30, retries: int = 2) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Crossref 请求失败：{last_error}")


def _year(item: dict[str, Any]) -> int | None:
    issued = item.get("issued") or {}
    parts = issued.get("date-parts") or []
    if parts and parts[0]:
        return parts[0][0]
    return None


def work_to_record(item: dict[str, Any]) -> dict[str, Any]:
    title = item.get("title") or []
    container = item.get("container-title") or []
    authors = []
    for author in item.get("author") or []:
        name = " ".join(part for part in (author.get("given"), author.get("family")) if part).strip()
        if name:
            authors.append(name)
    return {
        "source": "crossref",
        "doi": item.get("DOI"),
        "title": (title[0] if title else "").strip(),
        "year": _year(item),
        "authors": authors,
        "venue": (container[0] if container else "").strip(),
        "type": item.get("type"),
        "cited_by_count": item.get("is-referenced-by-count"),
        "landing_page": item.get("URL") or "",
        "pdf_url": "",
    }


def build_url(query: str, *, from_date: str | None, until_date: str | None,
              limit: int) -> str:
    params: dict[str, str] = {
        "query": query,
        "rows": str(limit),
        "select": "DOI,title,author,container-title,issued,URL,type,is-referenced-by-count",
        "sort": "is-referenced-by-count",
        "order": "desc",
    }
    filters: list[str] = []
    if from_date:
        filters.append(f"from-pub-date:{from_date}")
    if until_date:
        filters.append(f"until-pub-date:{until_date}")
    if filters:
        params["filter"] = ",".join(filters)
    return f"{API}?{urllib.parse.urlencode(params)}"


def search(query: str, *, from_date: str | None = None, until_date: str | None = None,
           limit: int = 20) -> list[dict[str, Any]]:
    if not query.strip():
        raise ValueError("query 不能为空")
    if not (1 <= limit <= 50):
        raise ValueError("limit 必须在 1..50")
    data = _get_json(build_url(query, from_date=from_date, until_date=until_date, limit=limit))
    items = (data.get("message") or {}).get("items") or []
    return [work_to_record(item) for item in items]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Crossref 文献元数据检索（只取元数据）")
    parser.add_argument("--query", required=True)
    parser.add_argument("--from-date", default=None, help="YYYY-MM-DD")
    parser.add_argument("--until-date", default=None, help="YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=20, help="1..50")
    parser.add_argument("-o", "--output", default="crossref_results.json")
    args = parser.parse_args(argv)
    try:
        results = search(args.query, from_date=args.from_date, until_date=args.until_date,
                         limit=args.limit)
    except Exception as exc:  # noqa: BLE001
        print(f"检索失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    payload = {
        "source": "crossref",
        "query": args.query,
        "from_date": args.from_date,
        "until_date": args.until_date,
        "retrieved_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "count": len(results),
        "results": results,
    }
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.output}: {len(results)} results")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
