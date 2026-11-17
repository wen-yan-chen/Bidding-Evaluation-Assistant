"""生成资格性人工标注表 A/B（25 样本 × R01–R10 = 250 行）。"""
from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

BASE = Path(__file__).resolve().parent          # 组织者用
ROOT = BASE.parent                              # 资格性标注材料
OUT = ROOT / "标注员包"
MAP = BASE / "样本映射.csv"

RULES = [
    ("R01", "营业执照"),
    ("R02", "行业资质证书"),
    ("R03", "安全生产许可证"),
    ("R04", "法定代表人授权书"),
    ("R05", "财务状况报告"),
    ("R06", "社保或纳税证明"),
    ("R07", "无重大违法记录声明"),
    ("R08", "中小企业声明函"),
    ("R09", "联合体协议"),
    ("R10", "项目负责人资格"),
]
STATES = "已提供,缺失,效力不足,无法判断"

HEAD_FILL = PatternFill("solid", fgColor="1F4E79")
HEAD_FONT = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
BODY_FONT = Font(name="微软雅黑", size=9)
THIN = Side(style="thin", color="D9E2F3")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)


def main() -> int:
    with MAP.open(encoding="utf-8-sig") as fh:
        samples = list(csv.DictReader(fh))
    for label in ("A", "B"):
        wb = Workbook()
        ws = wb.active
        ws.title = "标注表"
        headers = ["样本编号", "规则", "材料", "状态", "页码", "原文/备注", "标注员"]
        ws.append(headers)
        for c in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=c)
            cell.fill = HEAD_FILL
            cell.font = HEAD_FONT
            cell.alignment = CENTER
            cell.border = BORDER
        row = 2
        for sample in samples:
            for rid, material in RULES:
                ws.cell(row=row, column=1, value=sample["sample_id"]).alignment = CENTER
                ws.cell(row=row, column=2, value=rid).alignment = CENTER
                ws.cell(row=row, column=3, value=material).alignment = LEFT
                ws.cell(row=row, column=7, value=label).alignment = CENTER
                for c in range(1, len(headers) + 1):
                    cell = ws.cell(row=row, column=c)
                    cell.font = BODY_FONT
                    cell.border = BORDER
                row += 1
        widths = [10, 7, 22, 12, 10, 48, 8]
        for i, width in enumerate(widths, start=1):
            ws.column_dimensions[chr(64 + i)].width = width
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:G{row - 1}"
        dv = DataValidation(type="list", formula1=f'"{STATES}"', allow_blank=True,
                            showErrorMessage=True, errorTitle="状态不合法",
                            error="只能选：已提供 / 缺失 / 效力不足 / 无法判断")
        ws.add_data_validation(dv)
        dv.add(f"D2:D{row - 1}")
        ws.cell(row=row + 1, column=1,
                value="说明：状态只能选四个下拉值；页码/原文/备注尽量填；无法判断请在备注写原因。").font = Font(
            name="微软雅黑", size=9, color="666666")
        path = OUT / f"03-标注表_{label}.xlsx"
        wb.save(path)
        print(f"written {path} rows={row - 2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
