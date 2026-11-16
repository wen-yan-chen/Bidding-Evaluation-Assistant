"""D6 风险扫描单测：合规定式、否定上下文、计算型规则、误报基线。"""

from __future__ import annotations

from pathlib import Path

from api import checks, rules
from api.extract import extract_fields
from api.parsers.dispatch import parse_file
from api.review import qualification

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"
CONTEXT = {"max_price": 2000000, "min_validity_days": 90, "below_cost_ratio": 0.6, "near_cap_ratio": 0.97}


def load(path: Path):
    doc = parse_file(path.read_bytes(), path.name, "eval", "eval")
    doc.fields = extract_fields(doc)
    return doc


def scan(path: Path, context: dict | None = None) -> set[str]:
    return {h["rule_id"] for h in rules.scan_doc(load(path), context=context or CONTEXT)}


def test_clean_sample_has_no_hits():
    # bid-001 含「已按招标文件要求提交投标保证金」「有效期 90 天」「大写与小写一致」
    assert scan(SAMPLES / "bid-001.docx") == set()


def test_extension_quote_table_rules():
    path = SAMPLES / "extension" / "ext-quote-table.md"
    hits = scan(path)
    assert {"R34", "R36", "R38", "R39"} <= hits


def test_project_type_gate_applies_to_tender_only_rules():
    path = SAMPLES / "extension" / "ext-quote-table.md"
    engineering = {h["rule_id"] for h in rules.scan_doc(load(path), context={"project_type": "engineering"})}
    goods = {h["rule_id"] for h in rules.scan_doc(load(path), context={"project_type": "goods_services"})}
    assert "R36" in engineering
    assert "R36" not in goods


def test_qualification_project_type_gate():
    doc = load(SAMPLES / "bid-001.docx")
    goods = qualification.check(doc, project_type="goods_services")
    engineering = qualification.check(doc, project_type="engineering")
    assert "R03" in goods["not_applicable_rule_ids"]
    assert "R03" not in engineering["not_applicable_rule_ids"]


def test_implanted_rules_are_detected():
    assert "R12" in scan(SAMPLES / "risk" / "risk-001.docx")
    assert "R13" in scan(SAMPLES / "risk" / "risk-002.docx")
    assert "R17" in scan(SAMPLES / "risk" / "risk-003.docx")
    assert "R37" in scan(SAMPLES / "risk" / "risk-004.docx")
    assert "R31" in scan(SAMPLES / "risk" / "risk-009.docx")
    assert "R21" in scan(SAMPLES / "risk" / "risk-006.docx")
    assert "R27" in scan(SAMPLES / "risk" / "risk-007.docx")
    assert "R20" in scan(SAMPLES / "risk" / "risk-008.docx")


def test_hits_carry_traceable_span():
    doc = load(SAMPLES / "risk" / "risk-001.docx")
    hits = rules.scan_doc(doc, context=CONTEXT)
    assert hits
    for hit in hits:
        assert doc.slice_text(hit["char_start"], hit["char_end"]) == hit["quote"]
        assert doc.page_of(hit["char_start"]) == hit["page"]


def test_no_cap_in_document_means_no_price_checks():
    # bid-002 正文没有最高限价，价格类规则不应凭 context 硬比
    hits = rules.scan_doc(load(SAMPLES / "bid-002.docx"), context=CONTEXT)
    assert not {h["rule_id"] for h in hits} & {"R12", "R13", "R31"}
    notes = "；".join(rules.scan_notes(load(SAMPLES / "bid-002.docx")))
    assert "未载明最高投标限价" in notes


def test_cn_numeral_parsing():
    assert checks.cn_to_int("壹佰贰拾捌万陆仟元整") == 1_286_000
    assert checks.cn_to_int("玖拾陆万捌仟元") == 968_000
    assert checks.cn_to_int("贰佰叁拾万元整") == 2_300_000
    assert checks.cn_to_int("壹佰贰拾万元整") == 1_200_000


def test_qualification_missing_detected():
    doc = load(SAMPLES / "risk" / "risk-005.docx")
    result = qualification.check(doc)
    states = {i["rule_id"]: i["state"] for i in result["items"]}
    assert states["R01"] == "missing"

    doc2 = load(SAMPLES / "risk" / "risk-010.docx")
    states2 = {i["rule_id"]: i["state"] for i in qualification.check(doc2)["items"]}
    assert states2["R09"] == "missing"


def test_scan_is_deterministic():
    path = SAMPLES / "risk" / "risk-001.docx"
    first = [(h["rule_id"], h["char_start"]) for h in rules.scan_doc(load(path), context=CONTEXT)]
    second = [(h["rule_id"], h["char_start"]) for h in rules.scan_doc(load(path), context=CONTEXT)]
    assert first == second


def test_same_rule_is_not_counted_twice_in_one_document():
    # risk-015 正文两处“美元”，同一 R35 只应保留一条证据，避免风险数虚高
    hits = rules.scan_doc(load(SAMPLES / "risk" / "risk-015.docx"), context=CONTEXT)
    assert [h["rule_id"] for h in hits].count("R35") == 1
