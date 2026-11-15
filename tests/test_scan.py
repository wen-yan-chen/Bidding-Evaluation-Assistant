"""D3 扫描件与边界样本单测（需要 OCR 依赖，跑在容器内）。

覆盖：
- 扫描件 pdf 无文本层 → 走 OCR → 抽到字段，且 quote/页码仍自洽；
- 空白页 → 记为 empty_pages 并降级，但整体不 failed；
- 低分辨率 / 旋转页 → 允许识别差，但不得崩、不得编造字段。
"""

from __future__ import annotations

from pathlib import Path

from api.docmodel import Doc
from api.extract import extract_fields
from api.parsers.dispatch import parse_file

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"


def parse_file_at(path: Path) -> Doc:
    blob = path.read_bytes()
    doc = parse_file(blob, path.name, "eval", "eval")
    doc.fields = extract_fields(doc)
    return doc


def assert_quotes_consistent(doc: Doc) -> None:
    for field in doc.fields:
        assert doc.full_text[field.char_start : field.char_end] == field.quote
        assert doc.page_of(field.char_start) == field.page


def test_scan_pdf_uses_ocr_and_extracts_fields():
    doc = parse_file_at(SAMPLES / "scan-001.pdf")
    assert doc.parse_status in ("ok", "degraded")
    assert doc.meta.get("ocr_pages"), "扫描件应记录 OCR 页"
    assert len(doc.full_text) > 200
    assert len(doc.fields) >= 4
    assert_quotes_consistent(doc)


def test_scan_second_sample_has_project_name():
    doc = parse_file_at(SAMPLES / "scan-002.pdf")
    values = {f.name: f.value for f in doc.fields}
    assert "示例" in values.get("项目名称", "")
    assert len(values.get("项目编号", "")) >= 6
    assert_quotes_consistent(doc)


def test_blank_first_page_degrades_not_crashes():
    doc = parse_file_at(SAMPLES / "boundary" / "blank-page.pdf")
    assert doc.parse_status in ("ok", "degraded")
    assert doc.meta.get("empty_pages")
    assert len(doc.full_text) > 100  # 第 2 页仍应解析出内容


def test_lowres_scan_does_not_crash_or_fabricate():
    doc = parse_file_at(SAMPLES / "boundary" / "lowres-scan.pdf")
    assert doc.parse_status in ("ok", "degraded")
    values = {f.name: f.value for f in doc.fields}
    # 允许识别失败，但只要抽出来就必须来自原文
    assert_quotes_consistent(doc)
    if "报价" in values:
        assert "元" in values["报价"]


def test_rotated_scan_degrades_gracefully():
    doc = parse_file_at(SAMPLES / "boundary" / "rotated-scan.pdf")
    assert doc.parse_status in ("ok", "degraded", "failed")
    assert_quotes_consistent(doc)
