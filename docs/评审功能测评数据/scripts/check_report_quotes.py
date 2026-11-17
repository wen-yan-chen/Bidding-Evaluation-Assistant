"""报告页码与 quote 逐项核对（docx/pdf 文本 vs 评审 JSON / 原文）。"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as q
from docx import Document
from pypdf import PdfReader


def text_docx(blob: bytes) -> str:
    doc = Document(io.BytesIO(blob))
    return "\n".join([p.text for p in doc.paragraphs] + [c.text for t in doc.tables for row in t.rows for c in row.cells])


def text_pdf(blob: bytes) -> str:
    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(blob)).pages)


def norm(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def main() -> int:
    acc = q.jload(q.RAW / "accuracy-raw.json")
    bid = next(r for r in acc["samples"] if r["file"] == "bid-001.docx")
    risk = next(r for r in acc["risk"] if r["file"].endswith("risk-001.docx"))
    targets = [("bid-001-A", bid["review_a"]["body"], bid["doc"]["doc_id"]),
               ("risk-001-A", risk["review"]["body"], risk["doc_id"])]
    out = {"items": []}
    for label, review, doc_id in targets:
        doc = q.get_json(f"/api/doc/{doc_id}")
        full = doc.get("full_text") or ""
        item = {"label": label, "review_id": review["review_id"], "formats": {}}
        for fmt in ("docx", "pdf"):
            r = q.get(f"/api/report/{review['review_id']}?format={fmt}")
            text = text_docx(r.content) if fmt == "docx" else text_pdf(r.content)
            ntext = norm(text)
            checks = {"field_quotes": [], "qual_quotes": [], "risk_quotes": [], "pages": []}
            for f in doc.get("fields") or []:
                checks["field_quotes"].append({"name": f["name"], "quote_in_report": norm(f["quote"]) in ntext,
                                               "quote_in_source": f["quote"] in full,
                                               "page": f["page"], "page_in_report": f"第{f['page']}页" in ntext})
            for qi in review["qualification"]["items"]:
                if qi.get("quote"):
                    checks["qual_quotes"].append({"rule_id": qi["rule_id"], "quote_in_report": norm(qi["quote"]) in ntext,
                                                  "page": qi["page"], "page_in_report": (f"第{qi['page']}页" in ntext) if qi.get("page") else None})
            for rk in review["risks"]:
                checks["risk_quotes"].append({"rule_id": rk["rule_id"], "quote_in_report": norm(rk["quote"]) in ntext,
                                              "quote_in_source": rk["quote"] in full, "page": rk["page"],
                                              "page_in_report": f"第{rk['page']}页" in ntext})
            checks["has_disclaimer"] = "AI辅助评审结果，最终以评标委员会评审结论为准" in ntext
            checks["has_total"] = norm(str(review["scoring"]["total"])) in ntext
            checks["qual_counts_in_report"] = all(norm(str(v)) in ntext for v in review["qualification"]["counts"].values())
            checks["risk_count_in_report"] = norm(str(len(review["risks"]))) in ntext
            checks["chapter_markers"] = [m for m in ("招投标评审报告", "评审依据", "项目与投标人信息", "资格性核验",
                                                     "分项评分", "风险清单", "合同摘要", "结论与建议", "免责声明") if norm(m) in ntext]
            item["formats"][fmt] = checks
        out["items"].append(item)
    q.jdump(q.RAW / "report-quote-page-check.json", out)
    print(json.dumps(out, ensure_ascii=False, indent=2)[:8000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
