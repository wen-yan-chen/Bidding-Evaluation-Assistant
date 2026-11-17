"""把资格性标注终稿转成 `tools/eval_qualification.py` 可读的 JSON。"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
PKG = ROOT / "标注员包"
MAP = BASE / "样本映射.csv"
OUT = ROOT / "qualification_labels_25.json"
STATE_MAP = {"已提供": "provided", "缺失": "missing", "效力不足": "insufficient", "无法判断": None}


def main() -> int:
    ap = argparse.ArgumentParser(description="标注表终稿 -> qualification_labels_25.json")
    ap.add_argument("--input", default=str(BASE / "03-标注表_终稿.xlsx"))
    args = ap.parse_args()
    path = Path(args.input)
    if not path.exists():
        alt = PKG / "03-标注表_A.xlsx"
        print(f"未找到 {path}，改用 {alt}（仅用于试跑，正式请用终稿）")
        path = alt

    with MAP.open(encoding="utf-8-sig") as fh:
        sample_map = {row["sample_id"]: row["original_file"] for row in csv.DictReader(fh)}

    ws = load_workbook(path)["标注表"]
    by_file: dict[str, dict[str, str]] = {}
    unknown = 0
    for r in range(2, ws.max_row + 1):
        sample = ws.cell(row=r, column=1).value
        rule = ws.cell(row=r, column=2).value
        if not sample or not rule:
            continue
        raw = str(ws.cell(row=r, column=4).value or "").strip()
        if not raw:
            continue
        state = STATE_MAP.get(raw, None)
        if state is None:
            unknown += 1
            continue
        file = sample_map.get(str(sample))
        if not file:
            print(f"[WARN] 样本 {sample} 不在样本映射中")
            continue
        by_file.setdefault(file, {})[str(rule)] = state

    items = []
    for file in sorted(by_file):
        items.append({
            "file": file,
            "source": "人工标注员 A/B 终稿（非专家）",
            "expect": dict(sorted(by_file[file].items())),
        })
    payload = {
        "version": "v1",
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "note": "人工标注员 A/B 独立标注 + 第三人裁决的终稿；不是评标专家结论；无法判断项已排除。",
        "items": items,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rules = sum(len(i["expect"]) for i in items)
    print(f"written {OUT}")
    print(f"files={len(items)}/25 rules={rules}/250 unknown_skipped={unknown}")
    print("下一步：备份 data/samples/qualification_labels.json，把本文件复制过去后运行：")
    print("  python tools/eval_qualification.py --strict")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
