"""docx 报告渲染（D7）：九章 + 表格 + 页脚免责声明与页码。

只做"数据 → 版式"，不做任何计算；所有数值来自 `builder.build()` 的输出，
从而保证"报告数值 = 页面数值"。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BODY_FONT = "宋体"
HEAD_FONT = "微软雅黑"
INK = RGBColor(0x1B, 0x24, 0x38)
MUTED = RGBColor(0x5B, 0x66, 0x7C)
ACCENT = RGBColor(0x1F, 0x4F, 0xD8)
BAD = RGBColor(0xB0, 0x2A, 0x1E)


def _set_font(run, name: str, size: float, bold: bool = False, color: RGBColor = INK) -> None:
    run.font.name = name
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:eastAsia"), name)
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)


def _para(doc, text: str, size: float = 10.5, bold: bool = False, color: RGBColor = INK,
          align: int | None = None, space_after: float = 4) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.35
    if align is not None:
        p.alignment = align
    _set_font(p.add_run(text), BODY_FONT, size, bold, color)


def _heading(doc, text: str, level: int = 1) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10 if level == 1 else 8)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    _set_font(p.add_run(text), HEAD_FONT, 13 if level == 1 else 11.5, True, ACCENT if level == 1 else INK)


def _cell(cell, text: str, size: float = 8.5, bold: bool = False,
          color: RGBColor = INK) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    _set_font(p.add_run(str(text)), BODY_FONT, size, bold, color)


def _shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def _table(doc, headers: list[str], rows: list[list[str]], widths: list[float] | None = None) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    total = 16.6
    weights = widths or [1] * len(headers)
    scale = total / sum(weights)
    for index, header in enumerate(headers):
        cell = table.rows[0].cells[index]
        _cell(cell, header, 8.5, True)
        _shade(cell, "EAF0FF")
        cell.width = Cm(weights[index] * scale)
    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            _cell(cells[index], value)
            cells[index].width = Cm(weights[index] * scale)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def _footer(doc, disclaimer: str) -> None:
    footer = doc.sections[0].footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_font(footer.add_run(f"{disclaimer}　　— 第 "), BODY_FONT, 8, False, MUTED)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    run = OxmlElement("w:r")
    text = OxmlElement("w:t")
    text.text = "1"
    run.append(text)
    fld.append(run)
    footer._p.append(fld)
    _set_font(footer.add_run(" 页 —"), BODY_FONT, 8, False, MUTED)


def _header(doc, text: str) -> None:
    header = doc.sections[0].header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _set_font(header.add_run(text), BODY_FONT, 8, False, MUTED)


def render(data: dict[str, Any], out_path: Path) -> Path:
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.left_margin = section.right_margin = Cm(2.0)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(1.8)

    meta = data["meta"]
    _footer(doc, meta["disclaimer"])
    _header(doc, f"招投标评审报告　{meta['review_id']}")

    # 封面标题
    _para(doc, "招投标评审报告", 22, True, INK, WD_ALIGN_PARAGRAPH.CENTER, 6)
    _para(doc, meta["file_name"], 12, False, MUTED, WD_ALIGN_PARAGRAPH.CENTER, 16)

    _table(
        doc,
        ["报告信息", "内容"],
        [
            ["评审编号", meta["review_id"]],
            ["生成时间", meta["created_at"]],
            ["文档", f"{meta['file_name']}（{meta['doc_id']}）"],
            ["页数 / 解析状态", f"{meta['pages']} 页 / {meta['parse_status']}"],
            ["页码来源", "估算（docx 无分页符）" if meta["page_source"] == "estimated" else "精确（PDF/分页符）"],
            ["说明", "；".join(meta.get("degraded") or []) or "无"],
        ],
        widths=[2, 8],
    )

    # 二、评审依据
    _heading(doc, "二、评审依据与口径")
    basis = data["basis"]
    _table(
        doc,
        ["项", "值"],
        [
            ["评分细则", f"{basis['profile_name']}（{basis['profile_id']}）"],
            ["细则版本 / 指纹", f"{basis.get('profile_version') or '-'} / {basis['profile_digest']}"],
            ["规则库指纹", basis["rule_digest"]],
            ["满分", str(basis["total_full"])],
        ],
        widths=[2, 8],
    )

    # 三、项目与投标人信息
    _heading(doc, "三、项目与投标人信息")
    fields = data["project"]["fields"]
    _table(
        doc,
        ["字段", "值", "页码", "原文片段"],
        [[f["name"], f["value"], f"第 {f['page']} 页", f["quote"]] for f in fields] or [["未抽取到字段", "-", "-", "-"]],
        widths=[2, 5, 2, 6],
    )

    # 四、资格性核验
    _heading(doc, "四、资格性核验")
    counts = data["qualification"]["counts"]
    _para(doc, f"已提供 {counts.get('provided', 0)} 项 ｜ 效力不足 {counts.get('insufficient', 0)} 项 ｜ 缺失 {counts.get('missing', 0)} 项", 10)
    state_label = {"provided": "已提供", "insufficient": "效力不足", "missing": "缺失"}
    _table(
        doc,
        ["规则", "材料", "状态", "页码", "原文片段", "依据"],
        [
            [
                i["rule_id"],
                i.get("item", ""),
                state_label.get(i["state"], i["state"]),
                f"第 {i['page']} 页" if i.get("page") else "-",
                i.get("quote") or "-",
                i.get("legal_basis") or "未检索到权威依据",
            ]
            for i in data["qualification"]["items"]
        ],
        widths=[1, 2.4, 1.4, 1.2, 3, 4],
    )
    _para(doc, data["qualification"].get("note") or "", 8.5, False, MUTED)

    # 五、分项评分
    _heading(doc, "五、分项评分")
    scoring = data["scoring"]
    _para(doc, f"总分 {scoring['total']} / {scoring['total_full']}", 11, True)
    _table(
        doc,
        ["分项", "名称", "得分/满分", "理由", "溯源"],
        [
            [
                i["item_id"],
                i["name"],
                f"{i['score']} / {i['full_score']}",
                i["reason"],
                f"第 {i['evidence']['page']} 页「{i['evidence']['quote']}」" if i.get("evidence") else "-",
            ]
            for i in scoring["items"]
        ],
        widths=[1, 2.4, 1.6, 4.6, 4],
    )
    if scoring.get("deductions"):
        _para(doc, "扣分汇总：" + "；".join(f"{d['item_id']} 扣 {d['lost']} 分（{d['reason']}）" for d in scoring["deductions"]), 9)

    # 六、风险清单
    _heading(doc, "六、风险清单")
    risk_counts = data["risks"]["counts"]
    _para(doc, f"高 {risk_counts['高']} 条 ｜ 中 {risk_counts['中']} 条 ｜ 低 {risk_counts['低']} 条 ｜ 合计 {risk_counts['合计']} 条", 10)
    risk_rows = [
        [
            r["rule_id"],
            r["level"],
            f"第 {r['page']} 页",
            r["quote"],
            r.get("legal_basis") or "未检索到权威依据",
            r.get("reason") or r.get("title", ""),
        ]
        for r in data["risks"]["items"]
    ]
    if risk_rows:
        _table(doc, ["规则", "等级", "页码", "原文片段", "依据", "说明"], risk_rows, widths=[1, 1, 1.2, 3, 4, 4])
    else:
        _para(doc, "本次未命中可自动检测的风险规则。未命中不等于无风险，人工核对类规则见下。", 9, False, MUTED)
    _para(
        doc,
        "需人工核对：R01、R02、R03、R05、R06、R07、R08、R10、R11、R40（detect=manual）；"
        "暂不支持自动检测：R25、R32、R33、R34、R36、R38、R39。"
        "最高限价类规则仅在文档正文写明限价时判定。",
        8.5,
        False,
        MUTED,
    )

    # 七、合同摘要
    _heading(doc, "七、合同摘要（六要素）")
    _table(
        doc,
        ["要素", "内容", "页码", "原文片段", "状态"],
        [
            [
                c["item"],
                c["value"],
                f"第 {c['page']} 页" if c.get("page") else "-",
                c.get("quote") or "-",
                c["status"],
            ]
            for c in data["contract"]["items"]
        ],
        widths=[2, 4, 1.2, 4, 2],
    )

    # 八、结论与建议
    _heading(doc, "八、结论与建议")
    _para(doc, data["conclusion"]["text"], 10)
    for index, item in enumerate(data["conclusion"]["recommendations"], start=1):
        _para(doc, f"{index}. {item}", 9.5)

    # 九、免责声明
    _heading(doc, "九、免责声明")
    _para(doc, "本报告由系统依据模型与规则自动生成，仅作为招投标评审的辅助参考，不构成最终评审结论；", 9.5)
    _para(doc, "文件解析、字段抽取、评分与风险提示均可能存在误差，须由评标委员会复核确认。", 9.5)
    _para(doc, meta["disclaimer"], 10.5, True, BAD, WD_ALIGN_PARAGRAPH.CENTER, 10)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path)
    return out_path
