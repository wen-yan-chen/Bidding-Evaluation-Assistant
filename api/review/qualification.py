"""资格性核验（D5）：把 R01–R10 的「资质门槛」规则落成三态判定。

三态定义（手册 §5.2 的"缺失/效力不足/合规"改造）：
- `provided`     ：全文检出该资格材料的表述，且上下文没有否定词；
- `insufficient` ：检出了表述，但同一句里出现"未提供/无效/过期/缺失"等否定信号，
                   或材料名称出现在"无需提供"的说明里 —— 需要人工核对原件；
- `missing`      ：全文完全没有出现该材料名称 —— 按缺失处理。

注意：这是**纸面核验**，只回答"投标文件里写没写、写的是不是无效"，不回答"证件真伪"。
后者超出文本能力范围，报告里必须写明"需核对原件"。
"""

from __future__ import annotations

from typing import Any

from api import rules as rules_api

NEGATIVE = ("未提供", "未附", "无", "缺失", "过期", "失效", "无效", "不满足", "不具备", "未加盖")
CONTEXT_WINDOW = 24


def _hit(doc, pattern: str) -> dict[str, Any] | None:  # noqa: ANN001
    start = doc.full_text.find(pattern)
    if start < 0:
        return None
    end = start + len(pattern)
    context = doc.slice_text(max(0, start - CONTEXT_WINDOW), min(len(doc.full_text), end + CONTEXT_WINDOW))
    return {
        "page": doc.page_of(start),
        "char_start": start,
        "char_end": end,
        "quote": doc.slice_text(start, end),
        "context": context,
    }


def check(doc) -> dict[str, Any]:  # noqa: ANN001
    """对一份文档做资格性核验。返回逐项结论 + 汇总。"""
    qualifications = [r for r in rules_api.load_rules() if r.category == "资质门槛"]
    items: list[dict[str, Any]] = []

    for rule in qualifications:
        evidence = None
        pattern_used = ""
        for pattern in rule.patterns:
            found = _hit(doc, pattern)
            if found is not None:
                evidence = found
                pattern_used = pattern
                break

        if evidence is None:
            state = "missing"
            note = "全文未检出该资格材料，建议要求投标人澄清或补充"
        else:
            context = evidence["context"]
            if any(word in context for word in NEGATIVE):
                state = "insufficient"
                note = "检出相关表述，但上下文含否定/失效信号，需核对原件"
            else:
                state = "provided"
                note = "检出相关表述，仍需核对证件编号与有效期（文本核验不替代原件核验）"

        item = {
            "rule_id": rule.id,
            "item": rule.title.replace("未提供", "").replace("缺失", "").strip() or rule.title,
            "title": rule.title,
            "level": rule.level,
            "state": state,
            "page": evidence["page"] if evidence else None,
            "char_start": evidence["char_start"] if evidence else None,
            "char_end": evidence["char_end"] if evidence else None,
            "quote": evidence["quote"] if evidence else "",
            "matched_pattern": pattern_used,
            "legal_basis": rule.legal_basis,
            "basis_status": rule.basis_status,
            "note": note,
        }
        items.append(item)

    counts = {"provided": 0, "insufficient": 0, "missing": 0}
    for item in items:
        counts[item["state"]] += 1

    missing_items = [i for i in items if i["state"] != "provided"]
    return {
        "items": items,
        "counts": counts,
        "total": len(items),
        "passed": not missing_items,
        "conclusion": (
            "资格性材料齐备（文本层面），仍需核对原件"
            if not missing_items
            else f"存在 {len(missing_items)} 项需人工复核的资格材料"
        ),
        "note": "文本核验只判断「是否提供/是否自相矛盾」，不判断证件真伪；不得据此作出废标结论。",
    }
