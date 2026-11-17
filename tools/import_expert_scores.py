import json
from openpyxl import load_workbook

IDS = ["P1", "T1", "T2", "T3", "T4", "T5", "B1", "B2", "B3"]
items = []
for file, start, end in [
    ("docs/评审功能测评数据/老师参考评分回收/评分表_N01-N08.xlsx", 2, 9),
    ("docs/评审功能测评数据/老师参考评分回收/评分表_N09-N10.xlsx", 2, 3),
]:
    sheet = load_workbook(file, data_only=False)["评分表"]
    for row in range(start, end + 1):
        sid = sheet.cell(row=row, column=1).value
        scores = {IDS[i]: sheet.cell(row=row, column=2 + i).value for i in range(9)}
        total = sum(scores.values())
        items.append({
            "file": f"out_of_sample/新样本_S11-S18/{sid}.docx",
            "profile": "profile-a-calibrated",
            "reviewer": "BLIND-01",
            "total": total,
            "scores": scores,
        })
payload = {
    "version": "v2",
    "generated_at": "2026-11-17",
    "note": "重评版：N01-N10 一次盲评，B3 按具体时限/SLA/质保期严格口径；不区分独立性。",
    "items": items,
}
with open("data/samples/expert_scores.json", "w", encoding="utf-8") as fh:
    fh.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
print("items", len(items), [(i["file"].split("/")[-1], i["total"]) for i in items])
