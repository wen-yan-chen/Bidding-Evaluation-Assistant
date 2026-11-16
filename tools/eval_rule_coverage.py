"""规则库覆盖评测：把 40 条规则逐条标成“自动/人工/未实现”，防止口径漂移。

口径（与 D9/MCP scan_risks 一致）：
- 自动 = detect=pattern 的 18 条 + detect=price 且已在 checks.CHECKS 实现的 9 条 = 27；
- 人工 = detect=manual 的 10 条；
- 未实现 = detect=price 但不在 checks.CHECKS 的 3 条（R25/R32/R33，需多家比价）；
- 27 + 10 + 3 = 40。

用法：
  python tools/eval_rule_coverage.py
  python tools/eval_rule_coverage.py --strict  # 条数/字段/依据状态不一致时退出 1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api import checks, rules  # noqa: E402

VALID_BASIS = {"verified", "pending", "na"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="规则覆盖矩阵")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)

    all_rules = list(rules.load_rules())
    pattern = [r for r in all_rules if r.detect == "pattern"]
    manual = [r for r in all_rules if r.detect == "manual"]
    price = [r for r in all_rules if r.detect == "price"]
    auto_price = [r for r in price if r.id in checks.CHECKS]
    unimplemented = [r for r in price if r.id not in checks.CHECKS]
    dead = [r.id for r in manual if r.id in checks.CHECKS]

    problems: list[str] = []
    for rule in all_rules:
        if not rule.condition.strip():
            problems.append(f"{rule.id}: 缺 condition")
        if not rule.level.strip():
            problems.append(f"{rule.id}: 缺风险等级")
        if rule.basis_status not in VALID_BASIS:
            problems.append(f"{rule.id}: basis_status={rule.basis_status} 不在 {VALID_BASIS}")
        if rule.basis_status == "verified" and not rule.basis:
            problems.append(f"{rule.id}: verified 但 basis 为空")

    print(f"{'规则':<5}{'检测方式':<10}{'类别':<10}{'等级':<4}{'依据':<10}标题")
    print("-" * 96)
    state = {}
    for rule in all_rules:
        if rule.detect == "pattern":
            label = "自动-关键词"
        elif rule.detect == "price" and rule.id in checks.CHECKS:
            label = "自动-计算"
        elif rule.detect == "price":
            label = "未实现"
        else:
            label = "人工核对"
        state[rule.id] = label
        print(f"{rule.id:<5}{label:<12}{rule.category:<10}{rule.level:<4}{rule.basis_status:<10}{rule.title}")
    print("-" * 96)
    print(f"合计 {len(all_rules)}：自动 {len(pattern)}+{len(auto_price)}={len(pattern) + len(auto_price)}；"
          f"人工 {len(manual)}；未实现 {len(unimplemented)}")
    print(f"自动明细：pattern={len(pattern)} price={len(auto_price)}；"
          f"未实现：{', '.join(r.id for r in unimplemented) or '-'}")
    if dead:
        print(f"[WARN] 这些规则标 manual 但 CHECKS 里有实现（不会自动调用）：{', '.join(dead)}")

    expected = {"total": 40, "auto": 27, "pattern": 18, "auto_price": 9, "manual": 10, "unimplemented": 3}
    actual = {"total": len(all_rules), "auto": len(pattern) + len(auto_price), "pattern": len(pattern),
              "auto_price": len(auto_price), "manual": len(manual), "unimplemented": len(unimplemented)}
    ok = actual == expected and not problems
    if not ok:
        for key, want in expected.items():
            if actual[key] != want:
                print(f"[FAIL] {key}: 实际 {actual[key]}，期望 {want}")
        for problem in problems:
            print(f"[FAIL] {problem}")
    print(f"结论：{'通过（40=27+10+3）' if ok else '未通过'}")
    return 0 if (ok or not args.strict) else 1


if __name__ == "__main__":
    raise SystemExit(main())
