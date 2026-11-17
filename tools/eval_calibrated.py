"""out-of-sample 评分回归：比对旧/新细则与固定专家分，锁定校准版判据。

用法：
  python tools/eval_calibrated.py            # 打印对比表
  python tools/eval_calibrated.py --strict   # 校准版必须 8/8 在 ±5 内，且旧版不能全中

数据：data/samples/out_of_sample/manifest.json
  - expert_scores 来自 1 名评审人在评分表上的独立盲评（先评、后跑引擎）；
  - 该文件不是 data/samples/expert_scores.json 的替代，不参与"专家验收"口径。

退出码：0 通过；1 不通过（校准版有偏差，或旧版也全中导致测试失去区分力）。
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

BASE = ROOT / "data" / "samples" / "out_of_sample"
MANIFEST = BASE / "manifest.json"
ITEM_IDS = ["P1", "T1", "T2", "T3", "T4", "T5", "B1", "B2", "B3"]
TOL = 5.0


def score_one(path: Path, profile: str) -> dict:
    doc = parse_file(path.read_bytes(), path.name, "oos", "oos")
    doc.fields = extract_fields(doc)
    return scoring.score_doc(doc, profile)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="out-of-sample 评分回归")
    ap.add_argument("--strict", action="store_true", help="有偏差时返回非 0")
    args = ap.parse_args(argv)

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    baseline = data.get("baseline_profile", "profile-a")
    target = data.get("score_profile", "profile-a-calibrated")

    print(f"样本集：{MANIFEST.relative_to(ROOT)}")
    print(f"对照：{baseline} → {target}｜容差 ±{TOL:.0f}\n")
    print(f"{'sample':<8}{'expert':>7}{'old':>7}{'diff':>6}{'calib':>7}{'diff':>6}  ok")
    print("-" * 64)

    base_hit = new_hit = 0
    base_abs = new_abs = 0.0
    n = 0
    problems: list[str] = []

    for item in data.get("items") or []:
        sid = item["sample_id"]
        path = BASE / item["file"]
        if not path.exists():
            problems.append(f"{sid}: 文件不存在 {item['file']}")
            continue
        expert_scores = item.get("expert_scores") or {}
        expert_total = float(item.get("expert_total", sum(expert_scores.get(k, 0) for k in ITEM_IDS)))
        if expert_scores and abs(sum(float(expert_scores.get(k, 0)) for k in ITEM_IDS) - expert_total) > 1e-6:
            problems.append(f"{sid}: expert_total 与逐项分合计不一致")

        b = score_one(path, baseline)
        t = score_one(path, target)
        for name, res in ((baseline, b), (target, t)):
            if "error" in res:
                problems.append(f"{sid}: {name} 评分失败 {res['error']}")

        bt, tt = float(b.get("total", 0)), float(t.get("total", 0))
        bd, td = bt - expert_total, tt - expert_total
        base_abs += abs(bd)
        new_abs += abs(td)
        n += 1
        if abs(bd) <= TOL:
            base_hit += 1
        if abs(td) <= TOL:
            new_hit += 1
        else:
            problems.append(f"{sid}: 校准版偏差 {td:+.0f}（专家 {expert_total:.0f} / 引擎 {tt:.0f}）")

        mark = "√" if abs(td) <= TOL else "×"
        print(f"{sid:<8}{expert_total:>7.0f}{bt:>7.0f}{bd:>+6.0f}{tt:>7.0f}{td:>+6.0f}  {mark}")

    if not n:
        print("没有可评样本")
        return 1

    print("-" * 70)
    print(f"±{TOL:.0f} 内：旧版 {base_hit}/{n}（{base_hit / n:.0%}）｜"
          f"校准版 {new_hit}/{n}（{new_hit / n:.0%}）")
    print(f"平均绝对偏差：旧版 {base_abs / n:.2f} 分｜校准版 {new_abs / n:.2f} 分")

    if base_hit == n:
        problems.append("旧版也全部命中，本组样本已失去区分力（判据或样本需复核）")

    if problems:
        for p in problems:
            print(f"[ERROR] {p}")
        print(f"\n结论：不通过（{len(problems)} 个问题）")
        return 1 if args.strict or problems else 0
    print("\n结论：通过（校准版全部落在容差内，旧版仍有偏差）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
