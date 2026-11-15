"""生成 10 份「植入风险」投标文件 + 5 份干净对照，供 D6 算检出率/误报率。

设计：
- 每份风险样本只植入 1 类风险（便于归因），正文其余部分与正常标书一致；
- 5 份干净样本直接复用 `data/samples/bid-001..005`（它们本身就带有"已提交投标保证金"
  这类合规定式，正好用来测误报）；
- 同步产出 `data/samples/risk/manifest.json`（人工标注 = 唯一评测口径）。

用法：
  python tools/make_risk_samples.py
  python tools/make_risk_samples.py --all-clean   # 只重建干净对照（一般不需要）
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from docx import Document  # noqa: E402

from tools.make_samples import build_document, basic_lines  # noqa: E402

OUT = ROOT / "data" / "samples" / "risk"
CLEAN = ROOT / "data" / "samples"

CAP_LINE = "最高投标限价：人民币 2,000,000.00 元（报价超过该限价的按废标处理）"

RISK_CASES: list[dict] = [
    {
        "file": "risk-001.docx",
        "expect_rules": ["R12"],
        "expect_qualification": [],
        "split": "dev",
        "note": "报价 2,300,000 元 > 最高限价 2,000,000 元",
        "项目名称": "示例市政务云平台三期设备采购项目",
        "项目编号": "SJ-2026-GK-021",
        "采购人": "示例市公共资源交易中心",
        "投标人": "示例超价科技有限公司",
        "报价文本": "人民币 2,300,000.00 元（大写：贰佰叁拾万元整）",
        "工期": "90 日历天",
        "extras": [CAP_LINE],
    },
    {
        "file": "risk-002.docx",
        "expect_rules": ["R13"],
        "expect_qualification": [],
        "split": "dev",
        "note": "报价 900,000 元，仅为限价 45%，疑似低于成本",
        "项目名称": "示例区政务网络运维服务项目",
        "项目编号": "FW-2026-YW-033",
        "采购人": "示例区大数据中心",
        "投标人": "示例低价服务有限公司",
        "报价文本": "人民币 900,000.00 元（大写：玖拾万元整）",
        "工期": "365 日历天",
        "extras": [CAP_LINE],
    },
    {
        "file": "risk-003.docx",
        "expect_rules": ["R17"],
        "expect_qualification": [],
        "split": "holdout",
        "note": "投标有效期 60 天 < 要求 90 天",
        "项目名称": "示例市不动产登记系统升级项目",
        "项目编号": "BD-2026-GK-012",
        "采购人": "示例市自然资源和规划局",
        "投标人": "示例地理信息科技有限公司",
        "报价文本": "人民币 1,560,000.00 元（大写：壹佰伍拾陆万元整）",
        "工期": "120 日历天",
        "extras": [CAP_LINE, "投标有效期为自投标截止之日起 60 个日历日。"],
    },
    {
        "file": "risk-004.docx",
        "expect_rules": ["R37"],
        "expect_qualification": [],
        "split": "dev",
        "note": "大写「壹佰贰拾万元整」与小写 1,286,000.00 不一致",
        "项目名称": "示例市智慧交通信号优化项目",
        "项目编号": "JT-2026-GK-018",
        "采购人": "示例市公安局交通警察支队",
        "投标人": "示例交通科技有限公司",
        "报价文本": "人民币 1,286,000.00 元（大写：壹佰贰拾万元整）",
        "工期": "90 日历天",
        "extras": [CAP_LINE],
    },
    {
        "file": "risk-005.docx",
        "expect_rules": [],
        "expect_qualification": ["R01"],
        "split": "dev",
        "note": "删除营业执照章节与统一社会信用代码（资格性缺失）",
        "项目名称": "示例县农村饮水安全巩固提升工程",
        "项目编号": "NS-2026-SG-051",
        "采购人": "示例县水利局",
        "投标人": "示例水务工程有限公司",
        "报价文本": "人民币 1,600,000.00 元（大写：壹佰陆拾万元整）",
        "工期": "180 日历天",
        "extras": [CAP_LINE],
        "drop_keywords": ["营业执照", "统一社会信用代码"],
    },
    {
        "file": "risk-006.docx",
        "expect_rules": ["R21"],
        "expect_qualification": [],
        "split": "dev",
        "note": "正文写明由同一编制人统一编制（串标特征）",
        "项目名称": "示例市公共文化云平台建设项目",
        "项目编号": "WH-2026-GK-027",
        "采购人": "示例市文化和旅游局",
        "投标人": "示例文化科技有限公司",
        "报价文本": "人民币 1,680,000.00 元（大写：壹佰陆拾捌万元整）",
        "工期": "90 日历天",
        "extras": [CAP_LINE, "本项目投标文件由示例代理咨询有限公司同一编制人统一编制。"],
    },
    {
        "file": "risk-007.docx",
        "expect_rules": ["R27"],
        "expect_qualification": [],
        "split": "holdout",
        "note": "投标保证金与另一投标人从同一账户转出",
        "项目名称": "示例区垃圾分类智能监管项目",
        "项目编号": "HJ-2026-GK-044",
        "采购人": "示例区城市管理局",
        "投标人": "示例环境服务有限公司",
        "报价文本": "人民币 1,380,000.00 元（大写：壹佰叁拾捌万元整）",
        "工期": "365 日历天",
        "extras": [CAP_LINE, "我方投标保证金与示例联合投标公司从同一账户转出。"],
    },
    {
        "file": "risk-008.docx",
        "expect_rules": ["R20"],
        "expect_qualification": [],
        "split": "dev",
        "note": "正文承认提供虚假材料",
        "项目名称": "示例市档案馆库房改造项目",
        "项目编号": "DA-2026-SG-009",
        "采购人": "示例市档案馆",
        "投标人": "示例建筑装饰有限公司",
        "报价文本": "人民币 1,760,000.00 元（大写：壹佰柒拾陆万元整）",
        "工期": "150 日历天",
        "extras": [CAP_LINE, "为满足业绩要求，我方提供虚假材料用于本次投标。"],
    },
    {
        "file": "risk-009.docx",
        "expect_rules": ["R31"],
        "expect_qualification": [],
        "split": "dev",
        "note": "报价 1,990,000 元，达到限价 99.5%（贴标）",
        "项目名称": "示例市智慧停车管理平台项目",
        "项目编号": "TC-2026-GK-036",
        "采购人": "示例市城市管理局",
        "投标人": "示例停车科技有限公司",
        "报价文本": "人民币 1,990,000.00 元（大写：壹佰玖拾玖万元整）",
        "工期": "90 日历天",
        "extras": [CAP_LINE],
    },
    {
        "file": "risk-011.docx",
        "expect_rules": ["R14"],
        "expect_qualification": [],
        "split": "dev",
        "note": "投标文件未加盖公章（签章缺失）",
        "项目名称": "示例市残疾人康复中心改造项目",
        "项目编号": "CJ-2026-SG-101",
        "采购人": "示例市残疾人联合会",
        "投标人": "示例康复工程有限公司",
        "报价文本": "人民币 1,340,000.00 元（大写：壹佰叁拾肆万元整）",
        "工期": "150 日历天",
        "extras": [CAP_LINE, "本投标文件未加盖公章，亦未由法定代表人签字。"],
    },
    {
        "file": "risk-012.docx",
        "expect_rules": ["R15"],
        "expect_qualification": [],
        "split": "holdout",
        "note": "明确声明不接受招标文件的付款条件（实质性偏离）",
        "项目名称": "示例市智慧水务监测项目",
        "项目编号": "SW-2026-GK-107",
        "采购人": "示例市水务局",
        "投标人": "示例水务科技有限公司",
        "报价文本": "人民币 1,720,000.00 元（大写：壹佰柒拾贰万元整）",
        "工期": "120 日历天",
        "extras": [CAP_LINE, "我方不接受招标文件约定的付款条件，要求签约后一次性支付全款。"],
    },
    {
        "file": "risk-013.docx",
        "expect_rules": ["R16"],
        "expect_qualification": [],
        "split": "dev",
        "note": "同一投标人提交两个报价（备选报价未按要求标注）",
        "项目名称": "示例市城市大脑数据治理项目",
        "项目编号": "CS-2026-GK-113",
        "采购人": "示例市大数据管理局",
        "投标人": "示例数据治理有限公司",
        "报价文本": "人民币 1,480,000.00 元（大写：壹佰肆拾捌万元整）",
        "工期": "180 日历天",
        "extras": [CAP_LINE, "除上述报价外，我方另提交两个报价供采购人选择。"],
    },
    {
        "file": "risk-014.docx",
        "expect_rules": ["R19"],
        "expect_qualification": [],
        "split": "dev",
        "note": "投标文件逾期送达",
        "项目名称": "示例区老旧小区改造监理项目",
        "项目编号": "LJ-2026-JL-120",
        "采购人": "示例区住房和城乡建设局",
        "投标人": "示例工程监理有限公司",
        "报价文本": "人民币 1,540,000.00 元（大写：壹佰伍拾肆万元整）",
        "工期": "240 日历天",
        "extras": [CAP_LINE, "因内部流程原因，本投标文件逾期送达投标地点。"],
    },
    {
        "file": "risk-015.docx",
        "expect_rules": ["R35"],
        "expect_qualification": [],
        "split": "holdout",
        "note": "报价币种使用美元（未按人民币报价）",
        "项目名称": "示例市国际会展中心智能化项目",
        "项目编号": "HZ-2026-GK-126",
        "采购人": "示例市商务局",
        "投标人": "示例国际智能科技有限公司",
        "报价文本": "USD 320,000.00（美元叁拾贰万元整）",
        "工期": "150 日历天",
        "extras": [CAP_LINE, "本项目报价以美元（USD）计。"],
    },
    {
        "file": "risk-010.docx",
        "expect_rules": [],
        "expect_qualification": ["R09"],
        "split": "holdout",
        "note": "以联合体形式投标但未提交联合体协议",
        "项目名称": "示例市地下管网普查项目",
        "项目编号": "GW-2026-GK-058",
        "采购人": "示例市住房和城乡建设局",
        "投标人": "示例勘测设计研究院",
        "报价文本": "人民币 1,900,000.00 元（大写：壹佰玖拾万元整）",
        "工期": "180 日历天",
        "extras": [CAP_LINE, "本项目以联合体形式投标，联合体各方按分工承担相应工作。"],
    },
]

CLEAN_CASES = [
    {"file": "bid-001.docx", "split": "dev"},
    {"file": "bid-002.docx", "split": "holdout"},
    {"file": "bid-003.docx", "split": "dev"},
    {"file": "bid-004.pdf", "split": "dev"},
    {"file": "bid-005.pdf", "split": "holdout"},
]


def _drop_paragraphs(document: Document, keywords: list[str]) -> None:
    for paragraph in list(document.paragraphs):
        text = paragraph.text or ""
        if any(k in text for k in keywords):
            element = paragraph._element
            element.getparent().remove(element)


def build_case(case: dict, out_path: Path) -> None:
    item = {
        "项目名称": case["项目名称"],
        "项目编号": case["项目编号"],
        "采购人": case["采购人"],
        "投标人": case["投标人"],
        "报价文本": case["报价文本"],
        "工期": case["工期"],
        "with_table": False,
    }
    item["basic_lines"] = basic_lines(item)
    document = build_document(item)
    if case.get("drop_keywords"):
        _drop_paragraphs(document, case["drop_keywords"])
    for line in case.get("extras") or []:
        paragraph = document.add_paragraph(line)
        paragraph.paragraph_format.space_after = 6
    document.save(out_path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="生成植入风险样本与干净对照")
    ap.add_argument("--all-clean", action="store_true", help="只重建 manifest")
    args = ap.parse_args(argv)

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    (OUT / "README.md").write_text(
        "# 植入风险样本（D6）\n\n"
        "每份样本只植入 1 类风险，正文其余部分与正常标书一致；"
        "`manifest.json` 是人工标注（唯一评测口径），`split` 标记 dev/holdout。\n\n"
        "| 文件 | 植入风险 | 期望规则 |\n| --- | --- | --- |\n"
        + "\n".join(f"| `{c['file']}` | {c['note']} | {', '.join(c['expect_rules'] + c['expect_qualification']) or '（无）'} |" for c in RISK_CASES)
        + "\n",
        encoding="utf-8",
    )

    items: list[dict] = []
    for case in RISK_CASES:
        path = OUT / case["file"]
        build_case(case, path)
        items.append(
            {
                "file": f"risk/{case['file']}",
                "split": case["split"],
                "clean": False,
                "note": case["note"],
                "expect_rules": case["expect_rules"],
                "expect_qualification": case["expect_qualification"],
            }
        )

    for clean in CLEAN_CASES:
        items.append(
            {
                "file": clean["file"],
                "split": clean["split"],
                "clean": True,
                "note": "干净对照（仅含合规定式表述）",
                "expect_rules": [],
                "expect_qualification": [],
            }
        )

    manifest = {
        "version": "v1",
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "context": {"max_price": 2000000, "min_validity_days": 90, "below_cost_ratio": 0.6, "near_cap_ratio": 0.97},
        "note": "全部为自造虚构数据；风险样本每份只植入一类，干净对照用于测误报。",
        "items": items,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"已生成 {len(RISK_CASES)} 份风险样本 + {len(CLEAN_CASES)} 份干净对照 → {OUT}")
    for item in items:
        print(f"  {item['file']:<22} {'clean' if item['clean'] else 'risk ':<6} {item['split']:<8} {item['note'][:36]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
