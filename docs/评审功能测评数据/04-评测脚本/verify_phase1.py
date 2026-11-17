"""阶段 0/1 改动后的 API/报告/数据一致性验证（会创建并删除一份临时文档与少量临时评审）。"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as q
from docx import Document
from pypdf import PdfReader

TEXT = """项目名称：阶段1资格性验证项目
项目编号：QA-2026-PHASE1
采购人：测评采购人
投标人：测评投标人
投标报价：人民币 1,286,000.00 元
工期：90 日历天
最高投标限价：人民币 2,000,000.00 元
营业执照：已提供。
社会保险：已缴纳社会保险。
我方近三年内无重大违法记录，亦无行贿犯罪记录。
中小企业声明函：已提供。
项目负责人：项目经理 1 名。
联合体协议：本项目不接受联合体投标，无需提供联合体协议。
"""


def main() -> int:
    q.ensure_dirs()
    out: dict = {}
    s = q.admin_login()
    docs = s.get(q.BASE + "/api/documents?limit=1000", timeout=30).json()
    out["documents"] = {"count": docs.get("count"),
                        "contains_invalid_eval": any(d.get("doc_id") == "eval" for d in docs.get("items") or [])}
    out["eval_api"] = {"status": (r := s.get(q.BASE + "/api/doc/eval", timeout=10)).status_code,
                       "body": r.text[:120]}

    # 临时文档：合规否定式 + 无需提供
    path = q.RAW / "tmp_inputs" / "QA20261116-phase1-qual.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TEXT, encoding="utf-8")
    up = q.upload(path, name="QA20261116-phase1-qual.txt")
    doc_id = (up["body"] or {}).get("doc_id")
    review = q.review(doc_id, "profile-a")
    body = review["body"]
    states = {i["rule_id"]: i for i in body["qualification"]["items"]}
    out["qualification"] = {
        "counts": body["qualification"]["counts"],
        "R06": states["R06"]["state"], "R07": states["R07"]["state"],
        "R08": states["R08"]["state"], "R10": states["R10"]["state"],
        "R09": states["R09"]["state"], "R09_applicable": states["R09"].get("applicable"),
        "R09_note": states["R09"].get("note"),
    }
    rid = body["review_id"]
    for fmt in ("docx", "pdf"):
        r = q.get(f"/api/report/{rid}?format={fmt}")
        if fmt == "docx":
            doc = Document(io.BytesIO(r.content))
            text = "\n".join([p.text for p in doc.paragraphs] +
                             [c.text for t in doc.tables for row in t.rows for c in row.cells])
        else:
            text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(r.content)).pages)
        out.setdefault("report", {})[fmt] = {
            "status": r.status_code, "size": len(r.content),
            "has_chapter_1": "一、封面与文档信息" in text,
            "has_chapter_9": "九、免责声明" in text,
        }
    s.delete(q.BASE + f"/api/admin/doc/{doc_id}", timeout=120)
    out["temp_doc_deleted"] = doc_id

    # risk-015 去重（用现有文档，临时评审后删除评审）
    risk_doc = next((d for d in docs.get("items") or [] if d.get("file_name") == "risk-015.docx"), None)
    if risk_doc:
        rv = q.review(risk_doc["doc_id"], "profile-a")
        ids = [x["rule_id"] for x in (rv["body"] or {}).get("risks") or []]
        out["risk_015"] = {"levels": (rv["body"] or {}).get("summary"), "rule_ids": ids,
                           "r35_count": ids.count("R35")}
        s.delete(q.BASE + f"/api/admin/review/{(rv['body'] or {}).get('review_id')}", timeout=120)

    # bid-001 基线（临时评审后删除）
    bid = next((d for d in docs.get("items") or [] if d.get("file_name") == "bid-001.docx"), None)
    if bid:
        rv = q.review(bid["doc_id"], "profile-a")
        b = rv["body"]
        out["bid_001"] = {"total": b["summary"]["total_score"], "counts": b["qualification"]["counts"],
                          "risks": len(b["risks"])}
        s.delete(q.BASE + f"/api/admin/review/{b['review_id']}", timeout=120)

    q.jdump(q.RAW / "phase1-verify.json", out)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
