"""OpenAlex 文献元数据检索（合规：只取元数据，不下载全文）。

用法：
    python search_openalex.py --query "large language model compliance" \
        --from-year 2023 --limit 20 -o openalex.json

输出 JSON：
    {"source": "openalex", "query": ..., "retrieved_at": ..., "count": n, "results": [...]}

每条结果字段：id, doi, title, year, authors, venue, type, cited_by_count,
oa_url, pdf_url, landing_page。pdf_url 仅来自 OpenAlex 标注的合法 OA 位置，
本脚本不下载 PDF。
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

API = "https://api.openalex.org/works"
USER_AGENT = "literature-retrieval-skill/0.1 (research; contact: local)"


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
    raise RuntimeError(f"OpenAlex 请求失败：{last_error}")


def _author_name(authorship: dict[str, Any]) -> str:
    author = authorship.get("author") or {}
    return str(author.get("display_name") or "").strip()


def work_to_record(work: dict[str, Any]) -> dict[str, Any]:
    """把 OpenAlex work 转成稳定、可审计的记录。"""
    primary = work.get("primary_location") or {}
    source = primary.get("source") or {}
    best_oa = work.get("best_oa_location") or {}
    open_access = work.get("open_access") or {}
    return {
        "source": "openalex",
        "id": work.get("id"),
        "doi": work.get("doi"),
        "title": (work.get("title") or work.get("display_name") or "").strip(),
        "year": work.get("publication_year"),
        "authors": [name for name in (_author_name(item) for item in work.get("authorships") or []) if name],
        "venue": source.get("display_name") or "",
        "type": work.get("type"),
        "cited_by_count": work.get("cited_by_count"),
        "oa_url": open_access.get("oa_url") or best_oa.get("landing_page_url") or "",
        "pdf_url": best_oa.get("pdf_url") or "",
        "landing_page": primary.get("landing_page_url") or "",
    }


def build_url(query: str, *, from_year: int | None, to_year: int | None,
              limit: int, mailto: str | None = None) -> str:
    params: dict[str, str] = {
        "search": query,
        "per-page": str(limit),
        "sort": "cited_by_count:desc",
        "select": "id,doi,title,display_name,publication_year,authorships,primary_location,"
                  "best_oa_location,open_access,type,cited_by_count",
    }
    filters: list[str] = []
    if from_year is not None:
        filters.append(f"from_publication_date:{from_year}-01-01")
    if to_year is not None:
        filters.append(f"to_publication_date:{to_year}-12-31")
    if filters:
        params["filter"] = ",".join(filters)
    if mailto:
        params["mailto"] = mailto
    return f"{API}?{urllib.parse.urlencode(params)}"


def search(query: str, *, from_year: int | None = None, to_year: int | None = None,
           limit: int = 20, mailto: str | None = None) -> list[dict[str, Any]]:
    if not query.strip():
        raise ValueError("query 不能为空")
    if not (1 <= limit <= 50):
        raise ValueError("limit 必须在 1..50")
    if from_year is not None and to_year is not None and from_year > to_year:
        raise ValueError("from_year 不能大于 to_year")
    data = _get_json(build_url(query, from_year=from_year, to_year=to_year,
                               limit=limit, mailto=mailto))
    return [work_to_record(work) for work in data.get("results", [])]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenAlex 文献元数据检索（只取元数据）")
    parser.add_argument("--query", required=True, help="检索主题/关键词")
    parser.add_argument("--from-year", type=int, default=None)
    parser.add_argument("--to-year", type=int, default=None)
    parser.add_argument("--limit", type=int, default=20, help="1..50")
    parser.add_argument("--mailto", default=None, help="可选：联系邮箱（OpenAlex polite pool）")
    parser.add_argument("-o", "--output", default="openalex_results.json")
    args = parser.parse_args(argv)
    try:
        results = search(args.query, from_year=args.from_year, to_year=args.to_year,
                         limit=args.limit, mailto=args.mailto)
    except Exception as exc:  # noqa: BLE001 - 顶层 CLI 错误转退出码
        print(f"检索失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    payload = {
        "source": "openalex",
        "query": args.query,
        "from_year": args.from_year,
        "to_year": args.to_year,
        "retrieved_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "count": len(results),
        "results": results,
    }
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.output}: {len(results)} results")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
