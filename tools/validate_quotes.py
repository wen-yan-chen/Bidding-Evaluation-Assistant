"""校验溯源三元组：`full_text[char_start:char_end] == quote`，且页码与偏移一致。

这是 D2 的验收闸门，也是后面所有"点击跳回原文"的前提：
只要这条过不了，报告里的任何"引用原文"都不可信。

用法：
  python tools/validate_quotes.py                # 校验 data/parsed 下全部结果
  python tools/validate_quotes.py --dir other    # 指定目录
  python tools/validate_quotes.py --file x.json  # 只校验一份
退出码：0 全部通过；1 存在不一致。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.docmodel import Doc  # noqa: E402


def check_doc(doc: Doc) -> list[str]:
    """返回问题列表；空列表表示这份文档的溯源完全自洽。"""
    problems: list[str] = []

    for field in doc.fields:
        sliced = doc.full_text[field.char_start : field.char_end]
        if sliced != field.quote:
            problems.append(
                f"字段 {field.name}: 切片与 quote 不一致（切片={sliced[:20]!r} quote={field.quote[:20]!r}）"
            )
        if field.quote and field.quote not in doc.full_text:
            problems.append(f"字段 {field.name}: quote 不在原文中")
        expected_page = doc.page_of(field.char_start)
        if expected_page != field.page:
            problems.append(
                f"字段 {field.name}: 声明第 {field.page} 页，偏移落在第 {expected_page} 页"
            )

    for clause in doc.clauses:
        sliced = doc.full_text[clause.char_start : clause.char_end]
        if sliced != clause.text:
            problems.append(f"条款 {clause.clause_id}: 切片与 text 不一致")
        expected_page = doc.page_of(clause.char_start)
        if expected_page != clause.page:
            problems.append(
                f"条款 {clause.clause_id}: 声明第 {clause.page} 页，偏移落在第 {expected_page} 页"
            )

    # 页码表本身要覆盖全文且不乱序
    last_end = 0
    for span in doc.pages:
        if span.start > span.end:
            problems.append(f"第 {span.page} 页区间非法：[{span.start}, {span.end})")
        if span.start != last_end:
            problems.append(f"第 {span.page} 页起点 {span.start} 与前页终点 {last_end} 不连续")
        last_end = span.end
    if doc.pages and doc.pages[-1].end != len(doc.full_text):
        problems.append("最后一页没有覆盖到全文末尾")

    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="校验解析结果的溯源一致性")
    ap.add_argument("--dir", default=str(ROOT / "data" / "parsed"), help="解析结果目录")
    ap.add_argument("--file", help="只校验一个 JSON 文件")
    args = ap.parse_args(argv)

    if args.file:
        paths = [Path(args.file)]
    else:
        base = Path(args.dir)
        paths = sorted(base.glob("*.json")) if base.exists() else []

    if not paths:
        print(f"没有可校验的结果文件：{args.dir}")
        print("先上传一份样本：python tools/smoke_test.py 或 curl -F 'file=@data/samples/bid-001.docx' /api/upload")
        return 1

    total_fields = 0
    total_clauses = 0
    bad_docs = 0

    for path in paths:
        doc = Doc.from_dict(json.loads(path.read_text(encoding="utf-8")))
        problems = check_doc(doc)
        total_fields += len(doc.fields)
        total_clauses += len(doc.clauses)
        mark = "PASS" if not problems else "FAIL"
        print(
            f"{mark}  {doc.file_name:<16} 页={len(doc.pages):<3} 字段={len(doc.fields):<2} "
            f"条款={len(doc.clauses):<3} 状态={doc.parse_status}"
        )
        for problem in problems:
            print(f"      - {problem}")
        if problems:
            bad_docs += 1

    print("-" * 72)
    print(
        f"校验 {len(paths)} 份文档：字段 {total_fields} 个、条款 {total_clauses} 条；"
        f"不一致文档 {bad_docs} 份"
    )
    if bad_docs:
        print("结论：不通过。")
        return 1
    print("结论：通过。所有 quote 与切片、页码与偏移完全自洽。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
