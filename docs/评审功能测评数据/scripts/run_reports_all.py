"""25 份样本全部出报告（docx/pdf）+ .md 格式覆盖。"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as q


def main() -> int:
    q.ensure_dirs()
    acc = q.jload(q.RAW / "accuracy-raw.json")
    rows = []
    for rec in acc["samples"]:
        body = (rec.get("review_a") or {}).get("body") or {}
        rid = body.get("review_id")
        if not rid:
            rows.append({"file": rec["file"], "review_id": None, "docx": 0, "pdf": 0, "status": "no_review"})
            continue
        row = {"file": rec["file"], "review_id": rid, "docx": 0, "pdf": 0, "docx_ms": 0.0, "pdf_ms": 0.0,
               "docx_magic": "", "pdf_magic": "", "status": "ok"}
        for fmt in ("docx", "pdf"):
            r = q.get(f"/api/report/{rid}?format={fmt}")
            row[fmt] = len(r.content) if r.status_code == 200 else 0
            row[fmt + "_ms"] = round(r.elapsed.total_seconds() * 1000, 1)
            row[fmt + "_magic"] = r.content[:4].decode("latin1") if r.content else ""
            if r.status_code != 200 or len(r.content) < 1000:
                row["status"] = f"{fmt}_failed_{r.status_code}"
        rows.append(row)
        print(rec["file"], rid, row["docx"], row["pdf"], row["status"])

    # .md 格式
    md = q.RAW / "tmp_inputs" / "QA20261116-test.md"
    md.write_text("""# 测评 Markdown 投标文件

项目名称：测评 Markdown 项目
项目编号：QA-2026-MD-001
采购人：测评采购人
投标人：测评投标人
投标报价：人民币 1,286,000.00 元
工期：90 日历天

## 技术方案
技术路线与总体架构。

## 实施方案
实施计划与进度计划。

## 质量保证措施
质量管理与质量控制。

## 应急预案
应急保障与安全保障。

## 类似项目业绩
同类项目合同业绩。

## 项目负责人
项目经理。

## 售后服务
售后服务与质保期。
""", encoding="utf-8")
    up = q.upload(md, name=md.name)
    md_row = {"file": md.name, "upload_status": up["status"], "parse_status": (up["body"] or {}).get("parse_status"),
              "fields": {f["name"]: f["value"] for f in (up["body"] or {}).get("fields") or []}}
    if up["status"] == 200:
        rv = q.review(up["body"]["doc_id"], "profile-a")
        md_row["review_status"] = rv["status"]
        md_row["total"] = (rv["body"] or {}).get("scoring", {}).get("total")
        md_row["review_id"] = (rv["body"] or {}).get("review_id")
        for fmt in ("docx", "pdf"):
            r = q.get(f"/api/report/{md_row['review_id']}?format={fmt}")
            md_row[fmt] = len(r.content) if r.status_code == 200 else 0
    print("MD", json.dumps(md_row, ensure_ascii=False))

    out = {"samples": rows,
           "md": md_row,
           "summary": {"samples": len(rows), "docx_ok": sum(1 for r in rows if r["docx"] > 1000),
                       "pdf_ok": sum(1 for r in rows if r["pdf"] > 1000),
                       "all_ok": sum(1 for r in rows if r["status"] == "ok")}}
    q.jdump(q.RAW / "reports-all.json", out)
    with (q.RAW / "reports-all.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "review_id", "docx_bytes", "pdf_bytes", "status", "docx_ms", "pdf_ms"])
        for r in rows:
            w.writerow([r["file"], r["review_id"], r["docx"], r["pdf"], r["status"],
                        r.get("docx_ms"), r.get("pdf_ms")])
    print(json.dumps(out["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
