"""比较两位标注员的资格性标注，输出一致率、kappa 与分歧清单。"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
PKG = ROOT / "标注员包"
OUT_MD = BASE / "一致性报告.md"
OUT_CSV = BASE / "分歧清单.csv"
STATE_MAP = {"已提供": "provided", "缺失": "missing", "效力不足": "insufficient", "无法判断": "unknown"}


def read(path: Path) -> dict[tuple[str, str], dict]:
    ws = load_workbook(path)["标注表"]
    data = {}
    for r in range(2, ws.max_row + 1):
        sample = ws.cell(row=r, column=1).value
        rule = ws.cell(row=r, column=2).value
        if not sample or not rule:
            continue
        data[(str(sample), str(rule))] = {
            "material": ws.cell(row=r, column=3).value or "",
            "state": STATE_MAP.get(str(ws.cell(row=r, column=4).value or "").strip(), "unknown"),
            "page": ws.cell(row=r, column=5).value or "",
            "note": ws.cell(row=r, column=6).value or "",
        }
    return data


def kappa(pairs: list[tuple[str, str]]) -> float:
    if not pairs:
        return 0.0
    n = len(pairs)
    po = sum(1 for a, b in pairs if a == b) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum((ca[k] / n) * (cb[k] / n) for k in set(ca) | set(cb))
    return (po - pe) / (1 - pe) if pe < 1 else 0.0


def main() -> int:
    a = read(PKG / "03-标注表_A.xlsx")
    b = read(PKG / "03-标注表_B.xlsx")
    keys = sorted(set(a) | set(b))
    pairs = []
    disagreements = []
    for key in keys:
        sa = a.get(key, {}).get("state", "unknown")
        sb = b.get(key, {}).get("state", "unknown")
        if sa == "unknown" and sb == "unknown":
            continue
        pairs.append((sa, sb))
        if sa != sb:
            disagreements.append({
                "sample_id": key[0], "rule": key[1], "material": a.get(key, {}).get("material") or b.get(key, {}).get("material", ""),
                "A": sa, "B": sb,
                "A_page": a.get(key, {}).get("page", ""), "B_page": b.get(key, {}).get("page", ""),
                "A_note": a.get(key, {}).get("note", ""), "B_note": b.get(key, {}).get("note", ""),
            })

    total = len(pairs)
    agree = sum(1 for x, y in pairs if x == y)
    rate = agree / total if total else 0.0
    k = kappa(pairs)

    # 逐规则
    by_rule = {}
    for key in keys:
        sa = a.get(key, {}).get("state", "unknown")
        sb = b.get(key, {}).get("state", "unknown")
        if sa == "unknown" and sb == "unknown":
            continue
        row = by_rule.setdefault(key[1], [0, 0])
        row[1] += 1
        if sa == sb:
            row[0] += 1

    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["sample_id", "rule", "material", "A", "B", "A_page", "B_page", "A_note", "B_note"])
        w.writeheader()
        w.writerows(disagreements)

    lines = [
        "# 资格性标注一致性报告",
        "",
        f"- 可比条目：**{total}**（两位都标为“无法判断”的条目已排除）",
        f"- 一致：**{agree}/{total} = {rate:.1%}**",
        f"- Cohen's kappa：**{k:.3f}**",
        f"- 分歧：**{len(disagreements)} 条**（见 `分歧清单.csv`，需第三人对原文裁决）",
        "",
        "| 规则 | 一致/可比 | 一致率 |",
        "| --- | ---: | ---: |",
    ]
    for rule in sorted(by_rule):
        hit, n = by_rule[rule]
        lines.append(f"| {rule} | {hit}/{n} | {hit / n:.1%} |")
    lines += [
        "",
        "## 怎么用",
        "1. 分歧条目逐条看原文，由第三人或你裁决；",
        "2. 把终稿填到 `03-标注表_终稿.xlsx`（可复制 A 表后修改）；",
        "3. 运行 `06-转正式标签.py` 生成 `qualification_labels_25.json`；",
        "4. 备份并替换 `data/samples/qualification_labels.json` 后，运行 `python tools/eval_qualification.py --strict`。",
        "",
        "> 注意：一致率是两位人工标注员之间的一致性；不是与引擎的一致率，也不是专家结论。",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"pairs={total} agree={agree} rate={rate:.1%} kappa={k:.3f} disagreements={len(disagreements)}")
    print(f"written {OUT_MD} / {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
