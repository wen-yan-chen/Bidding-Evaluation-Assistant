"""生成 N09/N10 两份追加新样本（不覆盖已评的 N01–N08）。"""
from __future__ import annotations

import zipfile
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

BASE = Path(__file__).resolve().parent
OUT = BASE / "新样本_S11-S18"
ZIP = BASE / "新样本盲评包_N09-N10.zip"

HEAD_FILL = PatternFill("solid", fgColor="1F4E79")
HEAD_FONT = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
BODY_FONT = Font(name="微软雅黑", size=10)
THIN = Side(style="thin", color="E2E8F0")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)

ITEMS = [
    ("P1", "投标报价", 40),
    ("T1", "技术方案完整性", 10),
    ("T2", "实施方案与进度计划", 10),
    ("T3", "质量保证措施", 8),
    ("T4", "应急与安全保障", 6),
    ("T5", "工期响应", 6),
    ("B1", "类似项目业绩", 8),
    ("B2", "项目团队配置", 6),
    ("B3", "售后服务承诺", 6),
]


def p(doc, text, bold=False):
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.bold = bold
    run.font.name = "宋体"
    run.font.size = Pt(10.5)


def table(doc, rows):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            t.cell(i, j).text = value


def header(doc, title, code, price, days):
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run(title)
    run.bold = True
    run.font.name = "宋体"
    run.font.size = Pt(16)
    p(doc, f"项目编号：{code}")
    p(doc, "采购人：示例市公共资源交易中心")
    p(doc, "投标人：示例数智科技有限公司")
    p(doc, f"投标报价：人民币 {price}")
    p(doc, f"工期：{days}")


def common(doc):
    p(doc, "一、投标函", True)
    p(doc, "我方已详细审阅招标文件，承诺按招标文件要求完成本项目，投标文件所附资料真实、准确、完整。")
    p(doc, "二、资格证明文件", True)
    p(doc, "营业执照：已提供；法定代表人授权书：已提供；财务状况报告：已提供。")


def make_n09():
    doc = Document()
    header(doc, "示例市政务服务协同平台项目", "OUT-2026-009", "1,500,000.00 元", "90 日历天")
    common(doc)
    p(doc, "三、技术响应", True)
    p(doc, "技术方案：提供总体技术路线、微服务架构、数据流程、接口规范与安全设计，并给出容灾方案。")
    p(doc, "实施方案与进度计划：", True)
    p(doc, "第 1 周完成需求确认与现场勘察；第 4 周完成核心模块开发；第 8 周完成联调；第 12 周上线试运行。关键节点为第 4 周、第 8 周、第 12 周。")
    p(doc, "质量保证措施：建立质量责任制，执行需求评审、代码审查、三级复核和交付前检查。")
    p(doc, "应急与安全保障：成立应急小组，提供故障分级、备份恢复、安全加固和 2 小时到场机制。")
    p(doc, "四、商务响应", True)
    p(doc, "类似项目业绩：提供同类政务平台项目 2 项（示例市政务云一期 98 万元、示例区数据治理 76 万元）。")
    p(doc, "项目团队配置：", True)
    p(doc, "项目管理机构：项目经理 1 名（二级注册建造师），技术负责人 1 名（高级职称），实施人员 4 名（附职称证书）。")
    p(doc, "售后服务承诺：", True)
    p(doc, "一般故障 2 小时内响应、8 小时内解决；重大故障 1 小时内响应、24 小时内恢复；SLA 不低于 99.5%。")
    p(doc, "五、报价明细", True)
    table(doc, [
        ["序号", "费用项", "金额（元）"],
        ["1", "软件开发费", "700,000.00"],
        ["2", "实施部署费", "400,000.00"],
        ["3", "培训与文档费", "250,000.00"],
        ["4", "一年运维服务费", "150,000.00"],
        ["合计", "", "1,500,000.00"],
    ])
    p(doc, "注：本文件为自造虚构样本，仅用于学生比赛评审测试。")
    doc.save(OUT / "N09.docx")


def make_n10():
    doc = Document()
    header(doc, "示例区政务数据治理项目", "OUT-2026-010", "1,950,000.00 元", "120 日历天")
    common(doc)
    p(doc, "三、技术响应", True)
    p(doc, "实施方案与进度计划：", True)
    p(doc, "我方将按工期安排组织施工，确保按期完成。")
    p(doc, "质量保证措施：建立质量责任制，执行三级复核与交付前检查。")
    p(doc, "四、商务响应", True)
    p(doc, "类似项目业绩：提供同类政务数据项目 2 项（示例市数据共享 120 万元、示例区数据治理 80 万元）。")
    p(doc, "项目团队配置：", True)
    p(doc, "项目经理持证上岗，不擅自更换项目负责人。")
    p(doc, "售后服务承诺：", True)
    p(doc, "7×24 小时售后响应。")
    p(doc, "五、报价明细", True)
    table(doc, [
        ["序号", "费用项", "金额（元）"],
        ["1", "软件开发费", "1,200,000.00"],
        ["2", "实施部署费", "400,000.00"],
        ["3", "培训与文档费", "200,000.00"],
        ["4", "一年运维服务费", "150,000.00"],
        ["合计", "", "1,950,000.00"],
    ])
    p(doc, "注：本文件为自造虚构样本，仅用于学生比赛评审测试。")
    doc.save(OUT / "N10.docx")


def make_workbook():
    wb = Workbook()
    ws = wb.active
    ws.title = "评分表"
    headers = ["样本"] + [f"{iid} {name}（{score}分）" for iid, name, score in ITEMS] + ["总分", "备注"]
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = HEAD_FILL
        cell.font = HEAD_FONT
        cell.alignment = CENTER
        cell.border = BORDER
    for idx, sid in enumerate(("N09", "N10"), start=2):
        ws.cell(row=idx, column=1, value=sid).alignment = CENTER
        for c in range(1, len(headers) + 1):
            cell = ws.cell(row=idx, column=c)
            cell.font = BODY_FONT
            cell.border = BORDER
            cell.alignment = CENTER if c < 11 else LEFT
        ws.cell(row=idx, column=11, value=f"=SUM(B{idx}:J{idx})").font = Font(name="微软雅黑", size=10, bold=True)
        ws.cell(row=idx, column=11).border = BORDER
    for i, width in enumerate([8] + [9] * 9 + [9, 28], start=1):
        ws.column_dimensions[chr(64 + i)].width = width
    for col, (_, _, max_score) in enumerate(ITEMS, start=2):
        dv = DataValidation(type="decimal", operator="between", formula1="0", formula2=str(max_score),
                            allow_blank=True, showErrorMessage=True, errorTitle="分值超范围",
                            error=f"本项 0–{max_score} 分")
        ws.add_data_validation(dv)
        dv.add(f"{chr(64 + col)}2:{chr(64 + col)}3")
    ws2 = wb.create_sheet("说明")
    ws2.column_dimensions["A"].width = 100
    for i, text in enumerate([
        "招投标评审助手 · 追加新样本 N09–N10",
        "请按同一套 9 项、100 分细则独立评分，约 15–20 分钟。",
        "样本为自造虚构数据，仅用于学生比赛报告；不需要安装软件。",
        "只需要回传本评分表；备注可选。",
    ], start=1):
        cell = ws2.cell(row=i, column=1, value=text)
        cell.font = HEAD_FONT if i == 1 else BODY_FONT
    wb.save(OUT / "新样本评分表_N09-N10.xlsx")


def make_instructions():
    doc = Document()
    para = doc.add_paragraph()
    run = para.add_run("追加新样本盲评说明（N09–N10）")
    run.bold = True
    run.font.name = "宋体"
    run.font.size = Pt(16)
    for text in [
        "老师您好：",
        "这是两份追加的新样本 N09/N10，用于补齐正式验收的样本量；与之前 8 份不重复。",
        "请按同一套 9 项、100 分细则独立打分，约 15–20 分钟；不需要安装软件。",
        "样本为自造虚构数据，不含真实企业/个人信息；只用于学生比赛报告，可匿名/致谢。",
        "谢谢您！",
    ]:
        doc.add_paragraph(text)
    doc.save(OUT / "00-追加新样本盲评说明_N09-N10.docx")


def main():
    make_n09()
    make_n10()
    make_workbook()
    make_instructions()
    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in ("N09.docx", "N10.docx", "新样本评分表_N09-N10.xlsx", "00-追加新样本盲评说明_N09-N10.docx"):
            zf.write(OUT / name, name)
    print("written", ZIP, ZIP.stat().st_size)


if __name__ == "__main__":
    main()
