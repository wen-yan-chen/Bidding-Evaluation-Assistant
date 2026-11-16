"""评分 vs 专家标注评测（不含 AI 代评；AI 双盲只能作参考）。

标注文件：`data/samples/expert_scores.json`
schema 见文件内 `schema` 字段；没有人工专家标注时，脚本会明确输出“0 条，
无法计算 ±5 比例”，不会把 AI 双盲或引擎自评当专家。

用法：
  python tools/eval_scoring.py
  python tools/eval_scoring.py --strict   # 要求 ≥10 条标注且 ±5 内 ≥85%
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api import scoring  # noqa: E402
from api.extract import extract_fields  # noqa: E402
from api.parsers.dispatch import parse_file  # noqa: E402

SAMPLES = ROOT / "data" / "samples"
LABELS = SAMPLES / "expert_scores.json"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="评分与专家标注偏差")
    ap.add_argument("--strict", action="store_true", help="<10 条标注或 ±5 内 <85% 时返回非 0")
    args = ap.parse_args(argv)

    data = json.loads(LABELS.read_text(encoding="utf-8"))
    items = data.get("items") or []
    if not items:
        print("专家标注：0 条")
        print("无法计算评分偏差 ±5 比例；AI 双盲/引擎自评不能替代人类专家。")
        print("结论：未达成（缺专家真值）")
        return 1 if args.strict else 0

    rows: list[dict] = []
    for item in items:
        path = SAMPLES / item["file"]
        if not path.exists():
            print(f"[SKIP] {item['file']}: 文件不存在")
            continue
        profile = item.get("profile", "profile-a")
        doc = parse_file(path.read_bytes(), path.name, "eval", "eval")
        doc.fields = extract_fields(doc)
        result = scoring.score_doc(doc, profile)
        if "error" in result:
            print(f"[SKIP] {item['file']}: {result['error']}")
            continue
        total = float(result["total"])
        expert_total = float(item["total"])
        diff = total - expert_total
        row = {
            "file": item["file"], "profile": profile, "reviewer": item.get("reviewer", "unknown"),
            "engine_total": total, "expert_total": expert_total, "diff": round(diff, 2),
            "within_5": abs(diff) <= 5.0, "items": {},
        }
        engine_items = {i["item_id"]: float(i["score"]) for i in result["items"]}
        for item_id, expert_score in (item.get("scores") or {}).items():
            row["items"][item_id] = {"engine": engine_items.get(item_id), "expert": expert_score,
                                     "diff": round(float(engine_items.get(item_id, 0)) - float(expert_score), 2)}
        rows.append(row)
        print(f"{item['file']:<20} {profile:<10} 引擎 {total:6.2f}  专家 {expert_total:6.2f}  "
              f"差值 {diff:+6.2f}  {'✓' if row['within_5'] else '✗'}")

    if not rows:
        print("专家标注：0 条有效记录")
        return 1 if args.strict else 0
    within = sum(1 for r in rows if r["within_5"])
    rate = within / len(rows)
    mean_abs = sum(abs(r["diff"]) for r in rows) / len(rows)
    max_abs = max(abs(r["diff"]) for r in rows)
    print("-" * 72)
    print(f"专家标注：{len(rows)} 条｜±5 内 {within}/{len(rows)} = {rate:.1%}｜平均绝对偏差 {mean_abs:.2f}｜最大 {max_abs:.2f}")
    ok = len(rows) >= 10 and rate >= 0.85
    print(f"结论：{'通过' if ok else '未达标（需要 ≥10 条专家标注且 ±5 内 ≥85%）'}")
    return 0 if (ok or not args.strict) else 1


if __name__ == "__main__":
    raise SystemExit(main())
