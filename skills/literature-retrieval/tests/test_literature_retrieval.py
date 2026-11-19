"""literature-retrieval skill 离线测试（不访问网络；网络 smoke 见 SKILL.md 手动命令）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_query_plan
import export_bibtex
import search_arxiv
import search_crossref
import search_openalex
import verify_metadata


class FakeResponse:
    def __init__(self, data: bytes):
        self._data = data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._data


OALEX_WORK = {
    "id": "https://openalex.org/W1",
    "doi": "https://doi.org/10.1000/x1",
    "title": "Large Language Model Compliance: A Survey",
    "publication_year": 2024,
    "authorships": [{"author": {"display_name": "Alice Chen"}},
                    {"author": {"display_name": "Bob Liu"}}],
    "primary_location": {"source": {"display_name": "Journal of AI"},
                         "landing_page_url": "https://example.org/x1"},
    "best_oa_location": {"pdf_url": "https://example.org/x1.pdf"},
    "open_access": {"oa_url": "https://example.org/x1"},
    "type": "article",
    "cited_by_count": 42,
}


def test_openalex_record_and_search(monkeypatch):
    record = search_openalex.work_to_record(OALEX_WORK)
    assert record["title"].startswith("Large Language Model")
    assert record["doi"] == "https://doi.org/10.1000/x1"
    assert record["authors"] == ["Alice Chen", "Bob Liu"]
    assert record["cited_by_count"] == 42

    payload = {"results": [OALEX_WORK]}
    monkeypatch.setattr(search_openalex.urllib.request, "urlopen",
                        lambda *a, **k: FakeResponse(json.dumps(payload).encode()))
    results = search_openalex.search("large language model", limit=1)
    assert len(results) == 1 and results[0]["year"] == 2024
    with pytest.raises(ValueError):
        search_openalex.search("x", limit=0)
    with pytest.raises(ValueError):
        search_openalex.search("x", from_year=2025, to_year=2020)


CROSSREF_ITEM = {
    "DOI": "10.1000/x1",
    "title": ["Large Language Model Compliance: A Survey"],
    "author": [{"given": "Alice", "family": "Chen"}],
    "container-title": ["Journal of AI"],
    "issued": {"date-parts": [[2024]]},
    "URL": "https://doi.org/10.1000/x1",
    "type": "journal-article",
    "is-referenced-by-count": 30,
}


def test_crossref_record_and_search(monkeypatch):
    record = search_crossref.work_to_record(CROSSREF_ITEM)
    assert record["year"] == 2024
    assert record["authors"] == ["Alice Chen"]
    payload = {"message": {"items": [CROSSREF_ITEM]}}
    monkeypatch.setattr(search_crossref.urllib.request, "urlopen",
                        lambda *a, **k: FakeResponse(json.dumps(payload).encode()))
    results = search_crossref.search("compliance", limit=1)
    assert len(results) == 1 and results[0]["venue"] == "Journal of AI"
    with pytest.raises(ValueError):
        search_crossref.search("x", limit=51)


ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <title>Auditable Comparisons of AI Systems</title>
    <published>2024-01-01T00:00:00Z</published>
    <author><name>Carol Wang</name></author>
    <summary>We propose an auditable framework.</summary>
    <link title="pdf" href="http://arxiv.org/pdf/2401.00001v1" type="application/pdf"/>
    <category term="cs.AI"/>
  </entry>
</feed>"""


def test_arxiv_parse_and_search(monkeypatch):
    parsed = search_arxiv.parse_feed(ARXIV_XML)
    assert len(parsed) == 1
    assert parsed[0]["year"] == 2024
    assert "/pdf/" in parsed[0]["pdf_url"]
    monkeypatch.setattr(search_arxiv.urllib.request, "urlopen",
                        lambda *a, **k: FakeResponse(ARXIV_XML.encode()))
    results = search_arxiv.search("auditable AI", max_results=1)
    assert len(results) == 1 and results[0]["source"] == "arxiv"
    with pytest.raises(ValueError):
        search_arxiv.search("x", max_results=0)


def test_verify_metadata(monkeypatch):
    assert verify_metadata.normalize_title("Large Language Model: A Survey!") == \
        "large language model a survey"
    assert verify_metadata.title_similarity("Compliance of LLMs", "Compliance of LLMs") == 1.0

    monkeypatch.setattr(verify_metadata, "_crossref",
                        lambda doi: {"source": "crossref", "doi": doi,
                                     "title": "Large Language Model Compliance",
                                     "year": 2024})
    monkeypatch.setattr(verify_metadata, "_openalex",
                        lambda doi: {"source": "openalex", "doi": doi,
                                     "title": "Large Language Model Compliance",
                                     "year": 2024})
    result = verify_metadata.verify("10.1000/x")
    assert result["status"] == "match" and result["title_match"] and result["year_match"]

    monkeypatch.setattr(verify_metadata, "_crossref", lambda doi: None)
    monkeypatch.setattr(verify_metadata, "_openalex", lambda doi: None)
    assert verify_metadata.verify("10.1000/none")["status"] == "not_found"


def test_query_plan_and_bibtex(tmp_path):
    plan = build_query_plan.build_plan("大语言模型 合规")
    assert "large language model" in plan["terms"]
    assert "compliance" in plan["terms"]
    assert plan["openalex_search"]
    custom = build_query_plan.build_plan("AI 学习", {"学习": ["learning", "pedagogy"]})
    assert "pedagogy" in custom["terms"]
    with pytest.raises(ValueError):
        build_query_plan.expand("x", {"bad": "not-list"})  # type: ignore[arg-type]

    records = [search_openalex.work_to_record(OALEX_WORK),
               {"title": "Another Paper", "authors": ["Dan Li"], "year": 2023,
                "venue": "X", "doi": "10", "source": "crossref"}]
    bib = export_bibtex.to_bibtex(records)
    assert "@article" in bib and "Alice" in bib
    assert export_bibtex.to_bibtex([]) == ""
    out = tmp_path / "refs.bib"
    source = tmp_path / "in.json"
    source.write_text(json.dumps({"results": records}), encoding="utf-8")
    assert export_bibtex.main(["--input", str(source), "-o", str(out)]) == 0
    assert out.exists() and "Another Paper" in out.read_text(encoding="utf-8")
