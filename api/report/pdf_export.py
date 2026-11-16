"""pdf 报告渲染（D7）：reportlab + 内置 CID 中文字体，不依赖 LibreOffice。

为什么不用 LibreOffice：镜像里装它要多 400–600 MB、且要连 Debian 源；
reportlab 的 `STSong-Light`（Adobe CID 字体）在 PDF 里引用标准中文字体，
常见阅读器（Edge / Chrome / Acrobat）都能正常显示，体积也可控。

与 docx 版共用同一份 `builder` 数据，保证两种格式数值一致。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT = "STSong-Light"
pdfmetrics.registerFont(UnicodeCIDFont(FONT))

STYLE_TITLE = ParagraphStyle("title", fontName=FONT, fontSize=20, leading=26, alignment=1, spaceAfter=6)
STYLE_SUB = ParagraphStyle("sub", fontName=FONT, fontSize=10, leading=14, alignment=1, textColor=colors.HexColor("#5B667C"))
STYLE_H = ParagraphStyle("h", fontName=FONT, fontSize=13, leading=18, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#1F4FD8"))
STYLE_BODY = ParagraphStyle("body", fontName=FONT, fontSize=9.5, leading=14, spaceAfter=3)
STYLE_SMALL = ParagraphStyle("small", fontName=FONT, fontSize=8, leading=11, textColor=colors.HexColor("#5B667C"))
STYLE_CELL = ParagraphStyle("cell", fontName=FONT, fontSize=7.5, leading=10)
STYLE_CELL_B = ParagraphStyle("cellb", fontName=FONT, fontSize=7.5, leading=10, textColor=colors.white)


def _p(text: Any, style: ParagraphStyle = STYLE_BODY) -> Paragraph:
    safe = str(text if text is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(safe, style)


def _table(headers: list[str], rows: list[list[Any]], widths: list[float]) -> Table:
    data = [[_p(h, STYLE_CELL_B) for h in headers]]
    for row in rows:
        data.append([_p(cell, STYLE_CELL) for cell in row])
    table = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4FD8")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D4EA")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FD")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


def _page_decor(canvas, doc, meta: dict[str, Any]) -> None:
    canvas.saveState()
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(colors.HexColor("#5B667C"))
    canvas.drawString(2 * cm, 1.2 * cm, meta["disclaimer"])
    canvas.drawRightString(19 * cm, 1.2 * cm, f"第 {canvas.getPageNumber()} 页")
    canvas.drawString(2 * cm, 28.2 * cm, f"招投标评审报告　{meta['review_id']}")
    canvas.restoreState()


def render(data: dict[str, Any], out_path: Path) -> Path:
    meta = data["meta"]
    story: list[Any] = [
        Spacer(1, 2.2 * cm),
        _p("招投标评审报告", STYLE_TITLE),
        _p(meta["file_name"], STYLE_SUB),
        Spacer(1, 0.8 * cm),
        _p("一、封面与文档信息", STYLE_H),
    ]

    story.append(
        _table(
            ["报告信息", "内容"],
            [
                ["评审编号", meta["review_id"]],
                ["生成时间", meta["created_at"]],
                ["文档", f"{meta['file_name']}（{meta['doc_id']}）"],
                ["项目类型", {"engineering": "工程类（招标投标法体系）", "goods_services": "货物/服务类（政府采购体系）"}.get(meta.get("project_type"), "未指定（通用口径）")],
                ["页数 / 解析状态", f"{meta['pages']} 页 / {meta['parse_status']}"],
                ["页码来源", "估算（docx 无分页符）" if meta["page_source"] == "estimated" else "精确（PDF/分页符）"],
                ["说明", "；".join(meta.get("degraded") or []) or "无"],
            ],
            widths=[3, 13],
        )
    )

    story.append(_p("二、评审依据与口径", STYLE_H))
    basis = data["basis"]
    story.append(
        _table(
            ["项", "值"],
            [
                ["评分细则", f"{basis['profile_name']}（{basis['profile_id']}）"],
                ["细则版本 / 指纹", f"{basis.get('profile_version') or '-'} / {basis['profile_digest']}"],
                ["规则库指纹", basis["rule_digest"]],
                ["满分", str(basis["total_full"])],
            ],
            widths=[3, 13],
        )
    )

    story.append(_p("三、项目与投标人信息", STYLE_H))
    fields = data["project"]["fields"]
    story.append(
        _table(
            ["字段", "值", "页码", "原文片段"],
            [[f["name"], f["value"], f"第 {f['page']} 页", f["quote"]] for f in fields]
            or [["未抽取到字段", "-", "-", "-"]],
            widths=[2.6, 5.4, 1.6, 6.4],
        )
    )

    story.append(_p("四、资格性核验", STYLE_H))
    counts = data["qualification"]["counts"]
    story.append(_p(f"已提供 {counts.get('provided', 0)} 项 ｜ 效力不足 {counts.get('insufficient', 0)} 项 ｜ 缺失 {counts.get('missing', 0)} 项"))
    state_label = {"provided": "已提供", "insufficient": "效力不足", "missing": "缺失"}
    story.append(
        _table(
            ["规则", "材料", "状态", "页码", "原文片段", "依据"],
            [
                [
                    i["rule_id"],
                    i.get("item", ""),
                    state_label.get(i["state"], i["state"]) + ("（不适用）" if i.get("applicable") is False else ""),
                    f"第 {i['page']} 页" if i.get("page") else "-",
                    i.get("quote") or "-",
                    i.get("legal_basis") or "未检索到权威依据",
                ]
                for i in data["qualification"]["items"]
            ],
            widths=[1.2, 3, 1.6, 1.4, 3.6, 5.2],
        )
    )

    story.append(_p("五、分项评分", STYLE_H))
    scoring = data["scoring"]
    story.append(_p(f"总分 {scoring['total']} / {scoring['total_full']}", STYLE_BODY))
    story.append(
        _table(
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
            widths=[1.2, 3, 2, 5.4, 5.4],
        )
    )
    for deduction in scoring.get("deductions") or []:
        story.append(_p(f"{deduction['item_id']} 扣 {deduction['lost']} 分：{deduction['reason']}", STYLE_SMALL))
    for item in scoring.get("by_category", {}).items():
        pass

    story.append(_p("六、风险清单", STYLE_H))
    rc = data["risks"]["counts"]
    story.append(_p(f"高 {rc['高']} 条 ｜ 中 {rc['中']} 条 ｜ 低 {rc['低']} 条 ｜ 合计 {rc['合计']} 条"))
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
        story.append(_table(["规则", "等级", "页码", "原文片段", "依据", "说明"], risk_rows, widths=[1.2, 1.2, 1.6, 4, 5.2, 4.4]))
    else:
        story.append(_p("本次未命中可自动检测的风险规则。未命中不等于无风险，人工核对类规则见下。", STYLE_SMALL))
    story.append(
        _p(
            "需人工核对：R01、R02、R03、R05、R06、R07、R08、R10、R11、R40（detect=manual）；"
            "暂不支持自动检测：R25、R32、R33、R34、R36、R38、R39。最高限价类规则仅在文档正文写明限价时判定。",
            STYLE_SMALL,
        )
    )

    story.append(_p("七、合同摘要（六要素）", STYLE_H))
    story.append(
        _table(
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
            widths=[2.6, 5, 1.4, 5.4, 2.6],
        )
    )

    story.append(_p("八、结论与建议", STYLE_H))
    story.append(_p(data["conclusion"]["text"]))
    for index, item in enumerate(data["conclusion"]["recommendations"], start=1):
        story.append(_p(f"{index}. {item}", STYLE_SMALL))

    story.append(PageBreak())
    story.append(_p("九、免责声明", STYLE_H))
    story.append(_p("本报告由系统依据模型与规则自动生成，仅作为招投标评审的辅助参考，不构成最终评审结论；"))
    story.append(_p("文件解析、字段抽取、评分与风险提示均可能存在误差，须由评标委员会复核确认。"))
    story.append(Spacer(1, 0.4 * cm))
    story.append(_p(meta["disclaimer"], ParagraphStyle("warn", fontName=FONT, fontSize=11, leading=16, alignment=1, textColor=colors.HexColor("#B02A1E"))))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2.0 * cm,
        title=f"招投标评审报告 {meta['review_id']}",
        author="招投标评审助手",
    )
    doc.build(story, onFirstPage=lambda c, d: _page_decor(c, d, meta), onLaterPages=lambda c, d: _page_decor(c, d, meta))
    return out_path
