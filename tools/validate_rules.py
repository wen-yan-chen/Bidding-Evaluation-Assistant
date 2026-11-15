"""规则库校验（D4 的验收闸门）。

检查项：
1. 条数 ≥ 40，且四类各 10 条；
2. id 唯一、连续（R01–R40）、格式合法；
3. `detect=pattern` 的规则必须有 patterns；`detect=price/manual` 不参与自动扫描但要标明；
4. `basis_status` 只能是 verified / pending / na；verified 必须有 basis，pending/na 不得有 basis；
5. verified 的依据必须带书名号与"条"（防止写成"某某规定"这种无法核对的表述）；
6. 规则库指纹与知识库导出的指纹一致（`knowledge/manifest.json`）。

用法：
  python tools/validate_rules.py
  python tools/validate_rules.py --skip-kb   # 知识库还没导出时跳过第 6 项
退出码：0 通过；1 有问题。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api import rules as rules_api  # noqa: E402

CATEGORIES = {"资质门槛": 10, "废标条款": 10, "围标串标": 10, "报价异常": 10}
ID_RE = re.compile(r"^R\d{2}$")
BASIS_RE = re.compile(r"《.+?》\s*第[一二三四五六七八九十百零〇0-9]+条")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="校验规则库")
    ap.add_argument("--skip-kb", action="store_true", help="跳过知识库指纹一致性检查")
    args = ap.parse_args(argv)

    problems: list[str] = []
    warnings: list[str] = []

    try:
        loaded = rules_api.load_rules()
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] 规则库加载失败：{exc}")
        return 1

    # 1. 条数与分类
    if len(loaded) < 40:
        problems.append(f"规则条数不足：{len(loaded)} < 40")
    counts: dict[str, int] = {}
    for rule in loaded:
        counts[rule.category] = counts.get(rule.category, 0) + 1
    for category, expected in CATEGORIES.items():
        actual = counts.get(category, 0)
        if actual != expected:
            problems.append(f"「{category}」应有 {expected} 条，实际 {actual} 条")

    # 2. id
    ids = [r.id for r in loaded]
    if len(ids) != len(set(ids)):
        duplicated = {i for i in ids if ids.count(i) > 1}
        problems.append(f"id 重复：{sorted(duplicated)}")
    for rule in loaded:
        if not ID_RE.match(rule.id):
            problems.append(f"{rule.id}: id 格式不对")
    expected_ids = {f"R{n:02d}" for n in range(1, len(loaded) + 1)}
    if set(ids) != expected_ids:
        missing = sorted(expected_ids - set(ids))
        extra = sorted(set(ids) - expected_ids)
        problems.append(f"id 不连续：缺 {missing}，多 {extra}")

    # 3. detect 与 patterns
    for rule in loaded:
        if rule.detect not in ("pattern", "manual", "price"):
            problems.append(f"{rule.id}: detect 非法值 {rule.detect}")
        if rule.detect == "pattern" and not rule.patterns:
            problems.append(f"{rule.id}: detect=pattern 但没有 patterns")

    # 4. 依据三态
    for rule in loaded:
        if rule.basis_status not in ("verified", "pending", "na"):
            problems.append(f"{rule.id}: basis_status 非法值 {rule.basis_status}")
        if rule.basis_status == "verified":
            if not rule.basis:
                problems.append(f"{rule.id}: verified 但 basis 为空")
            elif not BASIS_RE.search(rule.basis):
                warnings.append(f"{rule.id}: 依据缺书名号或条号，核对格式：{rule.basis[:40]}")
        elif rule.basis:
            problems.append(f"{rule.id}: {rule.basis_status} 状态下不应填 basis（避免'假装有依据'）")

    # 6. 与知识库导出的一致性
    kb_manifest = ROOT / "knowledge" / "manifest.json"
    if not args.skip_kb:
        if not kb_manifest.exists():
            problems.append("缺少 knowledge/manifest.json（先跑 python tools/export_kb.py）")
        else:
            kb = json.loads(kb_manifest.read_text(encoding="utf-8"))
            if kb.get("digest") != rules_api.rules_digest():
                problems.append(
                    f"知识库与规则库指纹不一致：kb={kb.get('digest')} yaml={rules_api.rules_digest()}"
                    "（重新导出 export_kb.py）"
                )

    # 输出
    st = rules_api.stats()
    print(f"规则库：{st['total']} 条 ｜ 指纹 {st['digest']}")
    print(
        "类别分布："
        + " ｜ ".join(f"{k} {v}" for k, v in sorted(st["by_category"].items()))
    )
    print(
        "等级分布："
        + " ｜ ".join(f"{k} {v}" for k, v in sorted(st["by_level"].items()))
    )
    print(
        "依据状态："
        + " ｜ ".join(f"{k} {v}" for k, v in sorted(st["by_basis_status"].items()))
    )
    print(
        "检测方式："
        + " ｜ ".join(f"{k} {v}" for k, v in sorted(st["by_detect"].items()))
    )
    print()

    for warning in warnings:
        print(f"[WARN ] {warning}")
    for problem in problems:
        print(f"[ERROR] {problem}")

    if problems:
        print(f"\n结论：不通过（{len(problems)} 个问题，{len(warnings)} 个提示）")
        return 1
    print(f"结论：通过（{len(warnings)} 个提示）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
