"""把 docs/ 下四份项目文档排成中文 PDF（合集 + 单篇）。

依赖：reportlab（本地已安装）、Windows 中文字体 simhei.ttf。
Markdown 子集：标题、段落、列表、引用、代码块、表格、图片、链接、粗体/行内代码。
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    HRFlowable,
    Image,
    KeepTogether,
    LongTable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
    Frame,
)

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FONT = Path("C:/Windows/Fonts/simhei.ttf")
OUT_DIR = DOCS / "pdf"
OUT_DIR.mkdir(parents=True, exist_ok=True)

pdfmetrics.registerFont(TTFont("SimHei", str(FONT)))
pdfmetrics.registerFontFamily("SimHei", normal="SimHei", bold="SimHei", italic="SimHei", boldItalic="SimHei")

DOC_LIST = [
    ("开发说明.md", "架构、模块、规则/评分判据、门控、测试与 AgentsHub 提交"),
    ("数据说明.md", "25 份基线、15 份风险样本、40 条规则、250 条资格性标注、N01–N10"),
    ("评审说明.md", "N01–N10 重评的方法、10/10 结果、偏差来源、样本问题与局限"),
    ("使用说明.md", "5 分钟上手、界面、三步操作、结果阅读、常见问题"),
]

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="CoverTitle", fontName="SimHei", fontSize=28, leading=38,
    alignment=TA_CENTER, textColor=colors.HexColor("#123B5D"), spaceAfter=12,
))
styles.add(ParagraphStyle(
    name="CoverSub", fontName="SimHei", fontSize=12, leading=20,
    alignment=TA_CENTER, textColor=colors.HexColor("#4A6572"), spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="H1x", fontName="SimHei", fontSize=19, leading=25,
    textColor=colors.HexColor("#123B5D"), spaceBefore=8, spaceAfter=10,
))
styles.add(ParagraphStyle(
    name="H2x", fontName="SimHei", fontSize=14, leading=20,
    textColor=colors.HexColor("#1F5C7A"), spaceBefore=12, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="H3x", fontName="SimHei", fontSize=11.5, leading=17,
    textColor=colors.HexColor("#2A4B5C"), spaceBefore=8, spaceAfter=4,
))
styles.add(ParagraphStyle(
    name="Bodyx", fontName="SimHei", fontSize=9.8, leading=16,
    alignment=TA_LEFT, spaceAfter=5, wordWrap="CJK",
))
styles.add(ParagraphStyle(
    name="QuoteX", fontName="SimHei", fontSize=9.2, leading=15,
    leftIndent=12, textColor=colors.HexColor("#40505A"),
    backColor=colors.HexColor("#F2F6F8"), borderPadding=6, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="CodeX", fontName="SimHei", fontSize=7.8, leading=11,
    leftIndent=8, backColor=colors.HexColor("#F5F5F5"), borderPadding=5,
    textColor=colors.HexColor("#202020"),
))
styles.add(ParagraphStyle(
    name="CellX", fontName="SimHei", fontSize=7.2, leading=10, wordWrap="CJK",
))
styles.add(ParagraphStyle(
    name="CellHeadX", fontName="SimHei", fontSize=7.2, leading=10,
    textColor=colors.white, wordWrap="CJK",
))
styles.add(ParagraphStyle(
    name="CaptionX", fontName="SimHei", fontSize=7.8, leading=11,
    alignment=TA_CENTER, textColor=colors.HexColor("#5B6B73"), spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="TOCX", fontName="SimHei", fontSize=9.5, leading=18,
))


def inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r'<font color="#9C2A1A">\1</font>', text)
    return text


def is_table_sep(line: str) -> bool:
    return bool(re.match(r"^\s*\|?[\s:|-]+\|?\s*$", line)) and "-" in line


def add_table(story: list, rows: list[list[str]]) -> None:
    if not rows:
        return
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]
    data = []
    for i, row in enumerate(rows):
        cells = [Paragraph(inline(c.strip()), styles["CellHeadX"] if i == 0 else styles["CellX"]) for c in row]
        data.append(cells)
    width = 17.2 * cm
    col_w = [width / ncols] * ncols
    table = LongTable(data, colWidths=col_w, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F5C7A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D6DD")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFB")]),
    ]))
    story.append(table)
    story.append(Spacer(1, 6))


def image_flow(path: Path) -> list:
    if not path.exists():
        return []
    try:
        img = Image(str(path))
        max_w, max_h = 16.5 * cm, 9.5 * cm
        ratio = min(max_w / img.imageWidth, max_h / img.imageHeight)
        img.drawWidth = img.imageWidth * ratio
        img.drawHeight = img.imageHeight * ratio
        img.hAlign = "CENTER"
        return [Spacer(1, 4), img, Paragraph(path.name, styles["CaptionX"])]
    except Exception:
        return []


def parse_markdown(path: Path) -> list:
    lines = path.read_text(encoding="utf-8").splitlines()
    story: list = []
    i = 0
    while i < len(lines):
        raw = lines[i].rstrip()
        line = raw.strip()
        if not line:
            i += 1
            continue
        if line.startswith("```"):
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            story.append(Preformatted("\n".join(code), styles["CodeX"]))
            story.append(Spacer(1, 5))
            continue
        if line.startswith("|") and i + 1 < len(lines) and is_table_sep(lines[i + 1]):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c for c in lines[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            add_table(story, [r for n, r in enumerate(rows) if n != 1])
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            style = {1: "H1x", 2: "H2x", 3: "H3x", 4: "H3x"}[level]
            story.append(Paragraph(inline(m.group(2)), styles[style]))
            i += 1
            continue
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", line)
        if m:
            target = (path.parent / m.group(2)).resolve()
            story.extend(image_flow(target))
            i += 1
            continue
        if line.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            story.append(Paragraph(inline(" ".join(quote)), styles["QuoteX"]))
            continue
        if re.match(r"^[-*]\s+", line):
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i].strip()):
                story.append(Paragraph(inline(re.sub(r"^[-*]\s+", "", lines[i].strip())), styles["Bodyx"], bulletText="•"))
                i += 1
            continue
        if re.match(r"^\d+\.\s+", line):
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                story.append(Paragraph(inline(re.sub(r"^\d+\.\s+", "", lines[i].strip())), styles["Bodyx"], bulletText="•"))
                i += 1
            continue
        if line in ("---", "***"):
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#C9D6DD"), spaceBefore=4, spaceAfter=6))
            i += 1
            continue
        # paragraph: gather until blank / block marker
        para = [line]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt or nxt.startswith(("#", "```", "|", ">", "- ", "* ")) or re.match(r"^\d+\.\s+", nxt):
                break
            para.append(nxt)
            i += 1
        story.append(Paragraph(inline(" ".join(para)), styles["Bodyx"]))
    return story


def on_page(canvas, doc, title: str) -> None:
    canvas.saveState()
    canvas.setFont("SimHei", 8)
    canvas.setFillColor(colors.HexColor("#6B7C85"))
    canvas.drawString(1.9 * cm, 1.15 * cm, "招投标评审助手 · 项目文档")
    canvas.drawRightString(A4[0] - 1.9 * cm, 1.15 * cm, f"{doc.page}")
    canvas.restoreState()


def build(path: Path, files: list[tuple[Path, str]], cover: bool = True) -> None:
    doc = BaseDocTemplate(
        str(path), pagesize=A4,
        leftMargin=1.9 * cm, rightMargin=1.9 * cm,
        topMargin=1.7 * cm, bottomMargin=1.7 * cm,
        title="招投标评审助手 · 项目文档", author="Bidding Evaluation Assistant",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=lambda c, d: on_page(c, d, path.stem))])
    story: list = []
    if cover:
        story += [
            Spacer(1, 4.2 * cm),
            Paragraph("招投标评审助手", styles["CoverTitle"]),
            Paragraph("项目文档合集", styles["CoverTitle"]),
            Spacer(1, 0.6 * cm),
            Paragraph("开发说明 · 数据说明 · 评审说明 · 使用说明", styles["CoverSub"]),
            Spacer(1, 4.5 * cm),
            Paragraph("Nexent + FastAPI + MCP ｜ 课题 8 ｜ 政务民生", styles["CoverSub"]),
            Paragraph("2026-11-17", styles["CoverSub"]),
            PageBreak(),
            Paragraph("目录", styles["H1x"]),
            Spacer(1, 0.3 * cm),
        ]
        for name, desc in DOC_LIST:
            story.append(Paragraph(f"<b>{name}</b>　{desc}", styles["TOCX"]))
        story += [
            Spacer(1, 0.5 * cm),
            Paragraph("说明：本合集由 docs/ 下四份 Markdown 文档生成；结论以评审说明为准。", styles["QuoteX"]),
            PageBreak(),
        ]
    for idx, (file, title) in enumerate(files):
        if idx:
            story.append(PageBreak())
        story.append(Paragraph(title, styles["H1x"]))
        story.append(HRFlowable(width="100%", thickness=1.0, color=colors.HexColor("#1F5C7A"), spaceAfter=8))
        story.extend(parse_markdown(file))
    doc.build(story)


def main() -> int:
    files = [(DOCS / name, name.replace(".md", "")) for name, _ in DOC_LIST]
    combined = OUT_DIR / "招投标评审助手-文档合集.pdf"
    build(combined, files, cover=True)
    for file, title in files:
        build(OUT_DIR / f"{title}.pdf", [(file, title)], cover=False)
    for p in [combined, *[OUT_DIR / f"{t}.pdf" for _, t in files]]:
        print(p, p.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
