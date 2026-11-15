"""生成 D2 评测用的 10 份模拟投标文件（全部虚构，不含任何真实招投标信息）。

覆盖的形态：
- 格式：docx ×5、pdf ×2（docx 转制，带文本层）、txt ×3（含 GB18030 编码）
- 结构：带表格的报价明细、纯段落、超一页长文
- 边界：缺报价/缺工期（bid-008）、报价只写"￥金额"无单位且工期用"个月"（bid-009）

同时产出 `manifest.json`（人工标准答案），供 `tools/eval_parse.py` 复算
"解析成功率 / 关键字段准确率"，避免"我觉得抽得挺准"这种无法验收的说法。

用法：
  python tools/make_samples.py            # 生成 docx/txt + 转 pdf + 写 manifest
  python tools/make_samples.py --no-pdf   # 只生成 docx/txt（不依赖 LibreOffice）
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "samples"
SRC = OUT / "_docx_src"  # 转 pdf 用的中间 docx，不提交

DEFAULT_LO_NODE = r"D:\deepseek harness\resources\runtime\primary-runtime\dependencies\node\bin\node.exe"
DEFAULT_LO_CLI = (
    r"D:\deepseek harness\resources\app.asar.unpacked\dsh"
    r"\node_modules\@deepseek-ai\libreoffice-kit\lib\cli.js"
)

GENERIC_PARAS = [
    "我方已详细审阅招标文件的全部内容，包括澄清、修改文件及全部附件，对招标文件的条款无异议，并接受招标文件中约定的评标办法与合同主要条款。",
    "本投标文件中所提供的全部资料均真实、准确、完整，我方对资料的真实性承担法律责任；如经查实存在虚假材料，愿接受取消投标资格、没收投标保证金等处理。",
    "我方承诺按照招标文件确定的工期组织资源投入，关键岗位人员按投标文件承诺到岗，不擅自更换项目负责人及主要技术人员。",
    "我方具备履行本项目合同所必需的技术能力、人员配置与售后服务网络，能够在项目所在地提供本地化服务响应。",
    "我方近三年内不存在被列入失信被执行人名单、重大税收违法失信主体名单的情形，亦不存在处于被责令停业、财产被接管、冻结等状态的情形。",
    "投标有效期内，本投标文件对我方始终具有约束力；若我方在投标有效期内撤销投标文件，愿承担相应违约责任。",
    "我方理解并接受：评标委员会有权要求我方对投标文件中含义不明确的内容作出澄清，澄清不得改变投标文件的实质性内容。",
    "本项目实施过程中形成的全部文档、数据与成果的知识产权归属按合同约定处理，我方保证不侵犯任何第三方的知识产权。",
    "我方已按招标文件要求提交投标保证金，保证金的形式、金额与有效期均符合要求，并接受招标人对保证金的处置约定。",
    "如中标，我方将在收到中标通知书后按约定时限与采购人签订合同，并按合同约定提交履约保证金，全面履行合同义务。",
]


def _set_font(run, size: float = 11, bold: bool = False, name: str = "宋体") -> None:
    run.font.size = Pt(size)
    run.bold = bold
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:eastAsia"), name)
    rfonts.set(qn("w:ascii"), "Times New Roman")
    rfonts.set(qn("w:hAnsi"), "Times New Roman")


def _para(doc: Document, text: str, *, bold: bool = False, size: float = 11,
          align: int | None = None, space_after: float = 6) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.4
    if align is not None:
        p.alignment = align
    _set_font(p.add_run(text), size=size, bold=bold)


def build_document(item: dict) -> Document:
    """按条目内容生成一份完整的投标文件（封面 + 基本信息 + 四章正文）。"""
    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Cm(2.5)
    section.left_margin = section.right_margin = Cm(2.5)

    _para(doc, item["项目名称"], bold=True, size=16, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)
    _para(doc, "投 标 文 件", bold=True, size=22, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)
    _para(doc, f"投标人：{item['投标人']}", size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    _para(doc, "编制日期：二〇二六年十一月", size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=18)

    # 基本信息：字段抽取的主战场，标签与值写在同一行
    _para(doc, "一、投标基本信息", bold=True, size=13)
    for line in item["basic_lines"]:
        _para(doc, line)

    _para(doc, "二、投标函", bold=True, size=13, space_after=4)
    _para(doc, "第一章 投标函", bold=True)
    _para(doc, "一、投标承诺")
    for i, text in enumerate(GENERIC_PARAS[:5], start=1):
        _para(doc, f"{i}.{i} {text}")

    _para(doc, "第二章 资格证明文件", bold=True)
    _para(doc, "第三条 营业执照")
    _para(doc, f"投标人（全称）：{item['投标人']}")
    _para(doc, "统一社会信用代码：91330100MA2XXXXXXX（示例，虚构）")
    _para(doc, "经营范围：软件开发；信息系统集成服务；数据处理和存储支持服务；信息技术咨询服务。")
    _para(doc, "第四条 法定代表人授权书")
    _para(doc, "兹授权我方法定代表人授权的委托代理人，以我方名义参加本项目投标活动，全权处理投标、澄清、签约等事宜。")
    _para(doc, "第五条 财务状况报告")
    _para(doc, "我方提供近一年度经审计的财务报告，资产负债率、流动比率等指标满足招标文件要求，不存在资不抵债情形。")

    _para(doc, "第三章 商务与技术响应", bold=True)
    _para(doc, "第六条 项目实施计划")
    for text in GENERIC_PARAS[5:8]:
        _para(doc, text)
    _para(doc, "第七条 售后服务承诺")
    _para(doc, "我方承诺提供 7×24 小时故障受理，一般故障 2 小时内响应、8 小时内解决；重大故障 1 小时内响应、24 小时内恢复。")

    _para(doc, "第四章 报价明细", bold=True)
    _para(doc, "第八条 报价构成")
    if item.get("with_table"):
        table = doc.add_table(rows=1, cols=4)
        table.style = "Table Grid"
        for i, text in enumerate(["序号", "费用项", "说明", "金额（元）"]):
            cell = table.rows[0].cells[i]
            cell.text = ""
            _set_font(cell.paragraphs[0].add_run(text), size=9, bold=True)
        rows = [
            ("1", "软件开发费", "按功能点测算", "860,000.00"),
            ("2", "实施部署费", "含环境搭建与数据迁移", "216,000.00"),
            ("3", "培训与文档费", "含 3 场培训与全套文档", "120,000.00"),
            ("4", "一年运维服务费", "7×24 响应", "90,000.00"),
        ]
        for row in rows:
            cells = table.add_row().cells
            for i, text in enumerate(row):
                cells[i].text = ""
                _set_font(cells[i].paragraphs[0].add_run(text), size=9)
        _para(doc, "合计金额与投标报价一致；报价包含完成本项目全部工作内容所需的一切费用。")

    _para(doc, "第五章 其他资料", bold=True)
    for text in GENERIC_PARAS[8:]:
        _para(doc, text)

    return doc


def build_text(item: dict) -> str:
    """txt 版本：同样的信息，用纯文本行组织。"""
    lines = [item["项目名称"], "投 标 文 件", ""]
    lines.extend(item["basic_lines"])
    lines.append("")
    lines.append("第一章 投标函")
    lines.append("一、投标承诺")
    for i, text in enumerate(GENERIC_PARAS[:5], start=1):
        lines.append(f"{i}.{i} {text}")
    lines.append("第二章 资格证明文件")
    lines.append("第三条 营业执照")
    lines.append(f"投标人（全称）：{item['投标人']}")
    lines.append("统一社会信用代码：91330100MA2XXXXXXX（示例，虚构）")
    lines.append("第三章 商务与技术响应")
    lines.extend(GENERIC_PARAS[5:8])
    lines.append("第四章 报价明细")
    lines.append("第八条 报价构成")
    lines.append("合计金额与投标报价一致；报价包含完成本项目全部工作内容所需的一切费用。")
    lines.append("")
    if item.get("long"):
        # 边界样本：把承诺条款再走一遍，把篇幅撑过一页，验证"页码估算"这条路
        lines.append("第五章 其他资料")
        for text in GENERIC_PARAS:
            lines.append(text)
        lines.append("")
    return "\n".join(lines)


def convert_pdf(docx_path: Path, pdf_path: Path) -> None:
    node = Path(os.environ.get("LO_NODE", DEFAULT_LO_NODE))
    cli = Path(os.environ.get("LO_CLI", DEFAULT_LO_CLI))
    if not node.exists() or not cli.exists():
        raise SystemExit(
            "找不到 LibreOffice Kit，无法转 pdf。用 --no-pdf 跳过，"
            "或设置环境变量 LO_NODE / LO_CLI 指向已安装的 node 与 cli.js。"
        )
    result = subprocess.run(
        [str(node), str(cli), "convert", "--input", str(docx_path), "--output", str(pdf_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not pdf_path.exists():
        raise SystemExit(f"pdf 转换失败：{result.stderr[:400]}")
    if pdf_path.read_bytes()[:5] != b"%PDF-":
        raise SystemExit("转换产物文件头不是 %PDF-，拒绝写入样本")


def basic_lines(item: dict) -> list[str]:
    """基本信息行：字段抽取的输入。缺字段的样本刻意不写对应行。"""
    lines = [
        f"项目名称：{item['项目名称']}",
        f"项目编号：{item['项目编号']}",
        f"采购人：{item['采购人']}",
        f"投标人：{item['投标人']}",
    ]
    if not item.get("no_price"):
        lines.append(f"投标报价：{item['报价文本']}")
    if not item.get("no_duration"):
        lines.append(f"工期：{item['工期']}")
    return lines


EXPECT_KEYS = ("项目名称", "项目编号", "采购人", "投标人", "报价", "工期")

# 10 份样本：主体、编号、金额、工期全部虚构
SAMPLES: list[dict] = [
    {
        "file": "bid-001.docx",
        "kind": "货物",
        "format": "docx",
        "with_table": True,
        "项目名称": "示例市政务云平台二期设备采购项目",
        "项目编号": "SJ-2026-GK-014",
        "采购人": "示例市公共资源交易中心",
        "投标人": "示例数智科技有限公司",
        "报价": "1,286,000.00 元",
        "报价文本": "人民币 1,286,000.00 元（大写：壹佰贰拾捌万陆仟元整）",
        "工期": "90 日历天",
    },
    {
        "file": "bid-002.docx",
        "kind": "服务",
        "format": "docx",
        "with_table": False,
        "项目名称": "示例区政务服务中心窗口辅助服务外包项目",
        "项目编号": "FW-2026-CS-027",
        "采购人": "示例区行政审批服务局",
        "投标人": "示例人力服务集团有限公司",
        "报价": "2,460,000.00 元",
        "报价文本": "人民币 2,460,000.00 元（大写：贰佰肆拾陆万元整）",
        "工期": "365 日历天",
    },
    {
        "file": "bid-003.docx",
        "kind": "工程",
        "format": "docx",
        "with_table": False,
        "项目名称": "示例县城北片区雨污分流改造工程",
        "项目编号": "GC-2026-SG-108",
        "采购人": "示例县住房和城乡建设局",
        "投标人": "示例建工集团有限公司",
        "报价": "18,960,000.00 元",
        "报价文本": "人民币 18,960,000.00 元（大写：壹仟捌佰玖拾陆万元整）",
        "工期": "180 日历天",
    },
    {
        "file": "bid-004.pdf",
        "kind": "货物",
        "format": "pdf",
        "with_table": True,
        "项目名称": "示例市医保信息平台接口改造采购项目",
        "项目编号": "YB-2026-GK-006",
        "采购人": "示例市医疗保障局",
        "投标人": "示例健康数据科技有限公司",
        "报价": "768,500.00 元",
        "报价文本": "人民币 768,500.00 元（大写：柒拾陆万捌仟伍佰元整）",
        "工期": "120 日历天",
    },
    {
        "file": "bid-005.pdf",
        "kind": "服务",
        "format": "pdf",
        "with_table": False,
        "项目名称": "示例市公共数据开放平台运营服务项目",
        "项目编号": "SJ-2026-FW-052",
        "采购人": "示例市大数据管理局",
        "投标人": "示例数据运营服务有限公司",
        "报价": "1,920,000.00 元",
        "报价文本": "人民币 1,920,000.00 元（大写：壹佰玖拾贰万元整）",
        "工期": "12 个月",
    },
    {
        "file": "bid-006.txt",
        "kind": "服务",
        "format": "txt",
        "encoding": "gb18030",
        "项目名称": "示例市 12345 热线智能客服运维项目",
        "项目编号": "FW-2026-YW-031",
        "采购人": "示例市政务服务管理局",
        "投标人": "示例智能语音科技有限公司",
        "报价": "560,000.00 元",
        "报价文本": "人民币 560,000.00 元（大写：伍拾陆万元整）",
        "工期": "365 日历天",
    },
    {
        "file": "bid-007.txt",
        "kind": "货物",
        "format": "txt",
        "encoding": "utf-8",
        "long": True,
        "boundary": "长文本（超一页，页码估算）",
        "项目名称": "示例区中小学多媒体教学设备更新项目",
        "项目编号": "JY-2026-GK-019",
        "采购人": "示例区教育局",
        "投标人": "示例教育科技有限公司",
        "报价": "3,340,000.00 元",
        "报价文本": "人民币 3,340,000.00 元（大写：叁佰叁拾肆万元整）",
        "工期": "60 日历天",
    },
    {
        "file": "bid-008.docx",
        "kind": "服务",
        "format": "docx",
        "boundary": "缺报价与工期（应判为未提供，不得编造）",
        "with_table": False,
        "项目名称": "示例市档案馆数字化加工服务项目",
        "项目编号": "DA-2026-FW-004",
        "采购人": "示例市档案馆",
        "投标人": "示例档案服务有限公司",
        "no_price": True,
        "no_duration": True,
    },
    {
        "file": "bid-009.txt",
        "kind": "货物",
        "format": "txt",
        "encoding": "utf-8",
        "boundary": "报价只写 ￥ 金额无单位；工期用“个月”",
        "项目名称": "示例市应急指挥中心显示系统采购项目",
        "项目编号": "YJ-2026-GK-021",
        "采购人": "示例市应急管理局",
        "投标人": "示例视讯工程有限公司",
        "报价": "968,000.00 元",
        "报价文本": "￥968,000.00",
        "工期": "6 个月",
    },
    {
        "file": "bid-010.docx",
        "kind": "工程",
        "format": "docx",
        "boundary": "长文档（多页）",
        "with_table": True,
        "项目名称": "示例高新区智慧园区综合管理平台建设工程",
        "项目编号": "GX-2026-SG-077",
        "采购人": "示例高新区管理委员会",
        "投标人": "示例智慧城市科技有限公司",
        "报价": "5,780,000.00 元",
        "报价文本": "人民币 5,780,000.00 元（大写：伍佰柒拾捌万元整）",
        "工期": "240 日历天",
    },
]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="生成 D2 模拟投标文件样本")
    ap.add_argument("--no-pdf", action="store_true", help="不转 pdf（不依赖 LibreOffice）")
    args = ap.parse_args(argv)

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    SRC.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    for sample in SAMPLES:
        item = dict(sample)
        item["basic_lines"] = basic_lines(item)
        target = OUT / item["file"]
        fmt = item["format"]

        if fmt == "docx":
            build_document(item).save(target)
        elif fmt == "txt":
            target.write_text(build_text(item), encoding=item.get("encoding", "utf-8"), newline="\n")
        elif fmt == "pdf":
            if args.no_pdf:
                print(f"skip: {item['file']}（--no-pdf）")
                continue
            src = SRC / (target.stem + ".docx")
            build_document(item).save(src)
            convert_pdf(src, target)
        else:
            raise SystemExit(f"未知格式：{fmt}")

        expect = {key: item[key] for key in EXPECT_KEYS if key in item
                  and not (item.get("no_price") and key == "报价")
                  and not (item.get("no_duration") and key == "工期")}
        entries.append(
            {
                "file": item["file"],
                "kind": item["kind"],
                "format": fmt,
                "boundary": item.get("boundary"),
                "expect": expect,
            }
        )

    shutil.rmtree(SRC, ignore_errors=True)

    manifest = {
        "version": "v1",
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "note": "全部为自造虚构数据；主体名称、编号、金额均为示例，不含任何真实招投标信息。",
        "items": entries,
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"\n已生成 {len(entries)} 份样本 → {OUT}")
    for entry in entries:
        path = OUT / entry["file"]
        size = path.stat().st_size if path.exists() else 0
        print(f"  {entry['file']:<14} {entry['format']:<5} {size / 1024:6.1f} KB  {entry.get('boundary') or ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
