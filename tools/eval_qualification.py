"""资格性核验评测：对已人工标注的样本计算三态一致率，并跑 P1 语义回归用例。

口径：
- 只对 `data/samples/qualification_labels.json` 中已标注的 R01–R10 项计算一致率，
  未标注项不计入分母，避免把“没标注”说成“已通过”；
- `--strict`：已标注项有任一不一致、或语义回归用例失败，退出码 1；
- `--require-full`：还要求 25 份样本全部有标注；未全量时 strict 不通过。

用法：
  python tools/eval_qualification.py
  python tools/eval_qualification.py --strict
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.docmodel import Doc, PageSpan  # noqa: E402
from api.parsers.dispatch import parse_file  # noqa: E402
from api.review import qualification  # noqa: E402

SAMPLES = ROOT / "data" / "samples"
LABELS = SAMPLES / "qualification_labels.json"


def text_doc(text: str) -> Doc:
    return Doc(
        doc_id="20260101-aaaaaaaa",
        file_name="semantic.txt",
        ext=".txt",
        sha256="0" * 64,
        page_source="single",
        full_text=text,
        pages=[PageSpan(page=1, start=0, end=len(text))],
    )


SEMANTIC_CASES = [
    {
        "name": "合规否定式：无重大违法记录/相邻已提供材料",
        "text": (
            "投标人：示例公司\n"
            "营业执照：已提供。\n"
            "社会保险：已缴纳社会保险。\n"
            "我方近三年内无重大违法记录，亦无行贿犯罪记录。\n"
            "中小企业声明函：已提供。\n"
            "项目负责人：项目经理 1 名。\n"
            "联合体协议：本项目不接受联合体投标，无需提供联合体协议。\n"
        ),
        "expect": {"R01": "provided", "R06": "provided", "R07": "provided", "R08": "provided", "R10": "missing"},
        "forbid_insufficient": True,
        "not_applicable": ["R09"],
    },
    {
        "name": "R10 只认强资格证据：注册建造师应判已提供",
        "text": "投标人：示例公司\n项目负责人：项目经理 1 名，持二级注册建造师证书。\n",
        "expect": {"R10": "provided"},
    },
    {
        "name": "明说未提供：应判缺失而非效力不足",
        "text": "投标人：示例公司\n未提供营业执照。\n未提供财务报告。\n",
        "expect": {"R01": "missing", "R05": "missing"},
        "forbid_insufficient": True,
    },
    {
        "name": "过期：应判效力不足",
        "text": "投标人：示例公司\n营业执照：已过期。\n",
        "expect": {"R01": "insufficient"},
    },
    {
        "name": "无需提供：应标记不适用，不能判效力不足",
        "text": "投标人：示例公司\n无需提供社会保险缴纳证明。\n无需提供中小企业声明函。\n",
        "expect": {"R06": "missing", "R08": "missing"},
        "forbid_insufficient": True,
        "not_applicable": ["R06", "R08"],
    },
]


def run_labeled() -> tuple[list[str], int, int]:
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    problems: list[str] = []
    agree = 0
    total = 0
    for item in labels.get("items") or []:
        path = SAMPLES / item["file"]
        if not path.exists():
            problems.append(f"{item['file']}: 文件不存在")
            continue
        doc = parse_file(path.read_bytes(), path.name, "eval", "eval")
        result = qualification.check(doc)
        states = {i["rule_id"]: i["state"] for i in result["items"]}
        for rule_id, want in (item.get("expect") or {}).items():
            total += 1
            got = states.get(rule_id)
            if got == want:
                agree += 1
            else:
                problems.append(f"{item['file']} {rule_id}: 期望 {want}，实际 {got}")
    return problems, agree, total


def run_semantic() -> list[str]:
    problems: list[str] = []
    for case in SEMANTIC_CASES:
        result = qualification.check(text_doc(case["text"]))
        items = {i["rule_id"]: i for i in result["items"]}
        states = {rid: i["state"] for rid, i in items.items()}
        for rule_id, want in case["expect"].items():
            if states.get(rule_id) != want:
                problems.append(f"{case['name']} {rule_id}: 期望 {want}，实际 {states.get(rule_id)}")
        if case.get("forbid_insufficient") and result["counts"]["insufficient"]:
            problems.append(f"{case['name']}: 不应出现效力不足，实际 {result['counts']['insufficient']} 项")
        for rule_id in case.get("not_applicable") or []:
            item = items.get(rule_id)
            if item is None or item.get("applicable") is not False:
                problems.append(f"{case['name']} {rule_id}: 应标记 applicable=false")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="资格性三态评测")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--require-full", action="store_true", help="要求 25 份样本全部有标注")
    args = ap.parse_args(argv)

    problems, agree, total = run_labeled()
    sem_problems = run_semantic()
    all_problems = problems + sem_problems
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    manifest = json.loads((SAMPLES / "manifest.json").read_text(encoding="utf-8"))
    labeled_docs = len(labels.get("items") or [])
    total_docs = len(manifest.get("items") or [])
    coverage_ok = labeled_docs >= total_docs
    for problem in all_problems:
        print(f"[FAIL] {problem}")
    rate = agree / total if total else 0.0
    print(f"已标注项：{total}｜一致 {agree}/{total} = {rate:.1%}｜未标注项不计入")
    print(f"语义回归用例：{len(SEMANTIC_CASES)} 个｜失败 {len(sem_problems)} 个")
    print(f"标注覆盖：{labeled_docs} 份 / {total_docs} 份"
          + ("（全量）" if coverage_ok else "（未全量；不能宣称全量 ≥90%）"))
    workable = total > 0 and not all_problems and (coverage_ok or not args.require_full)
    if args.require_full and not coverage_ok:
        print("[FAIL] --require-full：标注未覆盖全部样本")
    print(f"结论：{'通过（仅就已标注项）' if workable else '未通过'}")
    return 0 if (workable or not args.strict) else 1


if __name__ == "__main__":
    raise SystemExit(main())
