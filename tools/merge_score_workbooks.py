"""把 N01-N08 与 N09-N10 两张评分表合并成 N01-N10。"""
from __future__ import annotations

from copy import copy
from pathlib import Path

from openpyxl import load_workbook

BASE = Path(__file__).resolve().parent.parent / "docs" / "评审功能测评数据" / "01-评分重评"
SRC = BASE / "评分表_N01-N08.xlsx"
ADD = BASE / "评分表_N09-N10.xlsx"
OUT = BASE / "评分表_N01-N10.xlsx"


def main() -> int:
    wb = load_workbook(SRC)
    ws = wb["评分表"]
    add = load_workbook(ADD)["评分表"]
    for src_row, dst_row in ((2, 10), (3, 11)):
        for col in range(1, 13):
            cell = ws.cell(row=dst_row, column=col, value=add.cell(row=src_row, column=col).value)
            proto = ws.cell(row=2, column=col)
            cell.font = copy(proto.font)
            cell.fill = copy(proto.fill)
            cell.border = copy(proto.border)
            cell.alignment = copy(proto.alignment)
            cell.number_format = proto.number_format
            cell.protection = copy(proto.protection)
        ws.cell(row=dst_row, column=11, value=f"=SUM(B{dst_row}:J{dst_row})")
        ws.row_dimensions[dst_row].height = ws.row_dimensions[2].height
    # 说明页
    info = wb["说明"]
    texts = [
        "招投标评审助手 · 新样本评分表（N01–N10）",
        "",
        "用途：请老师按同一套 9 项细则，对 10 份匿名投标文件独立打分。",
        "时间：约 60–75 分钟；不需要安装软件，Excel 填分即可。",
        "填写：只填 B–J 列；K 列自动求和；L 列备注可选。",
        "说明：样本全部虚构、匿名；仅用于学生比赛报告，不是评标委员会结论。",
        "这 10 份是 out-of-sample：N01–N08 与 N09–N10 同一套细则、同一次重评。",
    ]
    for row, text in enumerate(texts, start=1):
        info.cell(row=row, column=1, value=text)
    wb.save(OUT)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
