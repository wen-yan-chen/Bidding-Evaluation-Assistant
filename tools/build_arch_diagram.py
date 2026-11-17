"""生成架构图 PPT，并渲染为 PNG，供主 deck 作为图片插入。"""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
OUT_PPTX = ROOT / "docs" / "_arch_diagram.pptx"

PAPER = RGBColor(0xFF, 0xFF, 0xFF)
BLUE = RGBColor(0x00, 0x63, 0xFF)
DEEP = RGBColor(0x00, 0x43, 0xA8)
NAVY = RGBColor(0x00, 0x2B, 0x6B)
INK = RGBColor(0x1A, 0x22, 0x2E)
BODY = RGBColor(0x5A, 0x67, 0x78)
LIGHT = RGBColor(0xE9, 0xF1, 0xFF)
PALE = RGBColor(0xF3, 0xF8, 0xFF)
LINE = RGBColor(0xC9, 0xD6, 0xEA)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Noto Sans SC"


def _font(run, size=11, bold=False, color=INK, font=FONT):
    run.font.name = font
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = color
    rpr = run._r.get_or_add_rPr()
    ea = rpr.makeelement("{http://schemas.openxmlformats.org/drawingml/2006/main}ea", {})
    ea.set("typeface", font)
    rpr.append(ea)


def txt(s, text, x, y, w, h, size=11, bold=False, color=INK,
        align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    box = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    for i, line in enumerate(str(text).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = line
        _font(r, size, bold, color)
    return box


def box(s, x, y, w, h, text, fill=WHITE, line=LINE, color=INK, size=11, bold=False, radius=True):
    shape = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = Pt(0.9)
    shape.shadow.inherit = False
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.08)
    tf.margin_right = Inches(0.08)
    tf.margin_top = Inches(0.04)
    tf.margin_bottom = Inches(0.04)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    _font(r, size, bold, color)


def arrow(s, x, y, w, h, direction="right"):
    shape = s.shapes.add_shape(
        MSO_SHAPE.RIGHT_ARROW if direction == "right" else MSO_SHAPE.DOWN_ARROW,
        Inches(x), Inches(y), Inches(w), Inches(h),
    )
    shape.fill.solid(); shape.fill.fore_color.rgb = BLUE
    shape.line.fill.background(); shape.shadow.inherit = False


def group(s, x, y, w, h, label):
    shape = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.background()
    shape.line.color.rgb = LINE
    shape.line.width = Pt(1.1)
    shape.line.dash_style = 4  # dash
    shape.shadow.inherit = False
    txt(s, label, x + 0.15, y + 0.12, w - 0.3, 0.24, 8.5, True, BODY)


def main():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    s = prs.slides.add_slide(prs.slide_layouts[6])
    paper = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    paper.fill.solid(); paper.fill.fore_color.rgb = PAPER; paper.line.fill.background(); paper.shadow.inherit = False
    # 标题
    txt(s, "SYSTEM ARCHITECTURE", 0.55, 0.25, 5.0, 0.22, 9.5, True, BLUE)
    txt(s, "四层分工 + 一条可追溯链路", 0.55, 0.52, 8.5, 0.42, 22, True, INK)
    txt(s, "前端 / FastAPI / Nexent + MCP / data + knowledge", 0.55, 0.98, 8.0, 0.24, 9.5, False, BODY)
    # 三个层组
    group(s, 0.50, 1.45, 3.25, 4.35, "交互层 · web/")
    group(s, 4.05, 1.45, 4.25, 4.35, "服务层 · FastAPI api/")
    group(s, 8.60, 1.45, 4.15, 4.35, "智能体层 · Nexent")
    # UI
    box(s, 0.72, 1.92, 2.80, 0.62, "评审看板 / 上传解析", LIGHT, BLUE, DEEP, 9.5, True)
    box(s, 0.72, 2.70, 2.80, 0.62, "双栏对照 / 定位原文", LIGHT, BLUE, DEEP, 9.5, True)
    box(s, 0.72, 3.48, 2.80, 0.62, "报告中心 / docx · pdf", LIGHT, BLUE, DEEP, 9.5, True)
    box(s, 0.72, 4.26, 2.80, 0.62, "系统状态 / 数据管理", LIGHT, BLUE, DEEP, 9.5, True)
    # API
    box(s, 4.28, 1.92, 3.78, 0.55, "routes/ · review/service.py", LIGHT, BLUE, DEEP, 9.0, True)
    for i, (name, sub) in enumerate([
        ("parsers/", "docx / pdf / txt / OCR"),
        ("extract/", "8 字段 + 清单条目"),
        ("review/", "资格性三态 + 评分"),
        ("rules/ + checks/", "40 条规则 + 门控"),
        ("report/", "九章 docx / pdf"),
    ]):
        y = 2.62 + i * 0.56
        box(s, 4.28, y, 3.78, 0.46, f"{name}   {sub}", WHITE, LINE, INK, 7.8, False)
    # Agent
    box(s, 8.82, 1.92, 3.66, 0.72, "Nexent Agent\nmax_steps=15 · temperature=0", LIGHT, BLUE, DEEP, 8.8, True)
    box(s, 8.82, 2.82, 1.72, 0.72, "4 Skill\n规则/缺失/自检/摘要", WHITE, LINE, INK, 7.6, False)
    box(s, 10.72, 2.82, 1.76, 0.72, "8 MCP\n取数/定位/导出", WHITE, LINE, INK, 7.6, False)
    box(s, 8.82, 3.76, 3.66, 0.72, "知识库 rules-full.md\n40 条 · index_names 需替换", WHITE, LINE, INK, 7.8, False)
    box(s, 8.82, 4.72, 3.66, 0.62, "output: JSON + page/quote", LIGHT, BLUE, DEEP, 8.5, True)
    # 连接箭头
    arrow(s, 3.78, 3.28, 0.25, 0.26, "right")
    arrow(s, 8.32, 3.28, 0.25, 0.26, "right")
    arrow(s, 10.72, 3.56, 0.22, 0.22, "down")
    # 数据层
    group(s, 0.50, 5.98, 12.25, 1.05, "数据层 · data/ + knowledge/")
    for i, (name, sub) in enumerate([
        ("rules.yaml", "40 条规则"),
        ("scoring/*.yaml", "3 套细则"),
        ("samples/", "25 + N01–N10"),
        ("reports/", "docx / pdf"),
    ]):
        box(s, 0.72 + i * 2.98, 6.22, 2.72, 0.56, f"{name} ｜ {sub}", WHITE, LINE, INK, 7.6, False)
    # 返回箭头
    arrow(s, 1.95, 5.55, 0.22, 0.32, "up")
    txt(s, "MCP 调用 / 回写", 2.22, 5.58, 1.8, 0.20, 7.0, False, BODY)
    # 右侧注释
    txt(s, "确定性算分", 8.82, 5.62, 1.5, 0.20, 8.0, True, DEEP)
    txt(s, "模型只组织语言", 10.25, 5.62, 2.2, 0.20, 8.0, False, BODY)
    # 页脚
    txt(s, "位置由代码算 ｜ 判断有边界 ｜ 依据可回溯", 0.55, 7.18, 9.0, 0.18, 7.0, False, BODY)
    prs.core_properties.title = "招投标评审助手 · 架构图"
    prs.save(OUT_PPTX)
    print(OUT_PPTX)


if __name__ == "__main__":
    main()
