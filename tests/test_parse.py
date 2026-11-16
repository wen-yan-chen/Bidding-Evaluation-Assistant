"""D2 解析链路单测：直接用样本文件打解析器与应用，不依赖 Docker。

跑法（项目根目录）：
  pip install -r requirements-dev.txt
  pytest -q
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.docmodel import Doc
from api.extract import extract_fields
from api.main import app
from api.parsers.dispatch import parse_file

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"
client = TestClient(app)


def parse_sample(name: str) -> Doc:
    path = SAMPLES / name
    blob = path.read_bytes()
    doc = parse_file(blob, path.name, "eval", "eval")
    doc.fields = extract_fields(doc)
    return doc


def assert_quotes_consistent(doc: Doc) -> None:
    for field in doc.fields:
        assert doc.full_text[field.char_start : field.char_end] == field.quote
        assert doc.page_of(field.char_start) == field.page
        assert field.quote in doc.full_text
    for clause in doc.clauses:
        assert doc.full_text[clause.char_start : clause.char_end] == clause.text


def test_docx_extracts_six_fields():
    doc = parse_sample("bid-001.docx")
    assert doc.parse_status in ("ok", "degraded")
    values = {f.name: f.value for f in doc.fields}
    assert values["项目名称"] == "示例市政务云平台二期设备采购项目"
    assert values["项目编号"] == "SJ-2026-GK-014"
    assert values["采购人"] == "示例市公共资源交易中心"
    assert values["投标人"] == "示例数智科技有限公司"
    assert values["报价"] == "1,286,000.00 元"
    assert values["工期"] == "90 日历天"
    assert_quotes_consistent(doc)


def test_pdf_page_source_is_native():
    doc = parse_sample("bid-004.pdf")
    assert doc.parse_status == "ok"
    assert doc.page_source == "native"
    assert len(doc.pages) >= 2
    assert_quotes_consistent(doc)


def test_gb18030_txt_decoded():
    doc = parse_sample("bid-006.txt")
    assert doc.meta.get("encoding") in ("gb18030", "utf-8", "utf-8-sig")
    assert "示例市 12345 热线智能客服运维项目" in doc.full_text
    assert_quotes_consistent(doc)


def test_boundary_missing_fields_not_fabricated():
    doc = parse_sample("bid-008.docx")
    names = {f.name for f in doc.fields}
    assert "报价" not in names
    assert "工期" not in names
    assert len(doc.fields) == 4


def test_boundary_currency_symbol_and_month_duration():
    doc = parse_sample("bid-009.txt")
    values = {f.name: f.value for f in doc.fields}
    assert values["报价"] == "968,000.00 元"
    assert values["工期"] == "6 个月"
    assert_quotes_consistent(doc)


def test_extension_structured_qualification_and_performance_lists():
    path = SAMPLES / "extension" / "ext-qual-list.md"
    doc = parse_file(path.read_bytes(), path.name, "eval", "eval")
    doc.fields = extract_fields(doc)
    by_name = {f.name: f for f in doc.fields}
    assert len(by_name["资质清单"].items) == 4
    assert by_name["资质清单"].items[0]["name"] == "营业执照"
    assert by_name["资质清单"].items[0]["quote"].startswith("1. 营业执照")
    assert len(by_name["业绩清单"].items) == 3
    assert by_name["业绩清单"].items[0]["project_name"] == "示例市政务云平台一期"
    for field in doc.fields:
        assert doc.full_text[field.char_start : field.char_end] == field.quote
        for item in field.items:
            assert doc.full_text[item["char_start"] : item["char_end"]] == item["quote"]


def test_clauses_split():
    doc = parse_sample("bid-010.docx")
    assert len(doc.clauses) >= 5
    labels = [c.label for c in doc.clauses]
    assert any("章" in label for label in labels)
    assert any("条" in label for label in labels)


def test_unsupported_extension_rejected():
    response = client.post(
        "/api/upload",
        files={"file": ("x.exe", b"MZ...", "application/octet-stream")},
    )
    assert response.status_code == 415


def test_upload_and_fetch_full_document():
    blob = (SAMPLES / "bid-002.docx").read_bytes()
    response = client.post(
        "/api/upload",
        files={"file": ("bid-002.docx", blob, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 200
    summary = response.json()
    assert summary["parse_status"] in ("ok", "degraded")
    assert len(summary["fields"]) == 6

    detail = client.get(f"/api/doc/{summary['doc_id']}")
    assert detail.status_code == 200
    payload = detail.json()
    doc = Doc.from_dict(payload)
    assert_quotes_consistent(doc)

    raw = client.get(f"/api/doc/{summary['doc_id']}/raw")
    assert raw.status_code == 200
    assert raw.content[:2] == b"PK"
