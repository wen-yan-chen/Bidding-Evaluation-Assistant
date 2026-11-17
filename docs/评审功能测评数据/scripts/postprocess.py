"""从 accuracy-raw.json 重算汇总（修正首版汇总里 text/scan 标签互换的问题）。"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as q


def main() -> int:
    raw = q.jload(q.RAW / "accuracy-raw.json")
    samples = raw["samples"]
    field_rows = [r for rec in samples if rec.get("fields") for r in rec["fields"]["rows"]]
    text_rows = [r for rec in samples if rec.get("fields") and not rec["ocr"] for r in rec["fields"]["rows"]]
    scan_rows = [r for rec in samples if rec.get("fields") and rec["ocr"] for r in rec["fields"]["rows"]]
    parse = {
        "text": sum(1 for r in samples if not r["ocr"] and (r.get("doc") or {}).get("parse_status") != "failed"),
        "text_total": sum(1 for r in samples if not r["ocr"]),
        "scan": sum(1 for r in samples if r["ocr"] and (r.get("doc") or {}).get("parse_status") != "failed"),
        "scan_total": sum(1 for r in samples if r["ocr"]),
    }
    # 重复命中（同一 rule_id 在单次评审里出现 >1 次）
    dup = []
    for rec in raw["risk"]:
        body = (rec.get("review") or {}).get("body") or {}
        ids = [x["rule_id"] for x in body.get("risks") or []]
        for rid in set(ids):
            if ids.count(rid) > 1:
                dup.append({"file": rec["file"], "rule_id": rid, "count": ids.count(rid)})
    # bid-001 两套细则分项
    bid = next(r for r in samples if r["file"] == "bid-001.docx")
    a_items = {i["item_id"]: i["score"] for i in bid["review_a"]["body"]["scoring"]["items"]}
    b_items = {i["item_id"]: i["score"] for i in bid["review_b"]["body"]["scoring"]["items"]}
    # 资格性检查：每份文档三态计数是否 = 10
    qual_bad = []
    for rec in samples:
        for key in ("review_a", "review_b"):
            body = (rec.get(key) or {}).get("body") or {}
            ql = body.get("qualification") or {}
            if ql.get("total") != 10 or sum((ql.get("counts") or {}).values()) != 10:
                qual_bad.append({"file": rec["file"], "review": key, "total": ql.get("total"), "counts": ql.get("counts")})
    summary = {
        "generated_at": q.now(),
        "samples": len(samples),
        "parse_ok": parse,
        "fields": {"all": q.summarise(field_rows), "text": q.summarise(text_rows), "scan": q.summarise(scan_rows),
                   "extras": sum(len(rec["fields"]["extras"]) for rec in samples if rec.get("fields")),
                   "slice_bad": sum(1 for r in field_rows if not r["slice_ok"]),
                   "page_bad": sum(1 for r in field_rows if not r["page_ok"]),
                   "quote_missing_value": sum(1 for r in field_rows if not r["quote_has_value"])},
        "scoring": {"reviews": len(samples) * 2,
                    "problem_files_a": [(r["file"], r["scoring_problems_a"]) for r in samples if r.get("scoring_problems_a")],
                    "problem_files_b": [(r["file"], r["scoring_problems_b"]) for r in samples if r.get("scoring_problems_b")],
                    "bid001": {"a_total": bid["review_a"]["body"]["scoring"]["total"],
                               "b_total": bid["review_b"]["body"]["scoring"]["total"],
                               "a_items": a_items, "b_items": b_items,
                               "diff": {k: round(b_items[k] - a_items[k], 2) for k in a_items}}},
        "qualification": {"docs": len(samples), "bad_counts": qual_bad,
                          "states": {s: sum(1 for rec in samples for key in ("review_a",)
                                            for i in (rec[key]["body"]["qualification"]["items"]) if i["state"] == s)
                                     for s in ("provided", "insufficient", "missing")}},
        "risk": {},
        "duplicate_hits": dup,
    }
    for split in ("dev", "holdout", "all"):
        subset = [r for r in raw["risk"] if split == "all" or r["split"] == split]
        tp = fn = fp = 0
        for rec in subset:
            body = (rec.get("review") or {}).get("body") or {}
            det = {x["rule_id"] for x in body.get("risks") or []}
            st = {i["rule_id"]: i["state"] for i in (body.get("qualification") or {}).get("items") or []}
            dq = {rid for rid in rec["expected_qual"] if st.get(rid) not in (None, "provided")}
            tp += len(set(rec["expected_rules"]) & det) + len(dq)
            fn += len((set(rec["expected_rules"]) - det) | (set(rec["expected_qual"]) - dq))
            fp += len(det - set(rec["expected_rules"]))
        summary["risk"][split] = {"tp": tp, "fn": fn, "fp": fp,
                                  "recall": round(tp / (tp + fn), 4) if tp + fn else 1.0,
                                  "fp_rate": round(fp / (tp + fp), 4) if tp + fp else 0.0}
    q.jdump(q.RAW / "accuracy-summary.json", summary)

    # 独立分数明细 CSV
    with (q.RAW / "scores-by-doc.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "profile", "total", "total_full", "recomputed_total", "match",
                    "provided", "insufficient", "missing", "risk_count", "risk_rules"])
        for rec in samples:
            for key, profile in (("review_a", "profile-a"), ("review_b", "profile-b")):
                body = (rec.get(key) or {}).get("body") or {}
                if not body:
                    continue
                ql = body.get("qualification") or {}
                w.writerow([rec["file"], profile, (body.get("scoring") or {}).get("total"),
                            (body.get("scoring") or {}).get("total_full"),
                            (rec.get("recompute_" + profile[-1]) or {}).get("total"),
                            not rec.get("scoring_problems_" + profile[-1]),
                            (ql.get("counts") or {}).get("provided"), (ql.get("counts") or {}).get("insufficient"),
                            (ql.get("counts") or {}).get("missing"), len(body.get("risks") or []),
                            ";".join(x["rule_id"] for x in body.get("risks") or [])])
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
