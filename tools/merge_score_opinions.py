"""合并 N01-N08 与 N09-N10 评分意见为一份 N01-N10。"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BASE = Path(__file__).resolve().parent.parent / "docs" / "评审功能测评数据" / "01-评分重评"
OUT = BASE / "评分意见_N01-N10.docx"

ITEMS = [
    ("N01", 40, 10, 10, 8, 6, 6, 8, 6, 6, 100),
    ("N02", 40, 10, 0, 8, 6, 0, 8, 0, 0, 72),
    ("N03", 40, 10, 0, 8, 6, 6, 8, 0, 0, 78),
    ("N04", 40, 10, 10, 8, 6, 6, 8, 6, 6, 100),
    ("N05", 40, 10, 10, 8, 6, 6, 8, 6, 6, 100),
    ("N06", 40, 10, 0, 8, 6, 6, 8, 0, 0, 78),
    ("N07", 40, 10, 10, 8, 6, 6, 8, 6, 0, 94),
    ("N08", 0, 10, 0, 8, 6, 0, 8, 0, 0, 32),
    ("N09", 40, 10, 10, 8, 6, 6, 8, 6, 6, 100),
    ("N10", 28, 0, 0, 8, 0, 0, 8, 0, 0, 44),
]

DETAILS = [
    ("N01（100）", "报价 118 万，比值 0.59，P1 满档；进度写到“第 1 周需求确认、第 3 周到货、第 6 周上线”，有节点数字；团队写明项目经理、技术负责人及 3 名实施人员并注明证书；售后给出“一般故障 2 小时响应/8 小时解决、重大故障 1 小时响应/24 小时恢复”，四项要素齐备。九项均有实质内容。"),
    ("N02（72）", "报价 96 万，P1 满档；T2、B2 两节均为“本章节仅列标题，未展开/未提供”，记 0；工期写 120 日历天，超过 108 天，T5 记 0；售后只有“7×24 小时故障受理”，无响应/解决时限、无 SLA 与质保期，按 B3 严格口径记 0。"),
    ("N03（78）", "报价 105 万，P1 满档；T2、B2、B3 三节都只有套话——“我方将按工期安排组织施工，确保按期完成”“项目经理持证上岗，不擅自更换项目负责人”“我方承诺响应时限短，售后服务网络完善”——没有周次、没有人员表或证书、没有具体时限，三项记 0；工期 90 天，T5 满分；其余四项为实质内容。"),
    ("N04（100）", "报价 88 万，P1 满档；进度写“30 天内完成需求与设计、第 8 周上线试运行”；团队“项目经理、技术负责人、实施人员共 5 人，附职称证书”；售后“2 小时响应、8 小时解决”，九项齐备。"),
    ("N05（100）", "报价 142 万，比值 0.71，P1 满档；进度以横道图与关键路径给出第 2/5/9 周节点；团队写明注册建造师与高级职称证书；售后“4 小时到场，SLA 不低于 99.5%”，承诺具体可考核。"),
    ("N06（78）", "报价 76 万，P1 满档；T2、B2 为“仅列标题”，记 0；售后“7×24 小时售后响应”只有服务时段、没有具体时限，按 B3 严格口径记 0；工期 90 天满分。"),
    ("N07（94）", "报价 130 万，P1 满档；进度给里程碑（第 4 周接口、第 8 周联调、第 10 周上线）；团队有项目经理及附件人员表；售后一节写“仅列标题，未提供具体服务承诺”，B3 记 0，扣 6 分。"),
    ("N08（32）", "报价 235 万，超限价 200 万，P1 记 0；工期 120 天，T5 记 0；T2、B2、B3 三节均仅列标题；T1、T3、T4、B1 为实质内容，合计 32 分。"),
    ("N09（100）", "报价 150 万，比值 0.75，P1 满档；技术方案给到技术路线、微服务架构、数据流程、接口规范、安全设计并含容灾方案；进度写到第 1/4/8/12 周并点明关键节点，第 12 周上线约 84 天、在 90 天要求内；质量措施有需求评审、代码审查、三级复核；应急有应急小组、故障分级、备份恢复与 2 小时到场；业绩 2 项并附合同金额；团队 5 人（项目经理二级建造师、技术负责人高级职称、实施 4 人附证书）；售后 2 小时响应/8 小时解决、重大故障 1 小时/24 小时、SLA 不低于 99.5%，四项要素齐备。"),
    ("N10（44）", "报价 195 万，比值 0.975，落在 0.97–1.00 档，P1 记 28；文件没有“技术方案”一节，T1 记 0；进度只有“我方将按工期安排组织施工，确保按期完成”，T2 记 0；质量措施写“建立质量责任制，执行三级复核与交付前检查”，T3 得 8；全文没有“应急与安全保障”一节，T4 记 0；工期 120 日历天，超 108 天，T5 记 0；业绩 2 项附金额，B1 得 8；团队只有“项目经理持证上岗，不擅自更换项目负责人”，B2 记 0；售后只有“7×24 小时售后响应”，B3 记 0。"),
]


def set_font(run, size=10.5, bold=False, color=None):
    run.font.name = "宋体"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)


def para(doc, text, size=10.5, bold=False, color=None, after=6, align=None):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.25
    set_font(p.add_run(text), size, bold, color)
    return p


def heading(doc, text, level=1):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10 if level == 1 else 7)
    p.paragraph_format.space_after = Pt(4)
    set_font(p.add_run(text), 14 if level == 1 else 11.5, True, (0x12, 0x3B, 0x5D))
    return p


def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def table(doc, rows):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            cell = t.cell(i, j)
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(str(value))
            set_font(run, 8.5, i == 0, (255, 255, 255) if i == 0 else None)
            if i == 0:
                shade(cell, "1F5C7A")
    for row in t.rows:
        row.height = Cm(0.62)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def main() -> int:
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(2.0)
    sec.left_margin = Cm(2.2)
    sec.right_margin = Cm(2.2)
    doc.styles["Normal"].font.name = "宋体"
    doc.styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

    para(doc, "招投标辅助评审 · 参考评分意见（N01–N10）", 18, True, (0x12, 0x3B, 0x5D), 6, WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, "重评版 · 2026-11-17 · B3 口径确认后｜9 项 100 分｜限价 2,000,000.00 元｜工期 90 日历天",
         9.5, False, (0x4A, 0x65, 0x72), 14, WD_ALIGN_PARAGRAPH.CENTER)

    heading(doc, "一、评分口径")
    para(doc, "只依据样本原文判断，不参考系统分数；9 个评分项按细则给定档位取值，不设中间档。")
    for text in [
        "“有/无”类各项（T1–T4、B1–B3），以是否给出可核查的实质内容为准。仅写节标题、“本章节仅列标题，未展开/未提供”，或只有表态句（“将按工期安排组织施工”“响应时限短”），一律记 0；写出具体周次、人员、证书、时限等，才记满分。",
        "B3 售后服务承诺采用可考核口径：须给出响应时限、解决时限、SLA 或质保期之一；只写“7×24 小时受理/响应”这种服务时段、没有可考核的时限约定，记 0。这样 B3 与 T2、B2 的判法一致，都是看有没有能落到纸面的承诺，而不是看有没有出现关键词。",
        "报价以投标函载明的投标报价为准，P1 按“报价÷2,000,000”对档；工期以投标函载明的日历天数计，91–108 天记 4 分、超过 108 天记 0 分。",
    ]:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.2
        set_font(p.add_run(text), 9.8)

    heading(doc, "二、总分")
    para(doc, "10 份中 4 份满分（N01、N04、N05、N09），N07 94 分，N03 与 N06 各 78 分，N02 72 分，N10 44 分，N08 32 分。")

    heading(doc, "三、逐份依据")
    for title, text in DETAILS:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.2
        set_font(p.add_run(title + "　"), 10, True, (0x1F, 0x5C, 0x7A))
        set_font(p.add_run(text), 9.8)

    heading(doc, "四、材料与样本层面")
    for text in [
        "报价明细：N02–N08 已按投标函报价重算三项明细，合计与投标报价一致；N09/N10 生成时即一致。评分仍以投标函报价为准。",
        "T1/T3/T4 同质化：N01–N08 的 T1/T3/T4 原文相同，恒为 24 分，对这 8 份没有区分力；N09/N10 已让 T1/T4 出现“有/无”对照，但样本量仍小。",
        "T5 档位：N02、N08 报 120 天，超过 108 天记 0，与“完全不写工期”同分；若希望体现响应态度差异，需在 108 天以上再设一档。",
        "价格档：除 N08 超限价 0 分、N10 为 28 分外，其余 8 份都落在 ≤0.90 的 40 分档，价格分仍未充分拉开。",
    ]:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.2
        set_font(p.add_run(text), 9.8)

    heading(doc, "五、重评与统计口径")
    para(doc, "B3 口径统一后，N02、N06 的 B3 由 6 改 0，总分分别由 78/84 改为 72/78；其余 8 份分数不变。只采用本版 N01–N10 的分数，初评不再作为依据。")
    para(doc, "10 份为唯一样本；若两位评审人都评，标注条数是 20 条，但样本数仍是 10 份，刚够正式要求的下限（10–15 份）。10 份均由同一套生成模板产出，段落结构、句式高度相似，真实标书的长篇叙述、附件、表格混排仍未覆盖。")

    heading(doc, "六、结论")
    para(doc, "10 份的分数梯度比 8 份那批更开：4 份满分，N07 94，N03/N06 78，N02 72，N10 44，N08 32。差异集中在两处：一是“仅列标题/套话”与“实质内容”的区分；二是价格与工期两个硬性档位。报告里引用本版分数，并保留“10 份小样本、不能外推”的限制。")

    heading(doc, "七、10 份分值表")
    table(doc, [["样本", "P1", "T1", "T2", "T3", "T4", "T5", "B1", "B2", "B3", "总分"]] + [[str(v) for v in row] for row in ITEMS])

    doc.save(OUT)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
