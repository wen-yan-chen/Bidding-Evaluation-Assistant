"""资格性三态语义边界（本地纯函数，不写运行时数据）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from api.docmodel import Doc, PageSpan  # noqa: E402
from api.review import qualification  # noqa: E402


def doc(text: str) -> Doc:
    return Doc(doc_id="20260101-aaaaaaaa", file_name="semantic.txt", ext=".txt", sha256="0" * 64,
               page_source="single", full_text=text, pages=[PageSpan(page=1, start=0, end=len(text))])


CASES = {
    "合规否定式_无重大违法记录": "投标人：示例公司\n我方近三年内无重大违法记录，亦无行贿犯罪记录。\n",
    "明说未提供_营业执照": "投标人：示例公司\n未提供营业执照。\n",
    "先肯定后否定_营业执照": "投标人：示例公司\n营业执照：已提供。\n后附说明：未提供营业执照副本。\n",
    "相邻行无字干扰": "投标人：示例公司\n营业执照：已提供。\n社会保险：已缴纳社会保险。\n我方无重大违法记录。\n中小企业声明函：已提供。\n项目负责人：项目经理。\n",
}


def main() -> int:
    out = {}
    for name, text in CASES.items():
        q = qualification.check(doc(text))
        out[name] = {
            "states": {i["rule_id"]: i["state"] for i in q["items"]},
            "counts": q["counts"],
            "quotes": {i["rule_id"]: i.get("quote") for i in q["items"]},
        }
    Path(ROOT / "docs" / "评审功能测评数据" / "raw" / "qual-semantics.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
