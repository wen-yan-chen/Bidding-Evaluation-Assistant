"""按 manifest 复算解析指标：解析成功率、关键字段准确率，并按"文本层 / 扫描件"分列。

口径（写死，评审可复算）：
- 解析成功率 = `parse_status != failed` 的样本数 / 该组样本数
- 字段准确率 = 正确抽到的字段数 / 该组应抽字段数（标准答案只列该样本真实存在的字段）
- 多抽 = 标准答案里没有、却被抽出来的字段（边界样本多抽即"编造"，必须为 0）

用法：
  python tools/eval_parse.py            # 只打印
  python tools/eval_parse.py --strict   # 任一指标低于 90% 或出现多抽 → 退出码 1
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.extract import extract_fields  # noqa: E402
from api.parsers.dispatch import parse_file  # noqa: E402

SAMPLES = ROOT / "data" / "samples"
NOISE = re.compile(r"[\s\u3000,，]")
TAIL = re.compile(r"（大写[:：].*?）?$")


def norm(text: str) -> str:
    """比较用的归一化：去空白与逗号、去掉"（大写：…）"尾巴、统一小写。"""
    if text is None:
        return ""
    text = str(text).strip()
    text = TAIL.sub("", text)
    text = text.replace("人民币", "").replace("RMB", "")
    text = NOISE.sub("", text)
    return text.lower()


def matches(expected: str, actual: str) -> bool:
    a, e = norm(actual), norm(expected)
    if not a:
        return False
    return a == e or e in a or a in e


def group_of(item: dict) -> str:
    return "扫描件" if item.get("ocr") else "文本层"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="复算解析指标")
    ap.add_argument("--samples", default=str(SAMPLES))
    ap.add_argument("--strict", action="store_true", help="任一指标 < 90% 或有编造字段则返回非 0")
    args = ap.parse_args(argv)

    base = Path(args.samples)
    manifest_path = base / "manifest.json"
    if not manifest_path.exists():
        print(f"缺少标准答案：{manifest_path}（先跑 python tools/make_samples.py）")
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest.get("items") or []

    groups: dict[str, dict[str, int]] = {}
    total = {"items": 0, "parsed": 0, "expect": 0, "hit": 0, "extra": 0}

    print(f"{'文件':<14}{'类型':<8}{'状态':<10}{'页':>3}{'OCR':>4}{'字段':>5}{'应抽':>5}{'命中':>5}  说明")
    print("-" * 104)

    for item in items:
        path = base / item["file"]
        blob = path.read_bytes()
        doc = parse_file(blob, path.name, "eval", "eval")
        doc.fields = extract_fields(doc)
        values = {f.name: f.value for f in doc.fields}
        ocr_pages = len(doc.meta.get("ocr_pages") or [])
        group = group_of(item)
        stats = groups.setdefault(group, {"items": 0, "parsed": 0, "expect": 0, "hit": 0, "extra": 0})

        parsed_ok = doc.parse_status != "failed"
        expect = item.get("expect") or {}
        hits, misses = [], []
        for key, want in expect.items():
            if matches(want, values.get(key, "")):
                hits.append(key)
            else:
                misses.append(f"{key}={values.get(key, '∅')}")
        extras = [k for k in values if k not in expect]

        for bucket in (stats, total):
            bucket["items"] += 1
            bucket["parsed"] += 1 if parsed_ok else 0
            bucket["expect"] += len(expect)
            bucket["hit"] += len(hits)
            bucket["extra"] += len(extras)

        note = "；".join(misses) if misses else ""
        if extras:
            note += f"（多抽：{'、'.join(extras)}）"
        if item.get("boundary"):
            note += f" [{item['boundary']}]"

        print(
            f"{item['file']:<14}{group:<8}{doc.parse_status:<10}{len(doc.pages):>3}"
            f"{ocr_pages:>4}{len(doc.fields):>5}{len(expect):>5}{len(hits):>5}  {note}"
        )

    def line(name: str, bucket: dict[str, int]) -> str:
        if not bucket["items"]:
            return f"{name}：无样本"
        parse_rate = bucket["parsed"] / bucket["items"]
        field_rate = bucket["hit"] / bucket["expect"] if bucket["expect"] else 0.0
        return (
            f"{name}：解析成功率 {bucket['parsed']}/{bucket['items']} = {parse_rate:.1%}"
            f"｜字段准确率 {bucket['hit']}/{bucket['expect']} = {field_rate:.1%}"
            f"｜多抽 {bucket['extra']}"
        )

    print("-" * 104)
    for group_name in ("文本层", "扫描件"):
        print(line(group_name, groups.get(group_name, {"items": 0, "parsed": 0, "expect": 0, "hit": 0, "extra": 0})))
    print(line("合计", total))

    parse_rate = total["parsed"] / total["items"] if total["items"] else 0.0
    field_rate = total["hit"] / total["expect"] if total["expect"] else 0.0
    ok = parse_rate >= 0.9 and field_rate >= 0.9 and total["extra"] == 0
    print(f"结论：{'通过' if ok else '未达标'}")
    return 0 if (ok or not args.strict) else 1


if __name__ == "__main__":
    sys.exit(main())
