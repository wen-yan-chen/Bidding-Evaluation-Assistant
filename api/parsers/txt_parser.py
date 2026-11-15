"""纯文本解析：先嗅探编码（招标文件常见 GB18030），再按换页符 / 字数分页。"""

from __future__ import annotations

from api.docmodel import Doc, build_pages, estimate_pages
from api.parsers import ParseError

ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "utf-16")


def _decode(blob: bytes) -> tuple[str, str]:
    for enc in ENCODINGS:
        try:
            return blob.decode(enc), enc
        except UnicodeDecodeError:
            continue
    raise ParseError("文本编码无法识别（试过 utf-8 / gb18030 / utf-16），请另存为 UTF-8")


def parse(blob: bytes, file_name: str, doc_id: str, sha256: str, ext: str = ".txt") -> Doc:
    text, encoding = _decode(blob)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    if "\f" in text:
        chunks = [chunk if chunk.endswith("\n") else chunk + "\n" for chunk in text.split("\f")]
        page_source = "native"
    elif len(text) > 1100:
        chunks = estimate_pages(text)
        page_source = "estimated"
    else:
        chunks = [text]
        page_source = "single"

    full_text, pages = build_pages(chunks)
    doc = Doc(
        doc_id=doc_id,
        file_name=file_name,
        ext=ext,
        sha256=sha256,
        page_source=page_source,
        full_text=full_text,
        pages=pages,
        meta={"encoding": encoding},
    )

    if not full_text.strip():
        doc.parse_status = "failed"
        doc.degraded.append("文本文件为空")
    elif page_source == "estimated":
        doc.add_degraded("纯文本无换页符，页码按每页约 1100 字估算")

    return doc
