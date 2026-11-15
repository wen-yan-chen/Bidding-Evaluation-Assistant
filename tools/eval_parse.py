"""按 manifest 复算 D2 的两项验收指标：解析成功率、关键字段准确率。

口径（写死，评审可复算）：
- 解析成功率 = `parse_status != failed` 的样本数 / 样本总数
- 字段准确率 = 正确抽到的字段数 / 应抽字段总数（标准答案只列该样本真实存在的字段）
- 边界样本的"多抽"单独统计：缺报价的样本如果抽出了报价，记为误报并扣分

用法：
  python tools/eval_parse.py            # 只打印
  python tools/eval_parse.py --strict   # 低于 90% 视为失败（退出码 1）
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="复算 D2 解析指标")
    ap.add_argument("--samples", default=str(SAMPLES))
    ap.add_argument("--strict", action="store_true", help="低于 90% 返回非 0")
    args = ap.parse_args(argv)

    base = Path(args.samples)
    manifest_path = base / "manifest.json"
    if not manifest_path.exists():
        print(f"缺少标准答案：{manifest_path}（先跑 python tools/make_samples.py）")
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest.get("items") or []

    parsed_ok = 0
    expect_total = 0
    expect_hit = 0
    extra_hits = 0  # 边界样本多抽的字段数

    print(f"{'文件':<14}{'状态':<10}{'页':>3}{'字段':>5}{'应抽':>5}{'命中':>5}  说明")
    print("-" * 92)

    for item in items:
        path = base / item["file"]
        blob = path.read_bytes()
        doc = parse_file(blob, path.name, "eval", "eval")
        doc.fields = extract_fields(doc)
        values = {f.name: f.value for f in doc.fields}

        if doc.parse_status != "failed":
            parsed_ok += 1

        expect = item.get("expect") or {}
        hits, misses = [], []
        for key, want in expect.items():
            if matches(want, values.get(key, "")):
                hits.append(key)
            else:
                misses.append(f"{key}={values.get(key, '∅')}")

        # 标准答案里没有的字段，如果被抽出来，说明"编造"了
        extras = [k for k in values if k not in expect]
        extra_hits += len(extras)

        expect_total += len(expect)
        expect_hit += len(hits)

        note = "；".join(misses) if misses else ""
        if extras:
            note += f"（多抽：{'、'.join(extras)}）"
        if item.get("boundary"):
            note += f" [{item['boundary']}]"

        print(
            f"{item['file']:<14}{doc.parse_status:<10}{len(doc.pages):>3}"
            f"{len(doc.fields):>5}{len(expect):>5}{len(hits):>5}  {note}"
        )

    parse_rate = parsed_ok / len(items) if items else 0.0
    field_rate = expect_hit / expect_total if expect_total else 0.0

    print("-" * 92)
    print(f"解析成功率：{parsed_ok}/{len(items)} = {parse_rate:.1%}（要求 ≥ 90%）")
    print(f"字段准确率：{expect_hit}/{expect_total} = {field_rate:.1%}（要求 ≥ 90%）")
    if extra_hits:
        print(f"多抽字段：{extra_hits} 个（边界样本本不该存在，需为 0）")
    else:
        print("多抽字段：0 个（没有编造不存在的字段）")

    ok = parse_rate >= 0.9 and field_rate >= 0.9 and extra_hits == 0
    print(f"结论：{'通过' if ok else '未达标'}")
    return 0 if (ok or not args.strict) else 1


if __name__ == "__main__":
    sys.exit(main())
