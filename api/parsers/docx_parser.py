"""docx 解析：段落与表格按正文顺序取出，再建页码映射。

docx 没有"页"的概念（分页是排版时算的），所以这里分两种情况，并且**如实标注**：
- 文档里有显式分页符（`w:br type="page"`）→ 按分页符切页，`page_source=native`；
- 没有分页符 → 按字符预算估算页，`page_source=estimated`，并在 `degraded` 里说明。
下游（跳转原文）会读 `page_source`，估算页只承诺"大致位置"，不承诺精确到页。
"""

from __future__ import annotations

import io

from docx import Document as WordDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from api.docmodel import Doc, build_pages, estimate_pages
from api.parsers import ParseError

PAGE_BREAK_XPATH = './/w:br[@w:type="page"]'
ESTIMATE_NOTE = "docx 无分页符，页码按每页约 1100 字估算（跳转可能偏 1 页）"


def _iter_blocks(document):
    """按正文顺序产出段落与表格（python-docx 默认只给段落，会把表格位置丢掉）。"""
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def _table_text(table: Table) -> str:
    lines: list[str] = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            text = " ".join(p.text.strip() for p in cell.paragraphs if p.text.strip())
            cells.append(text)
        if any(cells):
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def parse(blob: bytes, file_name: str, doc_id: str, sha256: str) -> Doc:
    try:
        document = WordDocument(io.BytesIO(blob))
    except Exception as exc:  # 损坏、非 docx、加密
        raise ParseError(f"docx 无法打开：{exc}") from exc

    chunks: list[str] = []
    current: list[str] = []
    explicit_breaks = 0

    for block in _iter_blocks(document):
        if isinstance(block, Paragraph):
            breaks = block._p.xpath(PAGE_BREAK_XPATH)
            text = block.text.strip()
            if text:
                current.append(text)
            if breaks:
                explicit_breaks += len(breaks)
                chunks.append("\n".join(current))
                current = []
        else:
            table_text = _table_text(block)
            if table_text:
                current.append(table_text)

    if current or not chunks:
        chunks.append("\n".join(current))

    if explicit_breaks:
        page_source = "native"
        full_text, pages = build_pages([c + "\n" for c in chunks])
    else:
        page_source = "estimated"
        raw = "\n".join(chunks)
        full_text, pages = build_pages(estimate_pages(raw))

    doc = Doc(
        doc_id=doc_id,
        file_name=file_name,
        ext=".docx",
        sha256=sha256,
        page_source=page_source,
        full_text=full_text,
        pages=pages,
        meta={"explicit_page_breaks": explicit_breaks, "table_blocks": sum(1 for b in _iter_blocks(document) if isinstance(b, Table))},
    )

    if not full_text.strip():
        doc.parse_status = "failed"
        doc.degraded.append("文档中未提取到任何文本（可能是纯图片内容，D3 接 OCR）")
    elif page_source == "estimated":
        doc.add_degraded(ESTIMATE_NOTE)

    return doc
