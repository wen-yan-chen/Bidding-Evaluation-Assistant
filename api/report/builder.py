"""报告数据装配（D7）：把一次评审的 JSON 变成九章结构化的报告数据。

一条硬规则：**报告只读 `/api/review` 的结果，不重新算分**。
否则"报告数值 = 页面数值"这条验收随时会被打破。

九章结构（对应手册 §4.7 与交付要求第 5 条）：
1. 封面与文档信息
2. 评审依据与口径（细则指纹 + 规则指纹）
3. 项目与投标人信息（字段 + 溯源）
4. 资格性核验（三态）
5. 分项评分（得分 / 扣分理由 / 溯源）
6. 风险清单（等级 / 页码 / 原文 / 依据）
7. 合同摘要（六要素：标的 / 金额 / 工期 / 付款 / 违约 / 争议解决）
8. 结论与建议（含人工复核事项）
9. 免责声明
"""

from __future__ import annotations

from typing import Any

from api import config

CONTRACT_ITEMS = [
    ("付款", ("付款", "支付", "结算")),
    ("违约责任", ("违约", "赔偿", "逾期")),
    ("争议解决", ("争议", "仲裁", "诉讼", "管辖")),
]


def _contract_summary(doc) -> list[dict[str, Any]]:  # noqa: ANN001
    """合同摘要六要素：能从字段/条款抽到的给原文，抽不到的如实写「未约定」。"""
    fields = {f.name: f for f in doc.fields}
    items: list[dict[str, Any]] = []

    def from_field(name: str, label: str) -> None:
        field = fields.get(name)
        if field is not None:
            items.append(
                {
                    "item": label,
                    "value": field.value,
                    "page": field.page,
                    "quote": field.quote,
                    "status": "已抽取",
                }
            )
        else:
            items.append({"item": label, "value": "未约定", "page": None, "quote": "", "status": "未检出"})

    from_field("项目名称", "标的（项目名称）")
    from_field("报价", "合同金额（投标报价）")
    from_field("工期", "工期")

    for label, keywords in CONTRACT_ITEMS:
        hit = None
        for clause in doc.clauses:
            for keyword in keywords:
                position = clause.text.find(keyword)
                if position >= 0:
                    start = clause.char_start + position
                    hit = {
                        "item": label,
                        "value": clause.title or keyword,
                        "page": doc.page_of(start),
                        "quote": doc.slice_text(start, min(start + 40, len(doc.full_text))).replace("\n", " "),
                        "status": "疑似条款（需核对）",
                    }
                    break
            if hit:
                break
        items.append(hit or {"item": label, "value": "未约定", "page": None, "quote": "", "status": "未检出"})
    return items


def build(review: dict[str, Any], doc) -> dict[str, Any]:  # noqa: ANN001
    """把 review JSON + Doc 组装成报告数据（纯数据，渲染交给 docx/pdf）。"""
    summary = review.get("summary") or {}
    profile = review.get("profile") or {}
    qualification = review.get("qualification") or {}
    scoring = review.get("scoring") or {}
    risks = review.get("risks") or []

    high = [r for r in risks if r.get("level") == "高"]
    medium = [r for r in risks if r.get("level") == "中"]
    low = [r for r in risks if r.get("level") == "低"]

    recommendations: list[str] = []
    for item in (qualification.get("items") or []):
        if item.get("state") != "provided":
            recommendations.append(
                f"{item['rule_id']} {item.get('item', '')}："
                + ("建议要求澄清或补充材料" if item.get("state") == "missing" else "建议核对原件效力")
            )
    for deduction in scoring.get("deductions") or []:
        recommendations.append(f"{deduction['item_id']} 扣 {deduction['lost']} 分：{deduction['reason']}")
    for risk in high:
        recommendations.append(f"{risk['rule_id']}（高）第 {risk['page']} 页：{risk.get('reason') or risk['quote']}")

    return {
        "meta": {
            "review_id": review.get("review_id"),
            "created_at": review.get("created_at"),
            "doc_id": review.get("doc_id"),
            "file_name": review.get("file_name"),
            "pages": len(doc.pages),
            "page_source": doc.page_source,
            "parse_status": doc.parse_status,
            "degraded": doc.degraded,
            "disclaimer": review.get("disclaimer") or config.DISCLAIMER,
        },
        "basis": {
            "profile_id": profile.get("id"),
            "profile_name": profile.get("name"),
            "profile_version": profile.get("version"),
            "profile_digest": profile.get("digest"),
            "rule_digest": review.get("rule_digest"),
            "total_full": scoring.get("total_full"),
        },
        "project": {
            "fields": [
                {"name": f.name, "value": f.value, "page": f.page, "quote": f.quote}
                for f in doc.fields
            ]
        },
        "qualification": {
            "counts": qualification.get("counts") or {},
            "items": qualification.get("items") or [],
            "note": qualification.get("note", ""),
        },
        "scoring": {
            "items": scoring.get("items") or [],
            "by_category": scoring.get("by_category") or {},
            "total": scoring.get("total"),
            "total_full": scoring.get("total_full"),
            "deductions": scoring.get("deductions") or [],
        },
        "risks": {
            "items": risks,
            "counts": {"高": len(high), "中": len(medium), "低": len(low), "合计": len(risks)},
        },
        "contract": {"items": _contract_summary(doc)},
        "conclusion": {
            "text": summary.get("conclusion", ""),
            "recommendations": recommendations,
        },
    }
