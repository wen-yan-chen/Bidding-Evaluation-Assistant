"""docx 解析：段落与表格按正文顺序取出，再建页码映射。

docx 没有"页"的概念（分页是排版时算的），所以这里分两种情况，并且**如实标注**：
- 文档里有显式分页符（`w:br type="page"`）→ 按分页符切页，`page_source=native`；
- 没有分页符 → **按行数估算**（每页约 38 行、每行约 38 字，小四宋体 A4），`page_source=estimated`，
  并在 `degraded` 里说明。D3 把 D2 的"按字符数"换成"按段落行数"，与 Word 的分页更接近：
  短段落多的文档不会再被压成两页。
"""

from __future__ import annotations

import io
import math

from docx import Document as WordDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from api.docmodel import Doc, build_pages
from api.parsers import ParseError

PAGE_BREAK_XPATH = './/w:br[@w:type="page"]'
LINES_PER_PAGE = 38
CHARS_PER_LINE = 38
ESTIMATE_NOTE = f"docx 无分页符，页码按每页约 {LINES_PER_PAGE} 行估算（跳转可能偏 1 页）"


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


def _visual_lines(text: str) -> int:
    """估算一段文字排版后占几行（按每行 38 字硬折）。"""
    if not text:
        return 0
    return sum(max(1, math.ceil(len(line) / CHARS_PER_LINE)) for line in text.split("\n"))


def parse(blob: bytes, file_name: str, doc_id: str, sha256: str) -> Doc:
    try:
        document = WordDocument(io.BytesIO(blob))
    except Exception as exc:  # 损坏、非 docx、加密
        raise ParseError(f"docx 无法打开：{exc}") from exc

    segments: list[tuple[str, int]] = []  # (文本, 该段后的分页符个数)
    table_blocks = 0
    for block in _iter_blocks(document):
        if isinstance(block, Paragraph):
            segments.append((block.text.strip(), len(block._p.xpath(PAGE_BREAK_XPATH))))
        else:
            table_blocks += 1
            segments.append((_table_text(block), 0))

    explicit_breaks = sum(breaks for _, breaks in segments)

    if explicit_breaks:
        page_source = "native"
        chunks: list[str] = []
        current: list[str] = []
        for text, breaks in segments:
            if text:
                current.append(text)
            if breaks:
                chunks.append("\n".join(current))
                current = []
        if current or not chunks:
            chunks.append("\n".join(current))
    else:
        page_source = "estimated"
        chunks = []
        current = []
        lines_in_page = 0
        for text, _ in segments:
            if not text:
                continue
            lines = _visual_lines(text)
            # 超页就换页；单段超长时独占一页，不再硬切（切了会破坏 quote 连续性）
            if current and lines_in_page + lines > LINES_PER_PAGE:
                chunks.append("\n".join(current))
                current = []
                lines_in_page = 0
            current.append(text)
            lines_in_page += lines
        if current:
            chunks.append("\n".join(current))

    full_text, pages = build_pages([chunk + "\n" for chunk in chunks])

    doc = Doc(
        doc_id=doc_id,
        file_name=file_name,
        ext=".docx",
        sha256=sha256,
        page_source=page_source,
        full_text=full_text,
        pages=pages,
        meta={
            "explicit_page_breaks": explicit_breaks,
            "table_blocks": table_blocks,
            "lines_per_page": LINES_PER_PAGE,
            "chars_per_line": CHARS_PER_LINE,
        },
    )

    if not full_text.strip():
        doc.parse_status = "failed"
        doc.degraded.append("文档中未提取到任何文本（可能是纯图片内容，D3 的 OCR 只接 PDF）")
    elif page_source == "estimated":
        doc.add_degraded(ESTIMATE_NOTE)

    return doc
