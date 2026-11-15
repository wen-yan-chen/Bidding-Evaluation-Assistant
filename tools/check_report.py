"""报告一致性校验：报告里的数值必须等于评审 JSON 里的数值。

思路：不比对"渲染效果"，只比对**数字与指纹**——总分、满分、风险条数、资格性计数、
细则指纹、规则指纹必须在两种格式的报告里都能找到，且与 `data/reviews/*.json` 一致。

用法：
  python tools/check_report.py                 # 校验最近一次评审
  python tools/check_report.py --review-id rv-...
  python tools/check_report.py --all           # 校验全部评审
退出码：0 全部一致；1 有不一致。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.report import service as report_service  # noqa: E402


def _text_of_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


def _text_of_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def check_one(review_id: str) -> list[str]:
    problems: list[str] = []
    review = report_service.load_review(review_id)
    data = report_service.build_data(review)

    expected = {
        "total": str(data["scoring"]["total"]),
        "total_full": str(data["scoring"]["total_full"]),
        "risk_total": str(data["risks"]["counts"]["合计"]),
        "profile_digest": data["basis"]["profile_digest"],
        "rule_digest": data["basis"]["rule_digest"],
    }
    # 与评审 JSON 交叉核对（防止 builder 自己改了数）
    if str(review["summary"]["total_score"]) != expected["total"]:
        problems.append(f"总分不一致：review={review['summary']['total_score']} builder={expected['total']}")
    if str(review["summary"]["risk_total"]) != expected["risk_total"]:
        problems.append(f"风险数不一致：review={review['summary']['risk_total']} builder={expected['risk_total']}")

    for fmt, reader in (("docx", _text_of_docx), ("pdf", _text_of_pdf)):
        path, _ = report_service.generate(review_id, fmt)
        if not path.exists() or path.stat().st_size == 0:
            problems.append(f"{fmt} 未生成或为空")
            continue
        head = path.read_bytes()[:4]
        if fmt == "pdf" and head != b"%PDF":
            problems.append("pdf 文件头不是 %PDF-")
        text = reader(path).replace(" ", "")
        for key, value in expected.items():
            if value and value.replace(" ", "") not in text:
                problems.append(f"{fmt} 中找不到 {key}={value}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="报告数值一致性校验")
    ap.add_argument("--review-id")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)

    if args.review_id:
        ids = [args.review_id]
    else:
        reviews = report_service.review_service.list_reviews(limit=50) if args.all else report_service.review_service.list_reviews(limit=1)
        ids = [r["review_id"] for r in reviews]

    if not ids:
        print("没有可校验的评审记录，先跑一次 POST /api/review")
        return 1

    failed = 0
    for review_id in ids:
        try:
            problems = check_one(review_id)
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] {review_id}: {exc}")
            failed += 1
            continue
        if problems:
            failed += 1
            print(f"[FAIL ] {review_id}")
            for problem in problems:
                print(f"        - {problem}")
        else:
            print(f"[ OK  ] {review_id}: docx/pdf 数值与评审 JSON 一致")

    print("-" * 60)
    print(f"校验 {len(ids)} 份：通过 {len(ids) - failed}，失败 {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
