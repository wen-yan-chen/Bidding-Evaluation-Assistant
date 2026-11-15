"""pdf 解析：逐页取文本层，页码天然精确（`page_source=native`）。

扫描件（无文本层的页）不猜：记为降级，并在 `degraded` 里点名页码，
D3 接 OCR 后由 OCR 通道补齐。这里绝不用"空页"冒充"解析成功"。
"""

from __future__ import annotations

import io

from pypdf import PdfReader

from api.docmodel import Doc, build_pages
from api.parsers import ParseError


def parse(blob: bytes, file_name: str, doc_id: str, sha256: str) -> Doc:
    try:
        reader = PdfReader(io.BytesIO(blob))
    except Exception as exc:
        raise ParseError(f"pdf 无法打开：{exc}") from exc

    if reader.is_encrypted:
        # 空口令能解就解，解不开如实报错，不返回半截内容
        try:
            if not reader.decrypt(""):
                raise ParseError("pdf 有密码保护，无法解析")
        except ParseError:
            raise
        except Exception as exc:
            raise ParseError(f"pdf 解密失败：{exc}") from exc

    page_texts: list[str] = []
    empty_pages: list[int] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # 单页坏不牵连整份文档
            text = ""
        if not text.strip():
            empty_pages.append(index)
        page_texts.append(text if text.endswith("\n") else text + "\n")

    if not page_texts:
        page_texts = [""]

    full_text, pages = build_pages(page_texts)
    doc = Doc(
        doc_id=doc_id,
        file_name=file_name,
        ext=".pdf",
        sha256=sha256,
        page_source="native",
        full_text=full_text,
        pages=pages,
        meta={"pdf_pages": len(page_texts), "empty_pages": empty_pages},
    )

    if empty_pages:
        shown = "、".join(str(p) for p in empty_pages[:8])
        more = "" if len(empty_pages) <= 8 else f" 等 {len(empty_pages)} 页"
        doc.add_degraded(f"第 {shown}{more} 页无文本层（疑似扫描页，D3 由 OCR 补齐）")

    if not full_text.strip():
        doc.parse_status = "failed"
        doc.degraded.append("整份 PDF 无文本层（扫描件），D3 接 OCR 后才能解析")

    return doc
