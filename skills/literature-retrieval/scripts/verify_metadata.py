"""DOI 元数据交叉核验（Crossref vs OpenAlex）；只核对元数据，不下载全文。

用法：
    python verify_metadata.py --doi 10.1145/xxxx -o verify.json

输出：{doi, crossref: {...}|null, openalex: {...}|null, status, title_match, year_match, note}
status: match / partial / mismatch / not_found
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = "literature-retrieval-skill/0.1"


def _get_json(url: str, *, timeout: int = 30, retries: int = 2) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise LookupError("not found") from exc
            last_error = exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"请求失败：{last_error}")


def normalize_title(value: str) -> str:
    value = value.lower()
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[^\w\u4e00-\u9fff]+", " ", value)
    return " ".join(value.split())


def title_similarity(left: str, right: str) -> float:
    left_norm, right_norm = normalize_title(left), normalize_title(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    left_tokens, right_tokens = set(left_norm.split()), set(right_norm.split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _crossref(doi: str) -> dict[str, Any] | None:
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"
    try:
        data = _get_json(url)
    except LookupError:
        return None
    item = data.get("message") or {}
    titles = item.get("title") or []
    issued = item.get("issued") or {}
    parts = issued.get("date-parts") or []
    return {"source": "crossref", "doi": item.get("DOI") or doi,
            "title": (titles[0] if titles else "").strip(),
            "year": parts[0][0] if parts and parts[0] else None}


def _openalex(doi: str) -> dict[str, Any] | None:
    url = f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(doi, safe='')}"
    try:
        data = _get_json(url)
    except (LookupError, RuntimeError):
        return None
    return {"source": "openalex", "doi": data.get("doi") or doi,
            "title": (data.get("title") or data.get("display_name") or "").strip(),
            "year": data.get("publication_year")}


def verify(doi: str) -> dict[str, Any]:
    doi = doi.strip()
    if not doi:
        raise ValueError("doi 不能为空")
    crossref = _crossref(doi)
    openalex = _openalex(doi)
    if not crossref and not openalex:
        return {"doi": doi, "crossref": None, "openalex": None,
                "status": "not_found", "title_match": False, "year_match": False,
                "note": "DOI 在 Crossref/OpenAlex 均未找到，请人工核对"}
    similarity = 0.0
    if crossref and openalex:
        similarity = title_similarity(crossref["title"], openalex["title"])
        year_match = (crossref["year"] is not None and openalex["year"] is not None
                      and abs(int(crossref["year"]) - int(openalex["year"])) <= 1)
        if similarity >= 0.9 and year_match:
            status = "match"
        elif similarity >= 0.7:
            status = "partial"
        else:
            status = "mismatch"
        note = "交叉核验完成"
    else:
        status = "partial"
        year_match = False
        note = "仅单一来源可查（Crossref 或 OpenAlex），建议人工复核"
    return {"doi": doi, "crossref": crossref, "openalex": openalex,
            "status": status, "title_similarity": round(similarity, 3),
            "title_match": similarity >= 0.9, "year_match": year_match, "note": note}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DOI 元数据交叉核验")
    parser.add_argument("--doi", required=True)
    parser.add_argument("-o", "--output", default="verify.json")
    args = parser.parse_args(argv)
    try:
        result = verify(args.doi)
    except Exception as exc:  # noqa: BLE001
        print(f"核验失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    result["checked_at"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.output}: {result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
