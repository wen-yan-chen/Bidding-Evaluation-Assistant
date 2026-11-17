"""解析边界：空白页 / 低分辨率 / 旋转 / 重复页 / 缺页 / 空文件 / 损坏文件。"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as q

BOUND = q.ROOT / "data" / "samples" / "boundary"


def save_pdf(writer: PdfWriter, name: str) -> Path:
    path = q.RAW / "tmp_inputs" / name
    with path.open("wb") as fh:
        writer.write(fh)
    return path


def main() -> int:
    q.ensure_dirs()
    (q.RAW / "tmp_inputs").mkdir(parents=True, exist_ok=True)
    out: dict = {"started_at": q.now(), "items": []}

    files = ["blank-page.pdf", "lowres-scan.pdf", "rotated-scan.pdf"]
    for name in files:
        up = q.upload(BOUND / name, name=f"QA20261116-boundary-{name}", timeout=300)
        body = up["body"] or {}
        out["items"].append({"case": name, "status": up["status"], "ms": round(up["ms"], 1),
                             "parse_status": body.get("parse_status"), "pages": body.get("page_count"),
                             "ocr_pages": body.get("ocr_pages"), "empty_pages": body.get("empty_pages"),
                             "fields": {f["name"]: f["value"] for f in body.get("fields") or []},
                             "degraded": body.get("degraded")})
        print(name, up["status"], body.get("parse_status"), body.get("page_count"), body.get("ocr_pages"),
              len(body.get("fields") or []), round(up["ms"]))

    # 重复页：scan-001 第 1 页重复两次 + 第 2 页
    reader = PdfReader(str(q.ROOT / "data" / "samples" / "scan-001.pdf"))
    writer = PdfWriter()
    for idx in (0, 0, 1):
        writer.add_page(reader.pages[idx])
    dup = save_pdf(writer, "QA20261116-dup-page.pdf")
    up = q.upload(dup, name=dup.name, timeout=300)
    body = up["body"] or {}
    out["items"].append({"case": "重复页（scan-001 p1 重复）", "status": up["status"], "ms": round(up["ms"], 1),
                         "parse_status": body.get("parse_status"), "pages": body.get("page_count"),
                         "ocr_pages": body.get("ocr_pages"), "fields": {f["name"]: f["value"] for f in body.get("fields") or []},
                         "degraded": body.get("degraded")})
    print("dup", up["status"], body.get("parse_status"), body.get("page_count"), len(body.get("fields") or []))

    # 缺页：bid-004.pdf 去掉最后一页
    reader = PdfReader(str(q.ROOT / "data" / "samples" / "bid-004.pdf"))
    writer = PdfWriter()
    for page in list(reader.pages)[:-1]:
        writer.add_page(page)
    miss = save_pdf(writer, "QA20261116-missing-page.pdf")
    up = q.upload(miss, name=miss.name, timeout=120)
    body = up["body"] or {}
    out["items"].append({"case": "缺页（bid-004 去掉末页）", "status": up["status"], "ms": round(up["ms"], 1),
                         "parse_status": body.get("parse_status"), "pages": body.get("page_count"),
                         "fields": {f["name"]: f["value"] for f in body.get("fields") or []},
                         "degraded": body.get("degraded")})
    print("missing", up["status"], body.get("parse_status"), body.get("page_count"), len(body.get("fields") or []))

    # 插入空白页：bid-004 第 1 页后插空白页
    reader = PdfReader(str(q.ROOT / "data" / "samples" / "bid-004.pdf"))
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    writer.add_blank_page(width=float(reader.pages[0].mediabox.width), height=float(reader.pages[0].mediabox.height))
    for page in list(reader.pages)[1:]:
        writer.add_page(page)
    blank = save_pdf(writer, "QA20261116-blank-inserted.pdf")
    up = q.upload(blank, name=blank.name, timeout=300)
    body = up["body"] or {}
    out["items"].append({"case": "插入空白页（bid-004 第 2 页空白）", "status": up["status"], "ms": round(up["ms"], 1),
                         "parse_status": body.get("parse_status"), "pages": body.get("page_count"),
                         "ocr_pages": body.get("ocr_pages"), "empty_pages": body.get("empty_pages"),
                         "fields": {f["name"]: f["value"] for f in body.get("fields") or []},
                         "degraded": body.get("degraded")})
    print("blank", up["status"], body.get("parse_status"), body.get("page_count"), body.get("empty_pages"),
          len(body.get("fields") or []))

    q.jdump(q.RAW / "boundary-raw.json", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
