"""生成 8 份 out-of-sample 合成样本（不纳入 25 份基线），供老师独立评分。"""
from __future__ import annotations

import csv
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
ZIP = BASE / "新样本盲评包_S11-S18.zip"

HEAD_FILL = PatternFill("solid", fgColor="1F4E79")
HEAD_FONT = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
BODY_FONT = Font(name="微软雅黑", size=10)
THIN = Side(style="thin", color="D9E2F3")
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

# 内容只用于生成样本；不是评分答案，评分表由老师独立填写。
SAMPLES = {
    "N01": {
        "title": "示例市政务云平台五期设备采购项目",
        "code": "OUT-2026-001",
        "price": "1,180,000.00 元",
        "days": "90 日历天",
        "full": True,
        "progress": "第 1 周完成需求确认，第 3 周完成设备到货，第 6 周完成部署上线；关键节点为第 3 周、第 6 周。",
        "team": "项目管理机构：项目经理 1 名（二级注册建造师），技术负责人 1 名（高级职称），实施人员 3 名（持职称证书）。",
        "service": "一般故障 2 小时内响应、8 小时内解决；重大故障 1 小时内响应、24 小时内恢复。",
    },
    "N02": {
        "title": "示例区数据治理平台采购项目",
        "code": "OUT-2026-002",
        "price": "960,000.00 元",
        "days": "120 日历天",
        "full": False,
        "progress": "",
        "team": "",
        "service": "7×24 小时故障受理。",
    },
    "N03": {
        "title": "示例市统一身份认证平台运维项目",
        "code": "OUT-2026-003",
        "price": "1,050,000.00 元",
        "days": "90 日历天",
        "full": False,
        "progress": "我方将按工期安排组织施工，确保按期完成。",
        "team": "项目经理持证上岗，不擅自更换项目负责人。",
        "service": "我方承诺响应时限短，售后服务网络完善。",
    },
    "N04": {
        "title": "示例市公共信用信息平台二期项目",
        "code": "OUT-2026-004",
        "price": "880,000.00 元",
        "days": "90 日历天",
        "full": False,
        "progress": "进度安排：30 天内完成需求与设计，第 8 周完成上线试运行。",
        "team": "项目管理机构及人员表：项目经理、技术负责人、实施人员共 5 人，附职称证书。",
        "service": "售后服务：一般故障 2 小时内响应，8 小时内解决。",
    },
    "N05": {
        "title": "示例市政务服务大厅智能化改造项目",
        "code": "OUT-2026-005",
        "price": "1,420,000.00 元",
        "days": "90 日历天",
        "full": True,
        "progress": "提供横道图与关键路径：第 2 周完成现场勘察，第 5 周完成设备安装，第 9 周完成验收。",
        "team": "项目管理机构：项目经理持注册建造师证书，技术负责人具有高级职称证书。",
        "service": "承诺 4 小时到场，SLA 服务级别不低于 99.5%。",
    },
    "N06": {
        "title": "示例区政务外网安全加固项目",
        "code": "OUT-2026-006",
        "price": "760,000.00 元",
        "days": "90 日历天",
        "full": False,
        "progress": "",
        "team": "",
        "service": "7×24 小时售后响应。",
    },
    "N07": {
        "title": "示例市政务数据共享交换平台项目",
        "code": "OUT-2026-007",
        "price": "1,300,000.00 元",
        "days": "90 日历天",
        "full": False,
        "progress": "里程碑：第 4 周完成接口开发，第 8 周完成联调，第 10 周上线。",
        "team": "项目管理机构：项目经理 1 名（注册建造师），人员表见附件。",
        "service": "",
    },
    "N08": {
        "title": "示例市智慧政务大厅设备采购项目",
        "code": "OUT-2026-008",
        "price": "2,350,000.00 元",
        "days": "120 日历天",
        "full": False,
        "progress": "",
        "team": "",
        "service": "",
    },
}


def add_para(doc, text: str, bold: bool = False) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.font.name = "宋体"
    run.font.size = Pt(10.5)


def add_table(doc, rows: list[list[str]]) -> None:
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            table.cell(i, j).text = value


def make_docx(sid: str, data: dict) -> Path:
    doc = Document()
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(data["title"])
    run.bold = True
    run.font.name = "宋体"
    run.font.size = Pt(16)
    add_para(doc, f"项目编号：{data['code']}")
    add_para(doc, "采购人：示例市公共资源交易中心")
    add_para(doc, "投标人：示例数智科技有限公司")
    add_para(doc, f"投标报价：人民币 {data['price']}")
    add_para(doc, f"工期：{data['days']}")
    add_para(doc, "一、投标函", True)
    add_para(doc, "我方已详细审阅招标文件，承诺按招标文件要求完成本项目，投标文件所附资料真实、准确、完整。")
    add_para(doc, "二、资格证明文件", True)
    add_para(doc, "营业执照：已提供；法定代表人授权书：已提供；财务状况报告：已提供。")
    add_para(doc, "三、技术响应", True)
    add_para(doc, "技术方案：针对本项目提供总体技术路线、系统架构、数据流程与安全设计。")
    add_para(doc, "实施方案与进度计划：", True)
    add_para(doc, data["progress"] or "本章节仅列标题，未展开进度计划。")
    add_para(doc, "质量保证措施：建立质量责任制，执行三级复核与交付前检查。")
    add_para(doc, "应急与安全保障：提供应急预案、安全保障措施与故障处置流程。")
    add_para(doc, "四、商务响应", True)
    add_para(doc, "类似项目业绩：提供同类政务信息化项目业绩 2 项。")
    add_para(doc, "项目团队配置：", True)
    add_para(doc, data["team"] or "本章节仅列标题，未提供项目管理机构及人员表。")
    add_para(doc, "售后服务承诺：", True)
    add_para(doc, data["service"] or "本章节仅列标题，未提供具体服务承诺。")
    add_para(doc, "五、报价明细", True)
    add_table(doc, [
        ["序号", "费用项", "金额（元）"],
        ["1", "软件开发费", "600,000.00"],
        ["2", "实施部署费", "300,000.00"],
        ["3", "培训与运维费", "280,000.00"],
    ])
    add_para(doc, "注：本文件为自造虚构样本，仅用于学生比赛评审测试，不含真实企业/个人信息。")
    path = OUT / f"{sid}.docx"
    doc.save(path)
    return path


def make_workbook() -> None:
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
    ws.row_dimensions[1].height = 42
    for idx, sid in enumerate(SAMPLES, start=2):
        ws.cell(row=idx, column=1, value=sid).alignment = CENTER
        for c in range(1, len(headers) + 1):
            cell = ws.cell(row=idx, column=c)
            cell.font = BODY_FONT
            cell.border = BORDER
            cell.alignment = CENTER if c < 11 else LEFT
        ws.cell(row=idx, column=11, value=f"=SUM(B{idx}:J{idx})").font = Font(name="微软雅黑", size=10, bold=True)
        ws.cell(row=idx, column=11).border = BORDER
        ws.cell(row=idx, column=11).alignment = CENTER
    widths = [8] + [9] * 9 + [9, 26]
    for i, width in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + i)].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:K{1 + len(SAMPLES)}"
    for col, (_, _, max_score) in enumerate(ITEMS, start=2):
        dv = DataValidation(type="decimal", operator="between", formula1="0", formula2=str(max_score),
                            allow_blank=True, showErrorMessage=True,
                            errorTitle="分值超范围", error=f"本项 0–{max_score} 分")
        ws.add_data_validation(dv)
        dv.add(f"{chr(64 + col)}2:{chr(64 + col)}{1 + len(SAMPLES)}")

    ws2 = wb.create_sheet("说明")
    ws2.column_dimensions["A"].width = 100
    lines = [
        ("招投标评审助手 · 新样本评分表（S11–S18）", Font(name="微软雅黑", size=14, bold=True, color="1F4E79")),
        ("", BODY_FONT),
        ("用途：请老师按同一套 9 项细则，对 8 份匿名投标文件独立打分。", BODY_FONT),
        ("时间：约 45–60 分钟；不需要安装软件，Excel 填分即可。", BODY_FONT),
        ("填写：只填 B–J 列；K 列自动求和；L 列备注可选。", BODY_FONT),
        ("说明：样本全部虚构、匿名；仅用于学生比赛报告，不是评标委员会结论。", BODY_FONT),
        ("", BODY_FONT),
        ("这 8 份是 out-of-sample：老师此前未评过，用于验证校准后的判据，不是同一批 10 份。", Font(name="微软雅黑", size=10, bold=True, color="C00000")),
    ]
    for idx, (text, font) in enumerate(lines, start=1):
        cell = ws2.cell(row=idx, column=1, value=text)
        cell.font = font
        cell.alignment = LEFT
    wb.save(OUT / "新样本评分表.xlsx")


def make_instructions() -> None:
    doc = Document()
    p = doc.add_paragraph()
    r = p.add_run("新样本盲评说明（S11–S18）")
    r.bold = True
    r.font.name = "宋体"
    r.font.size = Pt(16)
    for text in [
        "老师您好：",
        "这是 8 份新的匿名投标文件（N01–N08），与之前 10 份不重复，用于验证校准后的判据。",
        "请您按同一套 9 项、100 分细则独立打分；不需要安装软件，直接在《新样本评分表.xlsx》里填分即可。",
        "时间约 45–60 分钟；如果时间紧，可以先评 N01–N04，剩余留空。",
        "样本全部为自造虚构数据，不含真实企业/个人信息；只用于学生比赛报告，可匿名/致谢。",
        "谢谢您！",
    ]:
        doc.add_paragraph(text)
    doc.save(OUT / "00-新样本盲评说明.docx")


def make_manifest() -> None:
    with (OUT / "样本清单_组织者用.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["sample_id", "file", "设计意图（不要发给老师）"])
        notes = {
            "N01": "全实质：进度表+团队表+SLA",
            "N02": "只有标题：T2/B2/B3 都无实质",
            "N03": "套话陷阱：工期安排无数字、响应时限无数字",
            "N04": "数字进度+人员表+具体时限",
            "N05": "横道图+证书+SLA",
            "N06": "只有 7×24，无具体时限",
            "N07": "有进度/团队，无售后承诺",
            "N08": "报价超限价，资格/技术/商务均弱",
        }
        for sid, data in SAMPLES.items():
            w.writerow([sid, f"{sid}.docx", notes[sid]])


def main() -> int:
    if OUT.exists():
        for path in OUT.glob("*"):
            path.unlink()
    OUT.mkdir(parents=True, exist_ok=True)
    for sid, data in SAMPLES.items():
        make_docx(sid, data)
    make_workbook()
    make_instructions()
    make_manifest()
    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(OUT.iterdir()):
            if path.name != "样本清单_组织者用.csv":
                zf.write(path, path.name)
    print(f"written {OUT}")
    print(f"written {ZIP} ({ZIP.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
