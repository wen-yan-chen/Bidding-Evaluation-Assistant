"""边界 / 异常 / 复现性 / 幂等 / 报告结构测试。

覆盖：
- 评分边界：比值 0.90/0.97/1.00、超限价、缺报价、工期 108/109、缺工期、缺章节
- 资格性边界：无重大违法记录（合规否定）、未提供营业执照（缺失 vs 效力不足）
- 异常路径：空文件、415、损坏文件、404、400、413、未授权 401
- 重复上传 / 重复评审 / 重复下载（幂等）
- 报告九章、页脚免责声明与页码、数值与评审 JSON 一致
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as q

TMP = q.RAW / "tmp_inputs"

BASE_TEXT = """项目名称：测评边界项目
项目编号：QA-2026-BOUNDARY
采购人：测评采购人
投标人：测评投标人
投标报价：人民币 {price} 元
工期：{days} 日历天
最高投标限价：人民币 2,000,000.00 元
技术方案：采用分层架构，详见技术路线。
实施方案：分三阶段实施，附进度计划。
质量保证措施：建立质量管理与质量控制双清单。
应急预案：重大故障应急保障与安全保障措施。
类似项目业绩：近三年同类项目合同业绩 3 项。
项目负责人：项目经理 1 名，技术负责人 1 名。
售后服务：7×24 售后服务与本地化服务响应。
"""

SECTIONS = ("技术方案", "实施方案", "质量保证", "应急预案", "业绩", "项目负责人", "售后服务")


def make_score_doc(name: str, price: str | None, days: str | None, sections: bool = True) -> Path:
    text = BASE_TEXT
    if price is None:
        text = "\n".join(line for line in text.splitlines() if not line.startswith("投标报价")) + "\n"
    else:
        text = text.replace("{price}", price)
    if days is None:
        text = "\n".join(line for line in text.splitlines() if not line.startswith("工期：")) + "\n"
    else:
        text = text.replace("{days}", days)
    if not sections:
        keep = ("项目名称", "项目编号", "采购人", "投标人", "投标报价", "工期", "最高投标限价")
        text = "\n".join(line for line in text.splitlines() if line.split("：")[0] in keep) + "\n"
    path = TMP / name
    path.write_text(text, encoding="utf-8")
    return path


SCORE_CASES = [
    # name, price, days, sections, expected_a_total, expected_b_total, expected_a_items(dict of changed), note
    ("QA20261116-score-ratio-090.txt", "1,800,000.00", "90", True, 100.0, 100.0, {}, "比值 0.90 边界"),
    ("QA20261116-score-ratio-097.txt", "1,940,000.00", "90", True, 96.0, 97.0, {"P1": 36.0}, "比值 0.97 边界"),
    ("QA20261116-score-ratio-100.txt", "2,000,000.00", "90", True, 88.0, 91.0, {"P1": 28.0}, "比值 1.00 边界"),
    ("QA20261116-score-over-cap.txt", "2,000,001.00", "90", True, 60.0, 70.0, {"P1": 0.0}, "超限价"),
    ("QA20261116-score-no-price.txt", None, "90", True, 60.0, 70.0, {"P1": 0.0}, "缺报价"),
    ("QA20261116-score-days-108.txt", "1,286,000.00", "108", True, 98.0, 97.0, {"T5": 4.0}, "工期 108 天（20% 边界）"),
    ("QA20261116-score-days-109.txt", "1,286,000.00", "109", True, 94.0, 92.0, {"T5": 0.0}, "工期 109 天（超 20%）"),
    ("QA20261116-score-no-days.txt", "1,286,000.00", None, True, 94.0, 92.0, {"T5": 0.0}, "缺工期"),
    ("QA20261116-score-no-sections.txt", "1,286,000.00", "90", False, 46.0, 38.0, {"T1": 0.0, "T2": 0.0, "T3": 0.0, "T4": 0.0,
                                                                         "B1": 0.0, "B2": 0.0, "B3": 0.0}, "缺技术/商务章节"),
]


def main() -> int:
    q.ensure_dirs()
    TMP.mkdir(parents=True, exist_ok=True)
    out: dict = {"started_at": q.now(), "scoring": [], "qualification": [], "negative": [], "repeat": [],
                 "report": [], "idempotent": []}

    # ---------- 评分边界 ----------
    for name, price, days, sections, exp_a, exp_b, changed, note in SCORE_CASES:
        path = make_score_doc(name, price, days, sections)
        up = q.upload(path)
        rec = {"case": name, "note": note, "price": price, "days": days, "sections": sections,
               "upload_status": up["status"], "doc_id": (up["body"] or {}).get("doc_id"),
               "expected_a_total": exp_a, "expected_b_total": exp_b, "changed": changed,
               "a": None, "b": None, "problems": []}
        if up["status"] == 200:
            doc_id = rec["doc_id"]
            doc = q.get_json(f"/api/doc/{doc_id}")
            rec["fields"] = {f["name"]: f["value"] for f in doc.get("fields") or []}
            for profile, exp_total in (("profile-a", exp_a), ("profile-b", exp_b)):
                rv = q.review(doc_id, profile)
                rec[profile[-1]] = rv
                body = rv.get("body") or {}
                got = (body.get("scoring") or {}).get("total")
                if abs(float(got if got is not None else -999) - exp_total) > 1e-9:
                    rec["problems"].append(f"{profile} 总分 {got} != 手工期望 {exp_total}")
                items = {i["item_id"]: i for i in (body.get("scoring") or {}).get("items") or []}
                # 手工 item 期望只针对 profile-a；profile-b 的分项由独立复算 + 总分覆盖
                for iid, exp_score in (changed if profile == "profile-a" else {}).items():
                    if abs(float(items.get(iid, {}).get("score", -1)) - exp_score) > 1e-9:
                        rec["problems"].append(f"{profile} {iid} {items.get(iid, {}).get('score')} != {exp_score}")
                rc = q.recompute_scoring(doc, profile)
                rec["problems"] += [f"{profile} {x}" for x in q.compare_scoring(body, rc)]
        out["scoring"].append(rec)
        print(f"SCORE {name:<36} A={((rec['a'] or {}).get('body') or {}).get('scoring', {}).get('total')} "
              f"B={((rec['b'] or {}).get('body') or {}).get('scoring', {}).get('total')} problems={rec['problems']}")

    # ---------- 资格性边界 ----------
    qual_cases = [
        ("QA20261116-qual-neg-compliant.txt",
         "投标人：测评投标人\n营业执照：已提供\n统一社会信用代码：91330100TEST000001\n"
         "资质证书：信息系统集成资质\n安全生产许可证：已提供\n法定代表人授权书：已附法定代表人签字并加盖单位公章\n"
         "财务报告：已提供近一年度审计报告\n社会保险：已缴纳社会保险\n"
         "我方近三年内无重大违法记录，亦无行贿犯罪记录。\n"
         "中小企业声明函：已提供\n联合体协议：本项目不接受联合体投标，无需提供联合体协议。\n"
         "项目负责人：项目经理 1 名。\n",
         {"R07": "provided"}, "合规否定式：无重大违法记录"),
        ("QA20261116-qual-neg-missing.txt",
         "投标人：测评投标人\n未提供营业执照。\n未提供财务报告。\n"
         "其余材料：无。\n",
         {"R01": "missing", "R05": "missing"}, "明说未提供：应判缺失还是效力不足"),
        ("QA20261116-qual-no-need.txt",
         "投标人：测评投标人\n无需提供社会保险缴纳证明。\n无需提供中小企业声明函。\n",
         {"R06": "missing", "R08": "missing"}, "“无需提供”是否算缺失"),
    ]
    for name, text, expected, note in qual_cases:
        path = TMP / name
        path.write_text(text, encoding="utf-8")
        up = q.upload(path)
        rec = {"case": name, "note": note, "expected": expected, "upload_status": up["status"], "doc_id": None,
               "states": {}, "counts": {}, "mismatch": []}
        if up["status"] == 200:
            rec["doc_id"] = up["body"].get("doc_id")
            rv = q.review(rec["doc_id"], "profile-a")
            body = rv.get("body") or {}
            qual = body.get("qualification") or {}
            rec["states"] = {i["rule_id"]: i["state"] for i in qual.get("items") or []}
            rec["counts"] = qual.get("counts")
            rec["quotes"] = {i["rule_id"]: i.get("quote") for i in qual.get("items") or []}
            for rid, want in expected.items():
                if rec["states"].get(rid) != want:
                    rec["mismatch"].append({"rule_id": rid, "expected": want, "actual": rec["states"].get(rid)})
        out["qualification"].append(rec)
        print(f"QUAL {name:<38} states={rec['states']} mismatch={rec['mismatch']}")

    # ---------- 异常路径 ----------
    neg = []
    neg.append({"case": "空文件", **q.upload_bytes(b"", "QA20261116-empty.txt")})
    neg.append({"case": "不支持扩展名", **q.upload_bytes(b"hello", "QA20261116-bad.exe")})
    neg.append({"case": "损坏 docx", **q.upload_bytes(b"not a zip at all", "QA20261116-corrupt.docx")})
    neg.append({"case": "损坏 pdf", **q.upload_bytes(b"%PDF-1.4\nbroken", "QA20261116-corrupt.pdf")})
    big = b"0" * (51 * 1024 * 1024)
    neg.append({"case": "51MB PDF", **q.upload_bytes(big, "QA20261116-big.pdf")})
    del big
    for path, case in [("/api/doc/20261116-deadbeef", "不存在文档"),
                       ("/api/doc/not-a-valid-id", "非法 doc_id"),
                       ("/api/doc/20261116-deadbeef/raw", "不存在原件"),
                       ("/api/review/rv-20260101-000000-abcdef", "不存在评审")]:
        r = q.get(path)
        neg.append({"case": case, "path": path, "status": r.status_code, "body": r.text[:300]})
    r = q.get("/api/report/rv-20260101-000000-abcdef?format=docx")
    neg.append({"case": "不存在报告", "path": "/api/report/...", "status": r.status_code, "body": r.text[:300]})
    r = q.get("/api/report/rv-20261116-141905-60a203?format=xlsx")
    neg.append({"case": "不支持的报格式", "path": "/api/report?format=xlsx", "status": r.status_code, "body": r.text[:300]})
    r = q.get(f"/api/doc/{(out['scoring'][0].get('doc_id') or 'x')}/html")
    neg.append({"case": "非 docx 请求 Word HTML", "path": "/api/doc/<txt>/html", "status": r.status_code, "body": r.text[:300]})
    r = q.SESSION.delete(q.BASE + "/api/admin/doc/20261116-deadbeef", timeout=30)
    neg.append({"case": "未登录删除", "path": "DELETE /api/admin/doc/...", "status": r.status_code, "body": r.text[:300]})
    r = q.SESSION.post(q.BASE + "/api/review", json={"doc_id": "20261116-deadbeef", "profile_id": "profile-a"}, timeout=30)
    neg.append({"case": "不存在文档评审", "path": "POST /api/review", "status": r.status_code, "body": r.text[:300]})
    out["negative"] = neg
    for n in neg:
        print(f"NEG {n['case']:<24} status={n.get('status')} body={str(n.get('body'))[:120]}")

    # ---------- 重复上传 / 重复评审 ----------
    src = q.ROOT / "data" / "samples" / "bid-001.docx"
    for i in range(3):
        up = q.upload(src, name=f"QA20261116-repeat-{i}.docx")
        rec = {"run": i + 1, "status": up["status"], "doc_id": (up["body"] or {}).get("doc_id"),
               "sha256": (up["body"] or {}).get("sha256"),
               "fields": {f["name"]: f["value"] for f in (up["body"] or {}).get("fields") or []}}
        if up["status"] == 200:
            rv = q.review(rec["doc_id"], "profile-a")
            b = rv.get("body") or {}
            rec["review_id"] = b.get("review_id")
            rec["total"] = (b.get("scoring") or {}).get("total")
            rec["items"] = [(x["item_id"], x["score"]) for x in (b.get("scoring") or {}).get("items") or []]
            rec["risks"] = [(x["rule_id"], x["page"], x["quote"]) for x in b.get("risks") or []]
            rec["counts"] = (b.get("qualification") or {}).get("counts")
        out["repeat"].append(rec)
        print(f"REPEAT {i+1}: status={rec['status']} total={rec.get('total')}")

    # 同一 review 再评审 2 次
    rep = out["repeat"][0]
    same = []
    for i in range(2):
        rv = q.review(rep["doc_id"], "profile-a")
        b = rv.get("body") or {}
        same.append({"review_id": b.get("review_id"), "total": (b.get("scoring") or {}).get("total"),
                     "items": [(x["item_id"], x["score"]) for x in (b.get("scoring") or {}).get("items") or []],
                     "risks": [(x["rule_id"], x["page"], x["quote"]) for x in b.get("risks") or []],
                     "counts": (b.get("qualification") or {}).get("counts")})
    baseline = {"total": rep["total"], "items": rep["items"], "risks": rep["risks"], "counts": rep["counts"]}
    consistency = [s["total"] == baseline["total"] and s["items"] == baseline["items"]
                   and s["risks"] == baseline["risks"] and s["counts"] == baseline["counts"] for s in same]
    out["repeat_consistency"] = {"same_3_runs": all(consistency), "runs": same}

    # ---------- 重复上传一致性 ----------
    shas = {r.get("sha256") for r in out["repeat"]}
    field_sets = {json.dumps(r.get("fields"), ensure_ascii=False, sort_keys=True) for r in out["repeat"]}
    out["repeat_upload_same"] = len(shas) == 1 and len(field_sets) == 1

    # ---------- 报告 ----------
    # 用 bid-001 的 A/B 两次评审 + risk-001
    targets = []
    for rec in json.loads((q.RAW / "accuracy-raw.json").read_text(encoding="utf-8"))["samples"]:
        if rec["file"] == "bid-001.docx":
            targets.append(("bid-001-A", (rec["review_a"]["body"])["review_id"]))
            targets.append(("bid-001-B", (rec["review_b"]["body"])["review_id"]))
    for rec in json.loads((q.RAW / "accuracy-raw.json").read_text(encoding="utf-8"))["risk"]:
        if rec["file"].endswith("risk-001.docx"):
            targets.append(("risk-001-A", rec["review"]["body"]["review_id"]))

    from docx import Document
    from pypdf import PdfReader

    for label, review_id in targets:
        rec = {"label": label, "review_id": review_id, "docx": {}, "pdf": {}, "problems": []}
        rv = q.get_json(f"/api/review/{review_id}")
        total = rv["summary"]["total_score"]
        counts = rv["qualification"]["counts"]
        risk_count = len(rv["risks"])
        for fmt in ("docx", "pdf"):
            r = q.get(f"/api/report/{review_id}?format={fmt}")
            rec[fmt]["status"] = r.status_code
            rec[fmt]["size"] = len(r.content)
            rec[fmt]["sha256"] = hashlib.sha256(r.content).hexdigest()
            rec[fmt]["disposition"] = r.headers.get("content-disposition")
            if r.status_code == 200:
                if fmt == "docx":
                    doc = Document(io.BytesIO(r.content))
                    text = "\n".join([p.text for p in doc.paragraphs] +
                                     [c.text for t in doc.tables for row in t.rows for c in row.cells])
                    rec[fmt]["tables"] = len(doc.tables)
                    footer = "\n".join(p.text for s in doc.sections for p in s.footer.paragraphs)
                    rec[fmt]["footer"] = footer
                    footer_xml = "\n".join(s.footer._element.xml for s in doc.sections)
                    rec[fmt]["footer_has_page_field"] = "PAGE" in footer_xml
                else:
                    reader = PdfReader(io.BytesIO(r.content))
                    text = "\n".join((p.extract_text() or "") for p in reader.pages)
                    rec[fmt]["pages"] = len(reader.pages)
                    rec[fmt]["page_markers"] = [f"第 {i} 页" for i in range(1, len(reader.pages) + 1)
                                                if f"第 {i} 页" in text]
                    footer = text[-400:]
                    rec[fmt]["footer"] = footer
                rec[fmt]["has_disclaimer"] = q.ROOT.joinpath("VERSION").exists() and "AI 辅助评审结果，最终以评标委员会评审结论为准" in text
                heads = [h for h in ("一、", "二、", "三、", "四、", "五、", "六、", "七、", "八、", "九、") if h in text]
                rec[fmt]["headings"] = heads
                rec[fmt]["has_total"] = str(total) in text.replace(" ", "")
                rec[fmt]["has_risk_count"] = str(risk_count) in text
                rec[fmt]["has_qual_counts"] = str(counts["provided"]) in text and str(counts["missing"]) in text
                if len(heads) != 9:
                    rec["problems"].append(f"{fmt} 章节数 {len(heads)} != 9")
                if not rec[fmt]["has_disclaimer"]:
                    rec["problems"].append(f"{fmt} 缺免责声明")
                if not rec[fmt]["has_total"]:
                    rec["problems"].append(f"{fmt} 缺总分 {total}")
        # 幂等：再下载一次
        for fmt in ("docx", "pdf"):
            r2 = q.get(f"/api/report/{review_id}?format={fmt}")
            rec[fmt]["sha256_2"] = hashlib.sha256(r2.content).hexdigest()
            if rec[fmt]["sha256"] != rec[fmt]["sha256_2"]:
                rec["problems"].append(f"{fmt} 重复下载不幂等")
        meta = q.get_json(f"/api/report/{review_id}/meta")
        rec["meta"] = meta
        out["report"].append(rec)
        print(f"REPORT {label}: docx={rec['docx'].get('size')}B pdf={rec['pdf'].get('size')}B "
              f"heads={len(rec['docx'].get('headings') or [])}/{len(rec['pdf'].get('headings') or [])} problems={rec['problems']}")

    q.jdump(q.RAW / "edges-raw.json", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
