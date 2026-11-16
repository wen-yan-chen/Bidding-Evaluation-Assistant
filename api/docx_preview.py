"""把 docx 渲染成可在浏览器中查看的 HTML（Word 版式近似）。

浏览器不能原生显示 docx；这里用 python-docx 读取段落、run、表格和图片，
生成一个 A4 白纸风格的 HTML 页面，供双栏「源文件」和预览弹窗内嵌。

注意：这是**近似渲染**，不追求与 Word 分页完全一致；原版式仍以保存的原件为准。
"""

from __future__ import annotations

import base64
import html
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

_ALIGN = {
    WD_ALIGN_PARAGRAPH.CENTER: "center",
    WD_ALIGN_PARAGRAPH.RIGHT: "right",
    WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
    WD_ALIGN_PARAGRAPH.LEFT: "left",
}


def _run_html(run, doc) -> str:
    pieces: list[str] = []
    if run.text:
        pieces.append(html.escape(run.text).replace("\t", "    ").replace("\n", "<br>"))
    for blip in run._element.xpath(".//a:blip"):
        rid = blip.get(qn("r:embed"))
        part = doc.part.related_parts.get(rid) if rid else None
        blob = getattr(part, "blob", None)
        if not blob:
            continue
        mime = getattr(part, "content_type", None) or "image/png"
        encoded = base64.b64encode(blob).decode("ascii")
        pieces.append(f'<img alt="" src="data:{mime};base64,{encoded}">')
    if not pieces:
        return ""
    inner = "".join(pieces)
    if run.bold:
        inner = f"<strong>{inner}</strong>"
    if run.italic:
        inner = f"<em>{inner}</em>"
    if run.underline:
        inner = f"<u>{inner}</u>"
    styles: list[str] = []
    try:
        if run.font.size is not None:
            styles.append(f"font-size:{run.font.size.pt:.1f}pt")
    except (AttributeError, ValueError):
        pass
    try:
        if run.font.color is not None and run.font.color.rgb is not None:
            styles.append(f"color:#{run.font.color.rgb}")
    except (AttributeError, ValueError):
        pass
    if styles:
        inner = f'<span style="{";".join(styles)}">{inner}</span>'
    return inner


def _paragraph_html(paragraph: Paragraph, doc) -> str:
    runs = "".join(_run_html(run, doc) for run in paragraph.runs)
    if not runs:
        runs = "&nbsp;"
    style_name = (paragraph.style.name if paragraph.style is not None else "") or ""
    style_key = style_name.lower()
    align = _ALIGN.get(paragraph.alignment)
    cls = ""
    if style_key.startswith("heading 1") or style_name.startswith("标题 1"):
        tag = "h1"
    elif style_key.startswith("heading 2") or style_name.startswith("标题 2"):
        tag = "h2"
    elif style_key.startswith("heading 3") or style_name.startswith("标题 3"):
        tag = "h3"
    elif style_key in ("title",) or style_name in ("标题",):
        tag = "h1"
        cls = ' class="doc-title"'
    elif style_key in ("subtitle",) or style_name in ("副标题",):
        tag = "p"
        cls = ' class="doc-subtitle"'
    elif style_name in ("List Bullet", "列表项目符号"):
        tag = "p"
        cls = ' class="doc-list"'
        runs = f"• {runs}"
    elif style_name in ("List Number", "列表编号"):
        tag = "p"
        cls = ' class="doc-list"'
    else:
        tag = "p"
    style = f' style="text-align:{align}"' if align else ""
    return f"<{tag}{cls}{style}>{runs}</{tag}>"


def _table_html(table: Table, doc) -> str:
    rows: list[str] = []
    for row in table.rows:
        cells: list[str] = []
        for cell in row.cells:
            body = "".join(_paragraph_html(p, doc) for p in cell.paragraphs)
            if cell.tables:
                body += "".join(_table_html(t, doc) for t in cell.tables)
            cells.append(f"<td>{body or '&nbsp;'}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return f'<table class="doc-table">{"".join(rows)}</table>'


def render_docx_html(path: Path, file_name: str, doc_id: str) -> str:
    document = Document(str(path))
    body: list[str] = []
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            body.append(_paragraph_html(Paragraph(child, document), document))
        elif isinstance(child, CT_Tbl):
            body.append(_table_html(Table(child, document), document))
    safe_name = html.escape(file_name)
    content = "".join(body) or '<p class="doc-empty">文档没有可显示的段落。</p>'
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_name}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #f3f5f9; color: #1f2a44; font-family: "Microsoft YaHei", "SimSun", sans-serif; }}
  .docx-toolbar {{ position: sticky; top: 0; z-index: 2; display: flex; align-items: center; justify-content: space-between;
    gap: 10px; padding: 8px 14px; background: #ffffff; border-bottom: 1px solid #e4e9f2; font-size: 12px; color: #5b6b86; }}
  .docx-toolbar a {{ color: #1f4fd8; text-decoration: none; border: 1px solid #cfdcff; background: #eef4ff;
    border-radius: 6px; padding: 4px 9px; white-space: nowrap; }}
  .docx-preview {{ width: 820px; max-width: 100%; min-height: calc(100vh - 37px); margin: 14px auto;
    padding: 52px 64px 64px; background: #ffffff; box-shadow: 0 3px 18px rgba(22, 48, 127, .10); }}
  .docx-preview p {{ margin: 0 0 9px; font-size: 13.5px; line-height: 1.9; white-space: pre-wrap; word-break: break-word; }}
  .docx-preview h1 {{ margin: 18px 0 12px; font-size: 23px; line-height: 1.5; text-align: center; }}
  .docx-preview h2 {{ margin: 16px 0 9px; font-size: 18px; line-height: 1.5; }}
  .docx-preview h3 {{ margin: 13px 0 7px; font-size: 15.5px; line-height: 1.5; }}
  .docx-preview .doc-title {{ font-size: 26px; letter-spacing: 2px; text-align: center; margin: 8px 0 26px; }}
  .docx-preview .doc-subtitle {{ text-align: center; color: #5b6b86; font-size: 14px; }}
  .docx-preview .doc-list {{ padding-left: 18px; }}
  .docx-preview .doc-empty {{ color: #8a97ad; text-align: center; margin-top: 80px; }}
  .docx-preview img {{ max-width: 100%; height: auto; display: block; margin: 8px auto; }}
  .doc-table {{ width: 100%; border-collapse: collapse; margin: 10px 0 14px; font-size: 12.5px; }}
  .doc-table td {{ border: 1px solid #cfd8e8; padding: 6px 8px; vertical-align: top; line-height: 1.7; }}
  .doc-table p {{ margin: 0 0 3px; font-size: 12.5px; line-height: 1.7; }}
  @media print {{ body {{ background: #fff; }} .docx-toolbar {{ display: none; }}
    .docx-preview {{ margin: 0; padding: 0; width: auto; box-shadow: none; }} }}
</style>
</head>
<body>
<div class="docx-toolbar"><span>Word 渲染预览 · {safe_name}</span></div>
<main class="docx-preview">{content}</main>
</body>
</html>"""
