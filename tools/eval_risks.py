"""D6 评测：风险检出率 / 误报率（按 dev / holdout 分档）。

口径（写死，可复算）：
- 检出率 = TP / (TP + FN)，TP = 期望规则中被检出的条数；
- 误报率 = FP / (TP + FP)，FP = **扫描命中的规则中不在期望列表里的条数**；
  只统计 `scan_risks` 的命中，不把资格性核验里"材料确实缺失"的判断算作误报
  （合成样本本来就没有那些材料，那是真实发现，不是误报）；
- 期望规则来自 `data/samples/risk/manifest.json`（人工标注），资格性风险按 `state != provided` 判定。

用法：
  python tools/eval_risks.py
  python tools/eval_risks.py --strict     # 检出率 <85% 或误报率 >15% 退出码 1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api import rules  # noqa: E402
from api.extract import extract_fields  # noqa: E402
from api.parsers.dispatch import parse_file  # noqa: E402
from api.review import qualification  # noqa: E402

SAMPLES = ROOT / "data" / "samples"
MANIFEST = SAMPLES / "risk" / "manifest.json"


def run_item(item: dict, context: dict) -> dict:
    path = SAMPLES / item["file"]
    doc = parse_file(path.read_bytes(), path.name, "eval", "eval")
    doc.fields = extract_fields(doc)
    hits = rules.scan_doc(doc, context=context)
    detected_scan = {h["rule_id"] for h in hits}
    qual = qualification.check(doc)
    qual_state = {i["rule_id"]: i["state"] for i in qual["items"]}

    expected_rules = set(item.get("expect_rules") or [])
    expected_qual = set(item.get("expect_qualification") or [])

    tp_scan = expected_rules & detected_scan
    tp_qual = {rid for rid in expected_qual if qual_state.get(rid) != "provided"}
    fn = (expected_rules - detected_scan) | (expected_qual - tp_qual)
    fp = detected_scan - expected_rules

    return {
        "file": item["file"],
        "clean": bool(item.get("clean")),
        "split": item.get("split", "dev"),
        "note": item.get("note", ""),
        "expected": sorted(expected_rules | expected_qual),
        "detected_scan": sorted(detected_scan),
        "detected_qual": sorted(rid for rid in expected_qual if qual_state.get(rid) != "provided"),
        "tp": len(tp_scan) + len(tp_qual),
        "fn": sorted(fn),
        "fp": sorted(fp),
        "hits": [
            {
                "rule_id": h["rule_id"],
                "page": h["page"],
                "quote": h["quote"],
                "detect": h.get("detect"),
                "reason": h.get("reason", ""),
            }
            for h in hits
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="风险检出率 / 误报率评测")
    ap.add_argument("--strict", action="store_true", help="低于阈值返回非 0")
    args = ap.parse_args(argv)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    context = manifest.get("context") or {}
    items = manifest.get("items") or []

    print(f"{'文件':<22}{'类型':<7}{'分档':<9}{'期望':<18}{'命中':<22}{'TP':>3}{'FN':>6}{'FP':>6}")
    print("-" * 108)
    results = [run_item(item, context) for item in items]

    for r in results:
        print(
            f"{r['file']:<22}{'clean' if r['clean'] else 'risk':<7}{r['split']:<9}"
            f"{','.join(r['expected']) or '-':<18}{','.join(r['detected_scan']) or '-':<22}"
            f"{r['tp']:>3}{len(r['fn']):>6}{len(r['fp']):>6}"
        )
        if r["fn"]:
            print(f"{'':<22}  ↳ 漏检：{', '.join(r['fn'])}")
        if r["fp"]:
            print(f"{'':<22}  ↳ 误报：{', '.join(r['fp'])}")

    def summarize(name: str, subset: list[dict]) -> tuple[float, float, int, int, int]:
        tp = sum(r["tp"] for r in subset)
        fn = sum(len(r["fn"]) for r in subset)
        fp = sum(len(r["fp"]) for r in subset)
        recall = tp / (tp + fn) if (tp + fn) else 1.0
        fp_rate = fp / (tp + fp) if (tp + fp) else 0.0
        print(
            f"{name}：TP={tp}　FN={fn}　FP={fp}　检出率={recall:.1%}（要求 ≥85%）　"
            f"误报率={fp_rate:.1%}（要求 ≤15%）"
        )
        return recall, fp_rate, tp, fn, fp

    print("-" * 108)
    recall_all, fp_all, tp_all, fn_all, fp_all_n = summarize("合计", results)
    dev = [r for r in results if r["split"] == "dev"]
    holdout = [r for r in results if r["split"] == "holdout"]
    if dev:
        summarize("dev", dev)
    if holdout:
        summarize("holdout", holdout)

    print("\n按规则看（检出 / 期望）：")
    per_rule: dict[str, list[int]] = {}
    for r in results:
        for rid in r["expected"]:
            stat = per_rule.setdefault(rid, [0, 0])
            stat[1] += 1
            if rid in r["detected_scan"] or rid in r["detected_qual"]:
                stat[0] += 1
    for rid in sorted(per_rule):
        hit, total = per_rule[rid]
        mark = "✓" if hit == total else "✗"
        print(f"  {mark} {rid}: {hit}/{total}")

    ok = recall_all >= 0.85 and fp_all <= 0.15
    print(f"\n结论：{'通过' if ok else '未达标'}")
    return 0 if (ok or not args.strict) else 1


if __name__ == "__main__":
    sys.exit(main())
