"""D4 规则库与 MCP 工具单测。

覆盖：
- 40 条规则、四类各 10 条、id 连续；
- 依据三态：verified 必须有条号；pending/na 不得带 basis，且运行期输出规范文案；
- 规则库指纹与知识库导出清单一致；
- 扫描命中带 page/quote，且切片与页码自洽；
- `/api/rules` 接口可用；
- MCP 三个工具函数（直接调用，不走 SSE）返回结构正确。
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from api import rules as rules_api
from api.extract import extract_fields
from api.main import app
from api.parsers.dispatch import parse_file

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"
client = TestClient(app)


def parse_sample(name: str, doc_id: str = "eval"):
    path = SAMPLES / name
    doc = parse_file(path.read_bytes(), path.name, doc_id, "eval")
    doc.fields = extract_fields(doc)
    return doc


def test_rule_count_and_categories():
    loaded = rules_api.load_rules()
    assert len(loaded) == 40
    counts: dict[str, int] = {}
    for rule in loaded:
        counts[rule.category] = counts.get(rule.category, 0) + 1
    assert counts == {"资质门槛": 10, "废标条款": 10, "围标串标": 10, "报价异常": 10}
    assert [r.id for r in loaded] == [f"R{n:02d}" for n in range(1, 41)]


def test_basis_three_state():
    for rule in rules_api.load_rules():
        if rule.basis_status == "verified":
            assert rule.basis and "第" in rule.basis
            assert rule.legal_basis == rule.basis
        elif rule.basis_status == "pending":
            assert rule.basis == ""
            assert rule.legal_basis == "未检索到权威依据"
        else:
            assert rule.basis_status == "na"
            assert rule.basis == ""
            assert rule.legal_basis == "经验判据，无法条依据"


def test_digest_matches_knowledge_base():
    manifest = json.loads((ROOT / "knowledge" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["digest"] == rules_api.rules_digest()
    assert manifest["rule_count"] == 40


def test_scan_hits_carry_traceable_span():
    # 干净样本不应命中；用植入风险样本验证溯源字段
    assert rules_api.scan_doc(parse_sample("bid-001.docx")) == []
    doc = parse_sample("risk/risk-001.docx")
    hits = rules_api.scan_doc(doc, context={"max_price": 2000000, "min_validity_days": 90})
    assert hits
    for hit in hits[:10]:
        assert doc.slice_text(hit["char_start"], hit["char_end"]) == hit["quote"]
        assert doc.page_of(hit["char_start"]) == hit["page"]
        assert hit["rule_id"].startswith("R")
        assert "legal_basis" in hit and hit["legal_basis"]


def test_scan_is_deterministic():
    doc = parse_sample("bid-002.docx")
    first = rules_api.scan_doc(doc)
    second = rules_api.scan_doc(doc)
    assert [(h["rule_id"], h["char_start"]) for h in first] == [(h["rule_id"], h["char_start"]) for h in second]


def test_rules_api_endpoints():
    resp = client.get("/api/rules")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["stats"]["total"] == 40
    assert payload["count"] == 40

    one = client.get("/api/rules/R12")
    assert one.status_code == 200
    assert one.json()["category"] == "废标条款"
    assert one.json()["basis_status"] == "verified"

    missing = client.get("/api/rules/R99")
    assert missing.status_code == 404


def test_mcp_tools_direct_call():
    from api import store
    from mcps import bid_review_mcp as mcp_tools

    doc = parse_sample("bid-001.docx", doc_id="20261115-abcdef01")
    store.save_doc(doc)  # MCP 工具按 doc_id 从 data/parsed 读，先落盘

    parsed = mcp_tools.parse_tender(doc.doc_id)
    assert parsed["doc_id"] == doc.doc_id
    assert len(parsed["fields"]) == len(doc.fields)

    scanned = mcp_tools.scan_risks(doc.doc_id)
    assert scanned["hit_count"] == len(scanned["hits"])
    assert scanned["rule_digest"] == rules_api.rules_digest()

    quote = doc.fields[0].quote
    located = mcp_tools.locate_span(doc.doc_id, quote)
    assert located["found"] is True
    assert located["page"] == doc.fields[0].page

    bad = mcp_tools.locate_span(doc.doc_id, "这句话一定不在原文里")
    assert bad["found"] is False

    err = mcp_tools.parse_tender("not-a-doc-id")
    assert "error" in err
