"""准确性主测试：上传 25 份解析样本 + 15 份风险样本，逐字段/逐项/逐规则独立核对。

输出：
  raw/accuracy-raw.json        全量原始记录（上传、评审、字段、资格性、风险）
  raw/fields.csv               146 个期望字段逐项
  raw/reviews.csv              每份文档 × profile 的 9 项分数与总分
  raw/qualification.csv        每份文档 R01–R10 三态
  raw/risks.csv                风险样本期望/实际命中
  raw/accuracy-summary.json    汇总指标
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as q

SAMPLES = q.ROOT / "data" / "samples"
RISK = SAMPLES / "risk"


def main() -> int:
    q.ensure_dirs()
    manifest = q.jload(SAMPLES / "manifest.json")
    risk_manifest = q.jload(RISK / "manifest.json")
    raw: dict = {"started_at": q.now(), "base": q.BASE, "samples": [], "risk": []}

    # ---------- A. 25 份解析样本 ----------
    doc_by_file: dict[str, str] = {}
    for item in manifest["items"]:
        path = SAMPLES / item["file"]
        up = q.upload(path)
        rec = {"file": item["file"], "expect": item.get("expect") or {}, "boundary": item.get("boundary"),
               "kind": item.get("kind"), "ocr": bool(item.get("ocr")), "upload": up,
               "doc": None, "review_a": None, "review_b": None, "fields": None,
               "recompute_a": None, "recompute_b": None, "scoring_problems_a": [], "scoring_problems_b": []}
        if up["status"] != 200:
            raw["samples"].append(rec)
            continue
        doc_id = up["body"].get("doc_id")
        doc_by_file[item["file"]] = doc_id
        doc = q.get_json(f"/api/doc/{doc_id}")
        rec["doc"] = {"doc_id": doc_id, "parse_status": doc.get("parse_status"), "degraded": doc.get("degraded"),
                      "page_count": len(doc.get("pages") or []), "char_count": len(doc.get("full_text") or ""),
                      "clause_count": len(doc.get("clauses") or []), "fields": doc.get("fields")}
        rec["fields"] = q.check_fields(doc, item.get("expect") or {})
        for profile in ("profile-a", "profile-b"):
            rv = q.review(doc_id, profile)
            rec["review_" + profile[-1]] = rv
            if rv["status"] == 200:
                rec["recompute_" + profile[-1]] = q.recompute_scoring(doc, profile)
                rec["scoring_problems_" + profile[-1]] = q.compare_scoring(rv["body"], rec["recompute_" + profile[-1]])
        raw["samples"].append(rec)
        print(f"SAMPLE {item['file']:<14} parse={doc.get('parse_status'):<8} fields={rec['fields']['hit']}/{rec['fields']['expect']} "
              f"extras={rec['fields']['extras']} A={((rec['review_a'] or {}).get('body') or {}).get('scoring', {}).get('total')} "
              f"B={((rec['review_b'] or {}).get('body') or {}).get('scoring', {}).get('total')}")

    # ---------- B. 15 份风险样本 + 5 份干净对照 ----------
    for item in risk_manifest["items"]:
        path = SAMPLES / item["file"]
        if item["file"].startswith("bid-"):
            doc_id = doc_by_file.get(Path(item["file"]).name)
            up = {"status": 200, "ms": 0.0, "body": {"doc_id": doc_id}, "file": item["file"], "reused": True}
        else:
            up = q.upload(path)
        rec = {"file": item["file"], "split": item.get("split"), "clean": bool(item.get("clean")),
               "expected_rules": item.get("expect_rules") or [], "expected_qual": item.get("expect_qualification") or [],
               "note": item.get("note", ""), "upload": up, "doc_id": None, "review": None, "fields": None}
        if up["status"] != 200:
            raw["risk"].append(rec)
            continue
        doc_id = (up["body"] or {}).get("doc_id")
        rec["doc_id"] = doc_id
        doc = q.get_json(f"/api/doc/{doc_id}")
        rec["fields"] = {f["name"]: f["value"] for f in doc.get("fields") or []}
        rv = q.review(doc_id, "profile-a")
        rec["review"] = rv
        raw["risk"].append(rec)
        hits = [x["rule_id"] for x in ((rv.get("body") or {}).get("risks") or [])] if rv["status"] == 200 else []
        print(f"RISK {item['file']:<20} split={item.get('split'):<7} hits={','.join(hits) or '-'} "
              f"expect={','.join(rec['expected_rules']) or '-'}")

    q.jdump(q.RAW / "accuracy-raw.json", raw)

    # ---------- 汇总 CSV ----------
    with (q.RAW / "fields.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "field", "expected", "actual", "hit", "slice_ok", "page_ok", "quote_has_value", "note"])
        for rec in raw["samples"]:
            if not rec.get("fields"):
                continue
            for row in rec["fields"]["rows"]:
                w.writerow([rec["file"], row["name"], row["expected"], row["actual"], row["hit"], row["slice_ok"],
                            row["page_ok"], row["quote_has_value"], row["note"]])

    with (q.RAW / "reviews.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "profile", "review_id", "total", "recomputed_total", "match", "item_id", "name", "weight",
                    "score", "recomputed_score", "tier", "reason"])
        for rec in raw["samples"]:
            for profile in ("profile-a", "profile-b"):
                rv = rec.get("review_" + profile[-1]) or {}
                body = rv.get("body") or {}
                rc = rec.get("recompute_" + profile[-1]) or {}
                for item in (body.get("scoring") or {}).get("items") or []:
                    exp = next((x for x in rc.get("items", []) if x["item_id"] == item["item_id"]), {})
                    w.writerow([rec["file"], profile, body.get("review_id"), (body.get("scoring") or {}).get("total"),
                                rc.get("total"), not rec.get("scoring_problems_" + profile[-1]), item["item_id"],
                                item["name"], item["weight"], item["score"], exp.get("score"), exp.get("tier"),
                                item.get("reason")])

    with (q.RAW / "qualification.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "profile", "review_id", "counts_provided", "counts_insufficient", "counts_missing",
                    "total", "rule_id", "state", "page", "quote", "title"])
        recs = [(r["file"], r) for r in raw["samples"]] + [(r["file"], r) for r in raw["risk"]]
        for name, rec in recs:
            rvs = []
            if rec.get("review_a"):
                rvs.append(("profile-a", rec["review_a"]))
            if rec.get("review_b"):
                rvs.append(("profile-b", rec["review_b"]))
            if rec.get("review"):
                rvs.append(("profile-a", rec["review"]))
            for profile, rv in rvs:
                body = rv.get("body") or {}
                qual = body.get("qualification") or {}
                for it in qual.get("items") or []:
                    w.writerow([name, profile, body.get("review_id"), (qual.get("counts") or {}).get("provided"),
                                (qual.get("counts") or {}).get("insufficient"), (qual.get("counts") or {}).get("missing"),
                                qual.get("total"), it["rule_id"], it["state"], it.get("page"), it.get("quote"), it.get("title")])

    with (q.RAW / "risks.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "split", "clean", "expected_rules", "expected_qual", "detected_rules", "detected_qual",
                    "tp", "fn", "fp", "review_id", "total", "hits_detail"])
        for rec in raw["risk"]:
            body = (rec.get("review") or {}).get("body") or {}
            det = [x["rule_id"] for x in body.get("risks") or []]
            qual_states = {i["rule_id"]: i["state"] for i in (body.get("qualification") or {}).get("items") or []}
            det_qual = [rid for rid in rec["expected_qual"] if qual_states.get(rid) not in (None, "provided")]
            tp = len(set(rec["expected_rules"]) & set(det)) + len(det_qual)
            fn = sorted((set(rec["expected_rules"]) - set(det)) | (set(rec["expected_qual"]) - set(det_qual)))
            fp = sorted(set(det) - set(rec["expected_rules"]))
            w.writerow([rec["file"], rec["split"], rec["clean"], ";".join(rec["expected_rules"]),
                        ";".join(rec["expected_qual"]), ";".join(det), ";".join(det_qual), tp, ";".join(fn),
                        ";".join(fp), body.get("review_id"), (body.get("scoring") or {}).get("total"),
                        json.dumps([{"rule_id": x["rule_id"], "page": x["page"], "quote": x["quote"]} for x in body.get("risks") or []],
                                   ensure_ascii=False)])

    # ---------- 汇总 ----------
    field_rows = [row for rec in raw["samples"] if rec.get("fields") for row in rec["fields"]["rows"]]
    text_rows = [row for rec in raw["samples"] if rec.get("fields") and not rec["ocr"] for row in rec["fields"]["rows"]]
    scan_rows = [row for rec in raw["samples"] if rec.get("fields") and rec["ocr"] for row in rec["fields"]["rows"]]
    extras = sum(len(rec["fields"]["extras"]) for rec in raw["samples"] if rec.get("fields"))
    parse_ok = {True: sum(1 for r in raw["samples"] if (r.get("doc") or {}).get("parse_status") != "failed" and not r["ocr"]),
                False: sum(1 for r in raw["samples"] if (r.get("doc") or {}).get("parse_status") != "failed" and r["ocr"])}
    scoring_problems = {
        "a": [(r["file"], r["scoring_problems_a"]) for r in raw["samples"] if r.get("scoring_problems_a")],
        "b": [(r["file"], r["scoring_problems_b"]) for r in raw["samples"] if r.get("scoring_problems_b")],
    }
    risk_summary = {}
    for split in ("dev", "holdout", "all"):
        subset = [r for r in raw["risk"] if split == "all" or r["split"] == split]
        tp = fn = fp = 0
        for rec in subset:
            body = (rec.get("review") or {}).get("body") or {}
            det = {x["rule_id"] for x in body.get("risks") or []}
            qual_states = {i["rule_id"]: i["state"] for i in (body.get("qualification") or {}).get("items") or []}
            det_qual = {rid for rid in rec["expected_qual"] if qual_states.get(rid) not in (None, "provided")}
            tp += len(set(rec["expected_rules"]) & det) + len(det_qual)
            fn += len((set(rec["expected_rules"]) - det) | (set(rec["expected_qual"]) - det_qual))
            fp += len(det - set(rec["expected_rules"]))
        risk_summary[split] = {"tp": tp, "fn": fn, "fp": fp,
                               "recall": round(tp / (tp + fn), 4) if tp + fn else 1.0,
                               "fp_rate": round(fp / (tp + fp), 4) if tp + fp else 0.0}
    summary = {
        "generated_at": q.now(),
        "samples": len(raw["samples"]),
        "parse_ok": {"text": parse_ok[False], "text_total": sum(1 for r in raw["samples"] if not r["ocr"]),
                     "scan": parse_ok[True], "scan_total": sum(1 for r in raw["samples"] if r["ocr"])},
        "fields": {"all": q.summarise(field_rows), "text": q.summarise(text_rows), "scan": q.summarise(scan_rows),
                   "extras": extras, "slice_bad": sum(1 for r in field_rows if not r["slice_ok"]),
                   "page_bad": sum(1 for r in field_rows if not r["page_ok"]),
                   "quote_missing_value": sum(1 for r in field_rows if not r["quote_has_value"])},
        "scoring": {"profiles": 2, "reviews": len(raw["samples"]) * 2,
                    "problem_files": scoring_problems,
                    "a_totals": {r["file"]: (r.get("review_a") or {}).get("body", {}).get("scoring", {}).get("total") for r in raw["samples"]},
                    "b_totals": {r["file"]: (r.get("review_b") or {}).get("body", {}).get("scoring", {}).get("total") for r in raw["samples"]}},
        "risk": risk_summary,
        "risk_rows": len(raw["risk"]),
    }
    q.jdump(q.RAW / "accuracy-summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
