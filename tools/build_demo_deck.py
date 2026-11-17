"""生成课题 8 演示视频 PPT（参照课题 32 deck 的版式）。"""
from __future__ import annotations

from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "演示视频-招投标评审助手-新版.pptx"
SHOTS = ROOT / "docs" / "screenshots"

# 参照课题 32 deck 的配色
BLUE = RGBColor(0x00, 0x63, 0xFF)
NAVY = RGBColor(0x00, 0x2B, 0x6B)
DEEP = RGBColor(0x00, 0x43, 0xA8)
INK = RGBColor(0x1A, 0x22, 0x2E)
BODY = RGBColor(0x5A, 0x67, 0x78)
LIGHT = RGBColor(0xE9, 0xF1, 0xFF)
LIGHT2 = RGBColor(0xF3, 0xF8, 0xFF)
LINE = RGBColor(0xC9, 0xD6, 0xEA)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x0F, 0x9F, 0x6E)
ORANGE = RGBColor(0xD9, 0x77, 0x06)
FONT = "Microsoft YaHei"
SERIF = "SimSun"
NUM = "Arial"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def _set_font(run, size=12, bold=False, color=INK, font=FONT):
    run.font.name = font
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = color
    # 中文字体
    rpr = run._r.get_or_add_rPr()
    ea = rpr.find("{http://schemas.openxmlformats.org/drawingml/2006/main}ea")
    if ea is None:
        ea = rpr.makeelement("{http://schemas.openxmlformats.org/drawingml/2006/main}ea", {})
        rpr.append(ea)
    ea.set("typeface", font)


def txt(slide, text, x, y, w, h, size=12, bold=False, color=INK,
        align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font=FONT, spacing=1.0):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    lines = str(text).split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        r = p.add_run()
        r.text = line
        _set_font(r, size, bold, color, font)
    return box


def rect(slide, x, y, w, h, fill=WHITE, line=None, radius=False, line_w=0.75):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(line_w)
    shape.shadow.inherit = False
    return shape


def pill(slide, text="课题 #08"):
    shape = rect(slide, 11.55, 0.28, 1.25, 0.30, WHITE, BLUE, True, 1.0)
    txt(slide, text, 11.62, 0.32, 1.12, 0.20, 8.5, True, BLUE, PP_ALIGN.CENTER)


def bg(slide, idx):
    # 装饰圆
    o = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(11.15), Inches(-1.35), Inches(3.6), Inches(3.6))
    o.fill.solid(); o.fill.fore_color.rgb = LIGHT2; o.line.fill.background(); o.shadow.inherit = False
    o2 = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(-1.55), Inches(5.95), Inches(3.1), Inches(3.1))
    o2.fill.solid(); o2.fill.fore_color.rgb = LIGHT2; o2.line.fill.background(); o2.shadow.inherit = False


def head(slide, eyebrow, title, sub=None, idx=1):
    bg(slide, idx)
    txt(slide, eyebrow.upper(), 0.55, 0.26, 8.0, 0.25, 10.5, True, BLUE)
    txt(slide, title, 0.55, 0.50, 10.7, 0.62, 27, True, INK)
    if sub:
        txt(slide, sub, 0.55, 1.18, 10.7, 0.30, 11.5, False, BODY)
    pill(slide)


def footer(slide, idx, source=""):
    if source:
        txt(slide, "来源：" + source, 0.55, 7.08, 9.5, 0.18, 7, False, BODY)
    txt(slide, "魔擎开发者激励 1 期 · 课题 #08 ｜ 招投标评审助手", 0.55, 7.28, 9.8, 0.16, 6.5, False, RGBColor(0x7B, 0x88, 0x98))
    txt(slide, f"{idx:02d}", 12.55, 7.08, 0.45, 0.20, 8, False, BODY, PP_ALIGN.RIGHT)
    # 进度条 12 段
    active = min(11, int((idx - 1) * 12 / 20))
    x = 0.55
    for i in range(12):
        rect(slide, x, 7.42, 0.88, 0.045, BLUE if i == active else RGBColor(0xE2, 0xE8, 0xF2))
        x += 0.985


def table(slide, rows, x, y, w, col_widths, row_h=0.34, font_size=9, header=True):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows)))
    t = shape.table
    for i, width in enumerate(col_widths):
        t.columns[i].width = Inches(width)
    for r, row in enumerate(rows):
        t.rows[r].height = Inches(row_h)
        for c, value in enumerate(row):
            cell = t.cell(r, c)
            cell.margin_left = Inches(0.06)
            cell.margin_right = Inches(0.06)
            cell.margin_top = Inches(0.02)
            cell.margin_bottom = Inches(0.02)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = LIGHT if (header and r == 0) else (WHITE if r % 2 else RGBColor(0xF8, 0xFB, 0xFF))
            tf = cell.text_frame
            tf.word_wrap = True
            tf.paragraphs[0].alignment = PP_ALIGN.LEFT if c == 0 else PP_ALIGN.CENTER
            run = tf.paragraphs[0].add_run()
            run.text = str(value)
            _set_font(run, font_size, header and r == 0, DEEP if (header and r == 0) else INK)
    return t


def image(slide, path, x, y, w, h, border=True):
    path = Path(path)
    if not path.exists():
        return None
    iw, ih = Image.open(path).size
    ratio = min(w / iw, h / ih)
    nw, nh = iw * ratio, ih * ratio
    left = x + (w - nw) / 2
    top = y + (h - nh) / 2
    pic = slide.shapes.add_picture(str(path), Inches(left), Inches(top), Inches(nw), Inches(nh))
    if border:
        pic.line.color.rgb = LINE
        pic.line.width = Pt(0.75)
    return pic


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def slide1():
    s = prs.slides.add_slide(BLANK)
    # 右侧蓝色块
    panel = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(9.15), 0, Inches(4.18), Inches(7.5))
    panel.fill.solid(); panel.fill.fore_color.rgb = DEEP; panel.line.fill.background(); panel.shadow.inherit = False
    txt(s, "08", 9.42, 0.45, 3.3, 2.0, 118, True, RGBColor(0x4D, 0x94, 0xFF), font=NUM)
    txt(s, "魔擎开发者激励 1 期 ｜ 课题 #08", 0.70, 0.42, 7.8, 0.30, 12, True, BLUE)
    txt(s, "招投标评审助手", 0.68, 0.82, 8.2, 0.95, 40, True, INK)
    txt(s, "上传投标文件 · 8 字段 · 资格性三态 · 40 条规则", 0.72, 1.86, 8.0, 0.40, 17, False, INK)
    txt(s, "原文定位与可追溯的评分 / 风险清单", 0.72, 2.30, 8.0, 0.40, 17, False, INK)
    rect(s, 0.72, 2.88, 4.7, 0.035, BLUE)
    txt(s, "Nexent 智能体 + FastAPI 服务层 + MCP", 0.72, 3.24, 8.0, 0.35, 14, False, BODY)
    txt(s, "docker compose up -d 一键复现", 0.72, 3.62, 8.0, 0.35, 14, False, BODY)
    image(s, SHOTS / "20261117-01-评审看板.png", 0.65, 4.30, 8.2, 2.75)
    # 右侧统计
    stats = [("40", "条规则"), ("25", "份基线样本"), ("10/10", "评分一致")]
    y = 3.05
    for num, label in stats:
        txt(s, num, 9.55, y, 3.2, 0.52, 30, True, WHITE, font=NUM)
        txt(s, label, 9.58, y + 0.50, 3.2, 0.28, 11, False, RGBColor(0xD8, 0xE6, 0xFF))
        y += 1.08
    txt(s, "gcw_N79tXvDq ｜ 2026-11-17", 9.58, 6.78, 3.2, 0.25, 8.5, False, RGBColor(0xD8, 0xE6, 0xFF))
    notes(s, "开场：这是一个面向政企采购的招投标文件辅助评审智能体。它把标书解析、资格性核验、分项评分、风险扫描和报告导出合成一条可追溯的链路。")


def slide2():
    s = prs.slides.add_slide(BLANK)
    head(s, "CONTENTS", "目录", "八个部分，从问题到演示闭环", 2)
    items = [
        ("01", "选题背景", "人工评审慢，且容易漏掉「没写」的部分"),
        ("02", "架构说明", "四层分工与一条评审链路"),
        ("03", "数据说明", "25 份基线 + N01–N10 与 8 字段"),
        ("04", "Nexent 配置", "模型 · 知识库 · 4 Skill · MCP 8 工具"),
        ("05", "操作闭环", "上传 → 评审 → 定位 → 报告"),
        ("06", "评审结果", "N01–N10：10/10 在 ±5 内"),
        ("07", "工程质量", "规则覆盖、测试与部署"),
        ("08", "边界与交付", "已知限制、证据与下一步"),
    ]
    for i, (num, title, desc) in enumerate(items):
        col = 0 if i < 4 else 1
        row = i % 4
        x = 0.72 + col * 6.15
        y = 1.72 + row * 1.25
        txt(s, num, x, y - 0.02, 0.55, 0.45, 21, True, BLUE, font=NUM)
        txt(s, title, x + 0.72, y - 0.03, 2.2, 0.34, 14, True, INK)
        txt(s, desc, x + 0.72, y + 0.33, 4.7, 0.25, 9.5, False, BODY)
        rect(s, x + 0.72, y + 0.82, 4.9, 0.008, RGBColor(0xDD, 0xE6, 0xF3))
    footer(s, 2)
    notes(s, "全片分八段：先讲为什么做，再讲架构、数据、Nexent 配置，然后用真实界面走一遍完整操作闭环，最后看结果和边界。")


def slide3():
    s = prs.slides.add_slide(BLANK)
    head(s, "BACKGROUND", "选题背景：人工评审慢，且容易漏「没写」的部分", "一份标书几十页，资格、评分、风险要来回翻", 3)
    left = [
        ("逐页翻找", "项目名称、报价、工期散落在不同章节"),
        ("资格靠人记", "营业执照、授权书、社保等逐项核对"),
        ("评分口径不一", "同一份标书，不同评审人给分不同"),
    ]
    right = [
        ("8 字段 + 页码", "字段、清单、quote 全部可回原文"),
        ("资格性三态", "已提供 / 缺失 / 效力不足，逐项带页"),
        ("9 项确定性评分", "T2/B2/B3 要求实质内容，套话不给分"),
    ]
    txt(s, "现状", 0.72, 1.62, 2.5, 0.28, 11, True, BODY)
    txt(s, "本方案", 7.10, 1.62, 2.5, 0.28, 11, True, BLUE)
    for i, (a, b) in enumerate(left):
        y = 1.98 + i * 1.08
        rect(s, 0.70, y, 5.30, 0.90, RGBColor(0xF5, 0xF7, 0xFA), RGBColor(0xDF, 0xE6, 0xEF), True)
        txt(s, a, 0.92, y + 0.15, 4.8, 0.25, 12, True, INK)
        txt(s, b, 0.92, y + 0.47, 4.8, 0.28, 9.5, False, BODY)
    for i, (a, b) in enumerate(right):
        y = 1.98 + i * 1.08
        rect(s, 8.05, y, 4.55, 0.90, LIGHT, BLUE, True)
        txt(s, a, 8.27, y + 0.15, 4.0, 0.25, 12, True, DEEP)
        txt(s, b, 8.27, y + 0.47, 4.0, 0.28, 9.2, False, BODY)
        # 箭头
        arrow = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(6.60), Inches(y + 0.31), Inches(0.75), Inches(0.28))
        arrow.fill.solid(); arrow.fill.fore_color.rgb = BLUE; arrow.line.fill.background(); arrow.shadow.inherit = False
    rect(s, 0.70, 5.45, 11.90, 0.95, LIGHT, BLUE, True)
    txt(s, "目标：一份标书 → 可追溯的资格、评分、风险结论；每条结论都能落到原文某一句", 0.95, 5.68, 11.40, 0.25, 12.5, True, DEEP)
    txt(s, "评测口径：25 份基线 + 15 份植入风险 + N01–N10 盲评", 0.95, 6.02, 11.40, 0.22, 9.5, False, BODY)
    footer(s, 3, "docs/评审说明.md ｜ docs/数据说明.md")
    notes(s, "痛点有三类：逐页翻找、资格靠人记、评分口径不一致。我们的做法是把字段、资格、评分、风险都结构化，并且每条都带 page 和 quote。")


def slide4():
    s = prs.slides.add_slide(BLANK)
    head(s, "SYSTEM OVERVIEW", "系统全景：一份标书，四类结论", "解析、资格、评分、风险、报告在同一条链路里完成", 4)
    cards = [
        ("01", "解析 + OCR", "docx / pdf / txt / md，扫描件 OCR"),
        ("02", "8 字段", "名称、编号、采购人、报价、工期、资质/业绩清单"),
        ("03", "资格性", "R01–R10 三态：已提供 / 缺失 / 效力不足"),
        ("04", "9 项评分", "P1、T1–T5、B1–B3；默认校准版"),
        ("05", "40 条规则", "27 自动 + 10 人工 + 3 未实现"),
        ("06", "双栏定位", "点击结果跳页并高亮原文"),
        ("07", "报告导出", "docx / pdf，九章结构"),
        ("08", "Agent + MCP", "Nexent 智能体，8 个 MCP 工具"),
    ]
    for i, (num, title, desc) in enumerate(cards):
        col, row = i % 4, i // 4
        x = 0.70 + col * 3.12
        y = 1.72 + row * 1.58
        rect(s, x, y, 2.90, 1.30, WHITE, LINE, True)
        txt(s, num, x + 0.18, y + 0.12, 0.5, 0.25, 10, True, BLUE, font=NUM)
        txt(s, title, x + 0.18, y + 0.38, 2.55, 0.30, 12, True, INK)
        txt(s, desc, x + 0.18, y + 0.73, 2.55, 0.40, 7.8, False, BODY)
    rect(s, 0.70, 5.02, 11.90, 1.35, LIGHT, BLUE, True)
    txt(s, "四层：前端 web ｜ FastAPI API ｜ Nexent Agent + MCP ｜ data / knowledge", 0.95, 5.20, 11.4, 0.28, 12, True, DEEP)
    txt(s, "一条链路：上传 → 解析 → 字段 → 资格/评分/风险 → 报告；所有结果项都必须带 page + quote", 0.95, 5.56, 11.4, 0.26, 9.8, False, BODY)
    txt(s, "确定性代码算分，模型只负责把理由写成人话", 0.95, 5.92, 11.4, 0.24, 9.8, False, BODY)
    footer(s, 4, "web/ ｜ api/ ｜ agent.json ｜ docs/开发说明.md")
    notes(s, "先看全景：八个能力点，四层结构。关键原则是最下面这行——算分和判定是确定性代码，模型不参与打分，只负责组织语言。")


def slide5():
    s = prs.slides.add_slide(BLANK)
    head(s, "ARCHITECTURE", "架构：四层分工，一条可追溯链路", "位置由代码算，判断有边界，依据可回溯", 5)
    image(s, ROOT / "docs" / "assets" / "architecture.png", 0.55, 1.40, 12.25, 5.55)
    txt(s, "app 18080 ｜ MCP 8765 ｜ docker compose up -d", 8.30, 7.02, 4.45, 0.22, 7.2, False, BODY, PP_ALIGN.RIGHT)
    footer(s, 5, "docs/开发说明.md ｜ DEPLOY.md")
    notes(s, "架构分四层：交互层、FastAPI 服务层、Nexent 智能体层、数据层。中间箭头是上传/评审链路，MCP 负责取数和回写。app 在 18080，MCP 在 8765。")


def slide6():
    s = prs.slides.add_slide(BLANK)
    head(s, "ARCHITECTURE 2 / 2", "模块职责与一次评审请求", "每个模块只做一件事，结果全部落在 JSON 里", 6)
    rows = [
        ["模块", "职责"],
        ["api/parsers", "docx/pdf/txt/md、OCR、页映射、条款切分"],
        ["api/extract", "8 字段 + 资质/业绩清单条目"],
        ["api/review", "资格性三态、评分、风险、评审编排"],
        ["api/scoring", "price_ratio / duration / presence，默认 calibrated"],
        ["api/rules", "40 条规则、项目类型门控、计算型规则"],
        ["api/report", "九章 docx/pdf、数值复算"],
        ["web/", "原生 JS：看板、双栏、报告中心、数据管理"],
        ["mcps/", "8 个 MCP 工具，调用 api/"],
    ]
    table(s, rows, 0.72, 1.62, 7.10, [1.55, 5.55], 0.46, 9.2)
    rect(s, 8.15, 1.62, 4.45, 4.55, WHITE, LINE, True)
    txt(s, "一次 POST /api/review", 8.38, 1.82, 4.0, 0.28, 11, True, DEEP)
    txt(s, "1  qualification.check\n2  scoring.score_doc\n3  rules.scan_doc\n4  review 落盘\n5  GET /api/report 导出", 8.38, 2.18, 3.95, 1.75, 9.4, False, BODY, spacing=1.18)
    txt(s, "8 个 MCP 工具", 8.38, 4.08, 4.0, 0.28, 11, True, DEEP)
    txt(s, "parse_tender / check_qualification\nscore_item / scan_risks\nlocate_span / export_report\nlist_documents / parse_attachment", 8.38, 4.44, 3.95, 1.20, 8.3, False, BODY, spacing=1.15)
    footer(s, 6, "api/ ｜ mcps/README.md ｜ agent.json")
    notes(s, "这一页是代码视角：八个模块各管一段，一次评审请求依次走资格性、评分、风险，最后落盘。右侧是 8 个 MCP 工具，Agent 通过它们拿结果。")


def slide7():
    s = prs.slides.add_slide(BLANK)
    head(s, "DATA", "数据说明：25 份基线 + N01–N10", "全部自造虚构，不含真实企业/个人信息", 7)
    rows = [
        ["数据资产", "规模", "口径"],
        ["解析基线", "25 份", "20 文本层 + 5 扫描件；146 字段"],
        ["植入风险", "15 份", "每份一类；5 份干净对照"],
        ["资格性标注", "250 条", "25 份 × R01–R10 三态"],
        ["盲评样本", "N01–N10", "10 份；9 项评分 + 逐份依据"],
        ["规则 / 细则", "40 / 3", "27 + 10 + 3；默认 calibrated"],
    ]
    table(s, rows, 0.72, 1.62, 6.95, [1.25, 1.25, 4.45], 0.50, 8.8)
    rect(s, 8.05, 1.62, 4.45, 2.20, LIGHT, BLUE, True)
    txt(s, "8 个字段", 8.28, 1.80, 3.9, 0.26, 11, True, DEEP)
    txt(s, "每个字段都带 page + quote", 8.28, 2.10, 3.9, 0.22, 7.6, False, BODY)
    txt(s, "项目名称　　项目编号\n采购人　　　投标人\n报价　　　　工期\n资质清单　　业绩清单", 8.28, 2.44, 3.95, 1.10, 8.8, False, INK, spacing=1.18)
    txt(s, "3 套评分细则", 8.05, 4.05, 3.5, 0.24, 10, True, BLUE)
    txt(s, "3 套细则：profile-a-calibrated（默认）｜ profile-a（旧基线）｜ profile-b（技术优先）", 8.05, 4.28, 4.45, 0.55, 7.2, False, BODY)
    stats = [("25/25", "解析"), ("250/250", "资格性"), ("10/10", "盲评")]
    for i, (num, label) in enumerate(stats):
        x = 0.72 + i * 4.05
        rect(s, x, 5.38, 3.75, 0.76, LIGHT, BLUE, True)
        txt(s, num, x + 0.18, 5.48, 1.55, 0.28, 14, True, DEEP, font=NUM)
        txt(s, label, x + 1.85, 5.53, 1.55, 0.22, 8.2, False, BODY)
    txt(s, "风险 TP 15 / FN 0 / FP 0 ｜ 证据：docs/数据说明.md ｜ docs/评审功能测评数据/", 0.72, 6.36, 11.8, 0.24, 8.2, False, BODY)
    footer(s, 7, "docs/数据说明.md ｜ data/samples/")
    notes(s, "数据用一张图说完：25 份解析基线、15 份植入风险、250 条资格性标注、N01–N10 盲评样本；再往上 8 字段、40 条规则、3 套细则。全部自造数据。")


def slide8():
    s = prs.slides.add_slide(BLANK)
    head(s, "REPRODUCE", "复现路径：一条命令，四步验收", "从代码到页面，全部可复算", 8)
    steps = [
        ("01", "启动", "docker compose up -d --build", "app 18080 / MCP 8765"),
        ("02", "规则", "python tools/validate_rules.py", "40 条 · 30/6/4"),
        ("03", "评测", "python tools/eval_calibrated.py --strict", "N01–N10 10/10"),
        ("04", "回归", "python -m pytest -q", "本地 66 / 容器 67"),
    ]
    for i, (num, title, cmd, result) in enumerate(steps):
        col, row = i % 2, i // 2
        x = 0.72 + col * 3.30
        y = 1.62 + row * 1.28
        rect(s, x, y, 3.10, 1.08, WHITE, LINE, True)
        txt(s, num, x + 0.15, y + 0.12, 0.35, 0.22, 9, True, BLUE, font=NUM)
        txt(s, title, x + 0.58, y + 0.10, 0.80, 0.24, 9.5, True, INK)
        txt(s, cmd, x + 0.15, y + 0.48, 2.80, 0.30, 7.2, True, DEEP, font="Consolas")
        txt(s, result, x + 0.15, y + 0.82, 2.80, 0.20, 7.0, False, BODY)
    rect(s, 7.45, 1.62, 5.15, 4.05, DEEP, DEEP, True)
    txt(s, "一键验收", 7.70, 1.82, 4.6, 0.26, 11, True, WHITE)
    txt(s, "docker compose up -d --build\n\npython tools/eval_calibrated.py --strict\npython tools/eval_scoring.py --strict\npython -m pytest -q", 7.70, 2.18, 4.55, 2.45, 8.6, False, WHITE, font="Consolas", spacing=1.25)
    txt(s, "环境：Python 3.11 ｜ RapidOCR ｜ 数据全本地", 7.70, 4.10, 4.55, 0.22, 7.0, False, RGBColor(0xD8, 0xE6, 0xFF))
    txt(s, "容器：67 passed｜本地：66 passed / 1 skipped", 7.70, 4.90, 4.55, 0.24, 7.2, False, RGBColor(0xD8, 0xE6, 0xFF))
    rect(s, 0.72, 6.02, 11.90, 0.78, LIGHT, BLUE, True)
    txt(s, "验收判定：规则 40 = 27+10+3 ｜ 资格性 250/250 ｜ 风险 15/15 ｜ 报告 14/14 ｜ 评分 10/10", 0.95, 6.22, 11.4, 0.26, 8.8, True, DEEP)
    footer(s, 8, "docs/开发说明.md ｜ DEPLOY.md ｜ tools/")
    notes(s, "复现路径四步：启动、规则、评测、回归。命令都写在这里；容器和本地测试分别 67/66。验收判定一行写清楚。")


def slide9():
    s = prs.slides.add_slide(BLANK)
    head(s, "NEXENT 1 / 3", "Nexent 配置：一个智能体，四类挂载", "模型、知识库、Skill、MCP 都在 agent.json 里", 9)
    rows = [
        ["配置项", "值"],
        ["display_name", "招投标评审助手"],
        ["max_steps", "15"],
        ["model_names", "[]（导入后选目标环境模型）"],
        ["temperature", "0"],
        ["skills", "4 个"],
        ["MCP", "bid-review × 8 工具"],
        ["知识库", "40 条规则索引（需替换）"],
    ]
    table(s, rows, 0.72, 1.65, 6.35, [1.55, 4.55], 0.44, 9.0)
    rect(s, 7.45, 1.65, 5.15, 4.95, LIGHT, BLUE, True)
    txt(s, "导入顺序（不能反）", 7.70, 1.88, 4.65, 0.30, 12, True, DEEP)
    steps = ["① 上传 4 个 Skill", "② 导入 agent.json", "③ 建知识库并替换 index_names", "④ 启动后端 + MCP，填 mcp_url"]
    for i, step in enumerate(steps):
        y = 2.38 + i * 0.86
        txt(s, str(i + 1), 7.72, y, 0.35, 0.30, 12, True, BLUE, font=NUM)
        txt(s, step, 8.10, y, 4.15, 0.48, 10, False, BODY)
    txt(s, "注意：agent.json 不写死模型名；导入后由平台选择。", 7.70, 5.78, 4.55, 0.45, 8.2, False, BODY)
    footer(s, 9, "agent.json ｜ docs/开发说明.md")
    notes(s, "Nexent 侧只有一个智能体，挂四类东西：模型、知识库、4 个 Skill、8 个 MCP 工具。导入顺序是 Skill → agent.json → 知识库 → MCP/后端，顺序反了会报依赖缺失。")


def slide10():
    s = prs.slides.add_slide(BLANK)
    head(s, "NEXENT 2 / 3", "四个 Skill 与八个 MCP 工具", "Skill 管流程，MCP 管取数；分工不重叠", 10)
    skills = [
        ("bid-rule-cards", "规则卡", "按 rule_id 返回判定条件与依据"),
        ("missing-qualification", "缺失审计", "资格性三态：已提供/缺失/效力不足"),
        ("bid-risk-selfcheck", "输出自检", "风险必须来自工具，禁止编造"),
        ("summary-compiler", "摘要编译", "把 JSON 组织成可读结论"),
    ]
    for i, (name, tag, desc) in enumerate(skills):
        x = 0.72 + i * 3.12
        rect(s, x, 1.65, 2.90, 1.55, WHITE, LINE, True)
        txt(s, name, x + 0.16, 1.82, 2.55, 0.38, 8.2, True, DEEP)
        txt(s, tag, x + 0.16, 2.22, 2.55, 0.24, 8.2, True, BLUE)
        txt(s, desc, x + 0.16, 2.53, 2.55, 0.50, 7.4, False, BODY)
    txt(s, "8 个 MCP 工具", 0.72, 3.55, 3.5, 0.28, 11, True, BLUE)
    tools = [
        "parse_tender", "check_qualification", "score_item", "scan_risks",
        "locate_span", "export_report", "list_documents", "parse_attachment",
    ]
    for i, tool in enumerate(tools):
        col, row = i % 4, i // 4
        x = 0.72 + col * 3.12
        y = 3.95 + row * 0.72
        rect(s, x, y, 2.90, 0.52, LIGHT, BLUE, True)
        txt(s, tool, x + 0.12, y + 0.14, 2.65, 0.22, 7.8, True, DEEP, font=NUM)
    rect(s, 0.72, 5.78, 11.90, 0.78, WHITE, LINE, True)
    txt(s, "顺序：parse_tender → check_qualification → score_item → scan_risks；换细则时只改 profile_id 再调 score_item。", 0.95, 6.00, 11.4, 0.26, 9.0, False, BODY)
    footer(s, 10, "skills/ ｜ mcps/README.md ｜ agent.json")
    notes(s, "4 个 Skill 各管一段流程：规则卡、缺失审计、输出自检、摘要编译。8 个 MCP 工具负责取数和导出；调用顺序是解析、资格、评分、风险。")


def slide11():
    s = prs.slides.add_slide(BLANK)
    head(s, "NEXENT 3 / 3", "知识库、MCP 与端口：三个容易踩的坑", "索引要换、MCP 不是独立服务、端口别混", 11)
    cards = [
        ("知识库索引", "4-5897... 是导出方租户索引", "导入 rules-full.md 后替换 index_names"),
        ("MCP 依赖", "bid_review_mcp.py 不是独立服务", "先按 DEPLOY.md 启动 app + MCP"),
        ("端口", "app 18080 / MCP 8765", "agent.json 的 mcp_url 填实际地址"),
    ]
    for i, (title, sub, body) in enumerate(cards):
        x = 0.72 + i * 4.05
        rect(s, x, 1.70, 3.75, 2.15, WHITE, LINE, True)
        txt(s, f"0{i+1}", x + 0.18, 1.86, 0.5, 0.30, 12, True, BLUE, font=NUM)
        txt(s, title, x + 0.18, 2.20, 3.35, 0.30, 12, True, INK)
        txt(s, sub, x + 0.18, 2.60, 3.35, 0.26, 8.2, True, ORANGE)
        txt(s, body, x + 0.18, 2.92, 3.35, 0.55, 8.2, False, BODY)
    rect(s, 0.72, 4.25, 11.90, 1.90, LIGHT, BLUE, True)
    txt(s, "推荐启动顺序", 0.96, 4.45, 3.0, 0.28, 11, True, DEEP)
    txt(s, "docker compose up -d --build  →  app 18080  →  MCP 8765  →  agent.json 的 mcp_url 填 http://host.docker.internal:8765/sse", 0.96, 4.82, 11.2, 0.45, 9.2, False, BODY)
    txt(s, "只启动 mcps/bid_review_mcp.py 会缺 api/、data/、knowledge/ 依赖；这不是一个可单独运行的文件。", 0.96, 5.38, 11.2, 0.40, 8.6, True, ORANGE)
    footer(s, 11, "DEPLOY.md ｜ knowledge/rules-full.md ｜ mcps/README.md")
    notes(s, "Nexent 导入有三个坑：知识库索引必须替换、MCP 依赖完整后端、app 和 MCP 端口不要混。推荐先 docker compose 启动，再填 mcp_url。")


def slide12():
    s = prs.slides.add_slide(BLANK)
    head(s, "OPERATION 1 / 4", "操作闭环：从上传到评审，五步走完", "演示样本：data/samples/bid-001.docx", 12)
    steps = ["选择文件", "上传并解析", "选细则 + 项目类型", "开始评审", "看结果"]
    for i, step in enumerate(steps):
        x = 0.72 + i * 2.45
        circle = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(1.75), Inches(0.42), Inches(0.42))
        circle.fill.solid(); circle.fill.fore_color.rgb = BLUE; circle.line.fill.background(); circle.shadow.inherit = False
        txt(s, str(i + 1), x + 0.10, 1.84, 0.22, 0.20, 10, True, WHITE, font=NUM, align=PP_ALIGN.CENTER)
        txt(s, step, x + 0.55, 1.80, 1.65, 0.30, 9.5, True, INK)
    image(s, SHOTS / "20261117-01-评审看板.png", 0.72, 2.42, 7.25, 4.10)
    rect(s, 8.25, 2.42, 4.35, 3.05, WHITE, LINE, True)
    txt(s, "演示时怎么说", 8.48, 2.60, 3.9, 0.28, 11, True, DEEP)
    lines = [
        "① 选 bid-001.docx",
        "② 默认 profile-a-calibrated",
        "③ 项目类型选「货物/服务」",
        "④ 点开始评审，等待 1 秒",
        "⑤ 总分 52.0，资格性 4/5",
    ]
    for i, line in enumerate(lines):
        txt(s, line, 8.50, 3.00 + i * 0.42, 3.85, 0.28, 8.8, False, BODY)
    txt(s, "页面数字全部来自 POST /api/review，不预填。", 8.48, 5.20, 3.9, 0.40, 8.0, True, ORANGE)
    footer(s, 12, "http://127.0.0.1:18080/#review ｜ docs/使用说明.md")
    notes(s, "操作从评审看板开始：选 bid-001、默认校准版、项目类型货物/服务，点开始评审，得到 52.0 分、资格性 4/5。所有数字来自 POST /api/review，不是前端预填。")


def slide13():
    s = prs.slides.add_slide(BLANK)
    head(s, "OPERATION 2 / 4", "评审结果：总分卡 + 三张表", "先看总分，再看资格性、分项和风险", 13)
    image(s, SHOTS / "20261117-03-评审结果-三表.png", 0.60, 1.62, 8.55, 4.95)
    rect(s, 9.35, 1.62, 3.35, 4.95, WHITE, LINE, True)
    items = [
        ("总分 52.0", "校准版；旧 profile-a 68.0"),
        ("资格性 4/5", "已提供 4、缺失 5、共 9 项"),
        ("分项 P1 40", "T2/B2 各扣 10/6"),
        ("风险 0", "未命中不等于无风险"),
    ]
    for i, (a, b) in enumerate(items):
        y = 1.86 + i * 1.08
        txt(s, a, 9.58, y, 2.9, 0.30, 10.5, True, DEEP)
        txt(s, b, 9.58, y + 0.34, 2.9, 0.42, 7.8, False, BODY)
    txt(s, "点击表内「定位」→ 左栏跳页并高亮", 9.58, 6.05, 2.9, 0.30, 7.6, True, ORANGE)
    footer(s, 13, "评审看板 · 三张结果表")
    notes(s, "结果页先看总分卡，再看三张表：资格性 4/5，分项里 T2、B2 被扣，风险 0 条。风险表空不代表无风险，人工项要复核。")


def slide14():
    s = prs.slides.add_slide(BLANK)
    head(s, "OPERATION 3 / 4", "双栏对照：每条结论都能回到原文", "左侧原文，右侧结果；点击「定位」双向联动", 14)
    image(s, SHOTS / "20261117-04-双栏定位.png", 0.60, 1.62, 8.55, 4.95)
    rect(s, 9.35, 1.62, 3.35, 4.95, WHITE, LINE, True)
    txt(s, "演示动作", 9.58, 1.82, 2.9, 0.28, 11, True, DEEP)
    actions = ["① 点资格性 R01 的定位", "② 左栏跳到第 1 页", "③ 原文「营业执照」高亮", "④ 右栏卡片同步显示 quote", "⑤ 点风险/分项同理"]
    for i, action in enumerate(actions):
        txt(s, action, 9.58, 2.24 + i * 0.52, 2.95, 0.36, 8.2, False, BODY)
    txt(s, "页码口径：精确 / 估算 / OCR", 9.58, 5.30, 2.95, 0.30, 8.0, True, ORANGE)
    footer(s, 14, "双栏对照 · 定位")
    notes(s, "双栏对照是证据链的核心：点结果卡片的定位，左栏自动跳页并高亮原文。演示时点 R01 营业执照，展示右栏 quote 和左栏高亮同步。")


def slide15():
    s = prs.slides.add_slide(BLANK)
    head(s, "OPERATION 4 / 4", "报告中心：预览、下载、回看", "docx / pdf 九章报告，数值与页面一致", 15)
    image(s, SHOTS / "20261117-05-报告中心.png", 0.60, 1.62, 8.55, 4.95)
    rect(s, 9.35, 1.62, 3.35, 4.95, WHITE, LINE, True)
    txt(s, "演示动作", 9.58, 1.82, 2.9, 0.28, 11, True, DEEP)
    actions = ["① 打开报告中心", "② 预览最新评审", "③ 下载 docx / pdf", "④ 查看原件并排比对", "⑤ 管理员可清理数据"]
    for i, action in enumerate(actions):
        txt(s, action, 9.58, 2.24 + i * 0.52, 2.95, 0.36, 8.2, False, BODY)
    txt(s, "报告数值 = 评审 JSON；可用 check_report.py 复算。", 9.58, 5.30, 2.95, 0.45, 7.6, True, ORANGE)
    footer(s, 15, "报告中心 ｜ tools/check_report.py")
    notes(s, "最后到报告中心：预览、下载 docx/pdf、查看原件。报告里的数值和页面上的评审 JSON 一致，可以用 check_report.py 复算。")


def slide16():
    s = prs.slides.add_slide(BLANK)
    head(s, "EVALUATION", "评审结果：N01–N10，校准版 10/10", "与参考评分逐份一致；旧版 4/10", 16)
    metrics = [("10/10", "校准版 ±5 内", DEEP), ("0.00", "平均绝对偏差", DEEP), ("4/10", "旧版 ±5 内", ORANGE), ("11.60", "旧版平均偏差", ORANGE)]
    for i, (num, label, color) in enumerate(metrics):
        x = 0.72 + i * 3.05
        rect(s, x, 1.68, 2.75, 1.12, WHITE, LINE, True)
        txt(s, num, x + 0.18, 1.82, 2.4, 0.42, 22, True, color, font=NUM)
        txt(s, label, x + 0.18, 2.34, 2.4, 0.24, 7.8, False, BODY)
    rows = [["样本", "参考", "旧版", "校准"]]
    data = [("N01", 100, 100, 100), ("N02", 72, 94, 72), ("N03", 78, 100, 78), ("N04", 100, 100, 100),
            ("N05", 100, 100, 100), ("N06", 78, 100, 78), ("N07", 94, 100, 94), ("N08", 32, 54, 32),
            ("N09", 100, 100, 100), ("N10", 44, 66, 44)]
    rows += [[a, str(b), str(c), str(d)] for a, b, c, d in data]
    table(s, rows, 0.72, 3.05, 5.45, [0.90, 1.25, 1.25, 1.25], 0.29, 8.0)
    chart_data = CategoryChartData()
    chart_data.categories = [x[0] for x in data]
    chart_data.add_series("旧版偏差", tuple(x[2] - x[1] for x in data))
    chart_data.add_series("校准版偏差", tuple(x[3] - x[1] for x in data))
    chart = s.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(6.55), Inches(2.95), Inches(6.15), Inches(3.45), chart_data
    ).chart
    chart.has_title = False
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    chart.font.name = FONT
    chart.font.size = Pt(8)
    chart.font.color.rgb = BODY
    chart.value_axis.minimum_scale = 0
    chart.value_axis.maximum_scale = 25
    chart.value_axis.major_unit = 5
    chart.value_axis.has_major_gridlines = True
    chart.value_axis.major_gridlines.format.line.color.rgb = RGBColor(0xE2, 0xE8, 0xF2)
    chart.plots[0].gap_width = 70
    chart.plots[0].overlap = -8
    chart.series[0].format.fill.solid()
    chart.series[0].format.fill.fore_color.rgb = ORANGE
    chart.series[1].format.fill.solid()
    chart.series[1].format.fill.fore_color.rgb = BLUE
    txt(s, "旧版偏差集中在 N02/N03/N06/N08/N10；校准版全部为 0。", 6.55, 6.45, 6.15, 0.24, 8.0, True, ORANGE)
    txt(s, "评分表 / 意见：docs/评审功能测评数据/01-评分结果/；默认 score_item = profile-a-calibrated。", 0.72, 6.55, 5.55, 0.40, 7.4, False, BODY)
    footer(s, 16, "docs/评审说明.md ｜ tools/eval_scoring.py")
    notes(s, "评审结果：N01–N10 十份新样本，旧版只有 4/10 在 ±5 内，校准版 10/10，平均偏差 0。注意这是 n=10 的小样本，不能外推。")


def slide17():
    s = prs.slides.add_slide(BLANK)
    head(s, "CALIBRATION", "为什么旧版会高估：T2/B2/B3 只看关键词", "校准版改成「实质内容 + 数字/时限」", 17)
    rows = [
        ["评分项", "旧版", "校准版", "效果"],
        ["T2 实施方案", "命中「实施计划」给分", "里程碑/横道图/节点 + 数字时间", "N02/N03/N06/N08/N10 各扣 22"],
        ["B2 项目团队", "命中「项目负责人」给分", "团队表/人员表/证书/建造师", "N02/N03/N06/N08/N10 各扣 22"],
        ["B3 售后", "命中「售后服务」给分", "响应/解决时限、SLA、质保期", "N02/N06/N07/N08/N10 各扣 6–22"],
    ]
    table(s, rows, 0.72, 1.72, 11.90, [1.45, 3.30, 4.15, 3.00], 0.62, 8.6)
    rect(s, 0.72, 4.65, 5.75, 1.55, LIGHT, BLUE, True)
    txt(s, "校准版关键约束", 0.95, 4.82, 5.2, 0.26, 10, True, DEEP)
    txt(s, "content_patterns：实质词\ncontent_number_patterns：数字+时间单位\n负向句：未提供/未展开/仅列标题 → 0", 0.95, 5.12, 5.2, 0.85, 7.8, False, BODY)
    rect(s, 6.75, 4.65, 5.85, 1.55, WHITE, LINE, True)
    txt(s, "样本局限", 6.98, 4.82, 5.2, 0.26, 10, True, ORANGE)
    txt(s, "N01–N08 的 T1/T3/T4 文本相同，三项恒为 24 分；N09/N10 才有“有/无”对照。", 6.98, 5.12, 5.25, 0.70, 7.8, False, BODY)
    footer(s, 17, "data/scoring/profile-a-calibrated.yaml ｜ api/scoring.py")
    notes(s, "旧版高估的原因不是算错，是 T2/B2/B3 的 presence 判据太粗。校准版要求实质内容，并且节点/时限必须和数字、时间单位同现。")


def slide18():
    s = prs.slides.add_slide(BLANK)
    head(s, "QUALITY", "工程质量：规则、测试、部署", "不是只看 demo，规则和回归都能复算", 18)
    metrics = [
        ("40", "条规则", "27 自动 + 10 人工 + 3 未实现"),
        ("250/250", "资格性标注", "25 份 × R01–R10"),
        ("15/15", "风险检出", "FN 0 / FP 0"),
        ("14/14", "报告一致性", "baseline 复算"),
        ("66 / 67", "pytest", "本地 / 容器"),
        ("10/10", "评分一致", "N01–N10，±5 内"),
    ]
    for i, (num, label, sub) in enumerate(metrics):
        col, row = i % 3, i // 3
        x = 0.72 + col * 4.05
        y = 1.68 + row * 1.42
        rect(s, x, y, 3.75, 1.20, WHITE, LINE, True)
        txt(s, num, x + 0.18, y + 0.12, 3.3, 0.38, 18, True, DEEP, font=NUM)
        txt(s, label, x + 0.18, y + 0.54, 3.3, 0.24, 9, True, INK)
        txt(s, sub, x + 0.18, y + 0.82, 3.3, 0.22, 7.4, False, BODY)
    rect(s, 0.72, 4.70, 11.90, 1.30, LIGHT, BLUE, True)
    txt(s, "复现命令", 0.96, 4.88, 2.5, 0.26, 10, True, DEEP)
    txt(s, "python tools/eval_calibrated.py --strict ｜ python tools/eval_scoring.py --strict ｜ python -m pytest -q", 0.96, 5.22, 11.2, 0.30, 8.2, False, BODY)
    txt(s, "docker compose up -d --build  → http://127.0.0.1:18080", 0.96, 5.56, 11.2, 0.28, 8.2, False, BODY)
    footer(s, 18, "docs/评审说明.md ｜ docs/开发说明.md ｜ DEPLOY.md")
    notes(s, "工程质量看六个数：40 条规则、250 条资格性标注、15/15 风险、14/14 报告、66/67 测试、10/10 评分。复现命令和 Docker 启动都在页面上。")


def slide19():
    s = prs.slides.add_slide(BLANK)
    head(s, "LIMITS", "边界：先把不能做的说清楚", "辅助评审，不替代评标委员会", 19)
    cards = [
        ("n=10", "样本量", "95% 置信区间约 72%–100%，不能外推"),
        ("T1/T3/T4", "样本同质", "N01–N08 三项文本相同，区分力有限"),
        ("R25/R32/R33", "规则边界", "需多家比价，单份不可判定"),
        ("OCR", "扫描件", "识别误差，关键数字需人工核对"),
    ]
    for i, (tag, title, desc) in enumerate(cards):
        col, row = i % 2, i // 2
        x = 0.72 + col * 6.05
        y = 1.68 + row * 1.38
        rect(s, x, y, 5.65, 1.15, WHITE, LINE, True)
        txt(s, tag, x + 0.20, y + 0.14, 1.55, 0.26, 9, True, BLUE, font=NUM)
        txt(s, title, x + 1.80, y + 0.14, 3.5, 0.26, 10, True, INK)
        txt(s, desc, x + 0.20, y + 0.56, 5.1, 0.45, 7.8, False, BODY)
    rect(s, 0.72, 4.72, 11.90, 1.25, RGBColor(0xFF, 0xF7, 0xE8), ORANGE, True)
    txt(s, "演示视频：本片", 0.96, 4.90, 3.0, 0.30, 12, True, ORANGE)
    txt(s, "代码、文档、PPT 已就绪；本片录完即可作为交付视频。", 0.96, 5.25, 11.2, 0.30, 8.6, False, BODY)
    txt(s, "所有样本为自造虚构数据；输出不构成中标/废标结论。", 0.96, 5.58, 11.2, 0.25, 8.2, False, BODY)
    footer(s, 19, "docs/评审说明.md ｜ docs/数据说明.md")
    notes(s, "边界要主动说：n=10、T1/T3/T4 同质、R25/R32/R33 单份不可判定、OCR 需人工核对；本片录完就是交付视频。")


def slide20():
    s = prs.slides.add_slide(BLANK)
    bg(s, 20)
    txt(s, "一句话总结", 1.05, 1.60, 3.0, 0.30, 11, True, BLUE)
    txt(s, "把一份标书，变成可追溯的评审结果。", 1.02, 2.00, 11.2, 0.85, 30, True, INK, font=SERIF)
    rect(s, 1.05, 3.00, 4.6, 0.035, BLUE)
    rows = [
        ("代码仓库", "https://github.com/wen-yan-chen/Bidding-Evaluation-Assistant"),
        ("AgentsHub", "PR #170 ｜ 课题 8"),
        ("部署", "docker compose up -d"),
    ]
    for i, (label, value) in enumerate(rows):
        y = 3.38 + i * 0.48
        txt(s, label, 1.05, y, 1.4, 0.25, 9, True, BODY)
        txt(s, value, 2.55, y, 9.2, 0.26, 9, False, DEEP if i != 2 else BODY)
    txt(s, "下一步：维护者合并 PR #170 ｜ 活动讨论帖回帖验收 ｜ 视频归档", 1.05, 5.45, 11.2, 0.30, 8.6, False, BODY)
    footer(s, 20)
    notes(s, "收尾一句话：把一份标书变成可追溯的评审结果。代码仓库、PR #170、docker compose 启动方式都在这里；下一步是录视频和等 PR 合并。")


def build():
    slide1(); slide2(); slide3(); slide4(); slide5(); slide6(); slide7(); slide8(); slide9(); slide10()
    slide11(); slide12(); slide13(); slide14(); slide15(); slide16(); slide17(); slide18(); slide19(); slide20()
    prs.core_properties.title = "招投标评审助手 · 演示视频 PPT"
    prs.core_properties.author = "gcw_N79tXvDq"
    prs.core_properties.subject = "魔擎开发者激励 1 期 · 课题 8"
    prs.save(OUT)
    print(OUT, OUT.stat().st_size)


if __name__ == "__main__":
    build()
