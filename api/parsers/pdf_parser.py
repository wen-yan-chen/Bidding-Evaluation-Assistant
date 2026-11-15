"""pdf 解析：逐页取文本层，页码天然精确（`page_source=native`）。

D3 起：文本层为空的页（扫描件）走 OCR 通道补齐，并**逐页标注来源**：
- `meta.text_pages`：文本层页（溯源最可信）
- `meta.ocr_pages`：OCR 页（文本来自识别，可能有误，页面会提示人工复核）
- `meta.empty_pages`：OCR 也没认出文字的页（如实留空，不编造）

OCR 可用与否由 `OCR_ENABLE`（默认 1）控制；依赖缺失时自动跳过并把原因写进 `degraded`。
"""

from __future__ import annotations

import io
import os

from pypdf import PdfReader

from api.docmodel import Doc, build_pages
from api.parsers import ParseError
from api.parsers import ocr as ocr_mod

OCR_ENABLED = os.getenv("OCR_ENABLE", "1") != "0"


def parse(blob: bytes, file_name: str, doc_id: str, sha256: str) -> Doc:
    try:
        reader = PdfReader(io.BytesIO(blob))
    except Exception as exc:
        raise ParseError(f"pdf 无法打开：{exc}") from exc

    if reader.is_encrypted:
        try:
            if not reader.decrypt(""):
                raise ParseError("pdf 有密码保护，无法解析")
        except ParseError:
            raise
        except Exception as exc:
            raise ParseError(f"pdf 解密失败：{exc}") from exc

    page_texts: list[str] = []
    text_pages: list[int] = []
    ocr_pages: list[int] = []
    empty_pages: list[int] = []
    low_conf = 0
    ocr_error = ""

    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # 单页坏不牵连整份文档
            text = ""

        if text.strip():
            text_pages.append(index)
        elif OCR_ENABLED and ocr_mod.available():
            result = ocr_mod.ocr_pdf_page(blob, index - 1)
            if result["text"].strip():
                text = result["text"]
                ocr_pages.append(index)
                low_conf += int(result.get("low_conf") or 0)
            else:
                empty_pages.append(index)
                ocr_error = result.get("error") or ocr_error
        else:
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
        meta={
            "pdf_pages": len(page_texts),
            "text_pages": text_pages,
            "ocr_pages": ocr_pages,
            "empty_pages": empty_pages,
            "ocr_low_conf_lines": low_conf,
            "ocr_enabled": OCR_ENABLED,
        },
    )

    if ocr_pages:
        shown = "、".join(str(p) for p in ocr_pages[:8])
        more = "" if len(ocr_pages) <= 8 else f" 等 {len(ocr_pages)} 页"
        note = f"第 {shown}{more} 页为 OCR 识别文本（可能有识别误差，建议人工复核）"
        if low_conf:
            note += f"；{low_conf} 行置信度过低已丢弃"
        doc.add_degraded(note)

    if empty_pages:
        shown = "、".join(str(p) for p in empty_pages[:8])
        more = "" if len(empty_pages) <= 8 else f" 等 {len(empty_pages)} 页"
        reason = f"（{ocr_error}）" if ocr_error else ""
        doc.add_degraded(f"第 {shown}{more} 页无文字{reason}，已留空，不作推断")

    if not full_text.strip():
        doc.parse_status = "failed"
        if not OCR_ENABLED:
            doc.degraded.append("整份 PDF 无文本层，且 OCR 已禁用（OCR_ENABLE=0）")
        elif not ocr_mod.available():
            doc.degraded.append("整份 PDF 无文本层，且 OCR 依赖不可用")
        else:
            doc.degraded.append("整份 PDF 无文本层，OCR 也未能识别出文字")

    return doc
