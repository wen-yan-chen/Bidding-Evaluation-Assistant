"""修正 N02–N08 的报价明细三项，使其合计等于投标函报价。

只改“报价明细”的示意金额，不改投标函、工期、技术/商务内容，也不改任何评分。
"""
from __future__ import annotations

from pathlib import Path

from docx import Document

BASE = Path(__file__).resolve().parent.parent / "data" / "samples" / "out_of_sample" / "新样本_S11-S18"
PRICES = {
    "N02": 960_000,
    "N03": 1_050_000,
    "N04": 880_000,
    "N05": 1_420_000,
    "N06": 760_000,
    "N07": 1_300_000,
    "N08": 2_350_000,
}


def main() -> int:
    for sid, price in PRICES.items():
        path = BASE / f"{sid}.docx"
        doc = Document(path)
        table = doc.tables[0]
        first = round(price * 0.55, 2)
        second = round(price * 0.30, 2)
        third = round(price - first - second, 2)
        for row, amount in zip(table.rows[1:4], (first, second, third)):
            row.cells[2].text = f"{amount:,.2f}"
        doc.add_paragraph("注：报价明细三项合计与投标函投标报价一致。")
        doc.save(path)
        print(sid, price, [first, second, third], "sum", first + second + third)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
