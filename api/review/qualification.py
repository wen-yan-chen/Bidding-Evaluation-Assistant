"""资格性核验（D5）：把 R01–R10 的“资质门槛”规则落成三态判定。

三态定义（手册 §5.2 的"缺失/效力不足/合规"改造）：
- `provided`     ：全文检出该资格材料的表述，且当前句没有“未提供/过期/失效”等否定信号；
- `insufficient` ：检出表述，但同一句出现“过期/失效/无效/不满足/不具备”等效力信号，
                   需要人工核对原件；
- `missing`      ：全文没有出现该材料名称，或同一句明确写“未提供/未附/无××”，
                   按缺失处理。

关键修正（2026-11-16 测评后）：
1. 否定信号按**句子**取，不再用 ±24 字窗口，避免相邻句的“无”跨行误伤；
2. 不再用单字“无”作为通用否定词，只匹配“无{材料名}/没有{材料名}”，
   避免把“无重大违法记录”“无异议”等合规否定式判成“效力不足”；
3. “未提供/未附/未提交/未加盖/缺失”优先归 `missing`，不再归 `insufficient`；
4. “无需提供/不需提供/不要求提供/免于提供”单独标记 `applicable=False`，
   仍按 `missing` 计数，但在 `note` 中说明“不适用，需按招标文件确认”；
5. R07 的“无重大违法记录/无行贿犯罪记录/无违法记录”是合规声明，判 `provided`。

注意：这是**纸面核验**，只回答“投标文件里写没写、写的是不是无效”，不回答“证件真伪”。
后者超出文本能力范围，报告里必须写明“需核对原件”。
"""

from __future__ import annotations

from typing import Any

from api import rules as rules_api

# 明确表示“没有提供”的词：归 missing
EXPLICIT_MISSING = ("未提供", "未附", "未提交", "未加盖", "缺失", "没有")
# 表示“有材料但效力有问题”的词：归 insufficient
INVALID = ("过期", "失效", "无效", "不满足", "不具备", "不符合")
# 文档声明“无需提供”：按 missing 计数，但 applicable=False
NOT_REQUIRED = ("无需提供", "不需提供", "不要求提供", "免于提供")
# R07 的合规否定式：是“已声明无违法记录”，不是“效力不足”
COMPLIANT_R07 = ("无重大违法记录", "无行贿犯罪记录", "无违法记录", "无不良记录", "无重大税收违法")
SENTENCE_ENDS = "。；;\n"


def _sentence_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    """取命中所在的句子区间；只用句号/分号/换行做边界，不用逗号（避免切碎“未提供，且…”）。"""
    left = 0
    for char in SENTENCE_ENDS:
        pos = text.rfind(char, 0, start)
        if pos >= left:
            left = pos + 1
    right = len(text)
    for char in SENTENCE_ENDS:
        pos = text.find(char, end)
        if pos != -1 and pos < right:
            right = pos
    return left, right


def _hit(doc, pattern: str) -> dict[str, Any] | None:  # noqa: ANN001
    start = doc.full_text.find(pattern)
    if start < 0:
        return None
    end = start + len(pattern)
    sentence_start, sentence_end = _sentence_bounds(doc.full_text, start, end)
    return {
        "page": doc.page_of(start),
        "char_start": start,
        "char_end": end,
        "quote": doc.slice_text(start, end),
        "sentence": doc.slice_text(sentence_start, sentence_end).strip(),
        "sentence_start": sentence_start,
        "sentence_end": sentence_end,
    }


def _signals(sentence: str, matched: str) -> list[str]:
    """返回命中的否定/效力信号，供 note 与调试使用。"""
    found: list[str] = []
    for word in NOT_REQUIRED + EXPLICIT_MISSING + INVALID:
        if word in sentence:
            found.append(word)
    if f"无{matched}" in sentence:
        found.append(f"无{matched}")
    if f"没有{matched}" in sentence:
        found.append(f"没有{matched}")
    return sorted(set(found))


def _classify(rule: Any, evidence: dict[str, Any]) -> tuple[str, str, bool, list[str]]:
    """返回 (state, note, applicable, signals)。"""
    sentence = str(evidence.get("sentence") or "")
    matched = str(evidence.get("quote") or "")
    signals = _signals(sentence, matched)

    # 明确“无需提供”：不适用，但仍按 missing 计数，避免三态计数被打破
    if any(word in sentence for word in NOT_REQUIRED):
        return (
            "missing",
            "文档声明无需提供（不适用），建议按招标文件确认是否应提供；文本核验不替代原件核验",
            False,
            signals,
        )

    # 明确“未提供/未附/缺失”优先归 missing
    if any(word in sentence for word in EXPLICIT_MISSING):
        return "missing", "同一句明确写了未提供/未附/缺失，建议要求澄清或补充", True, signals

    # R07：无重大违法记录等是合规声明，不是效力不足
    if rule.id == "R07" and any(word in sentence for word in COMPLIANT_R07):
        return (
            "provided",
            "检出无重大违法记录/无违法记录声明；仍需核对声明原件与查询记录",
            True,
            signals,
        )

    # 材料名前的“无/没有”：如“无营业执照”
    if f"无{matched}" in sentence or f"没有{matched}" in sentence:
        return "missing", "同一句明确写了无该材料，建议要求澄清或补充", True, signals

    # 有材料但过期/失效/无效：归 insufficient
    if any(word in sentence for word in INVALID):
        return "insufficient", "检出相关表述，但同一句含过期/失效/无效信号，需核对原件效力", True, signals

    return "provided", "检出相关表述，仍需核对证件编号与有效期（文本核验不替代原件核验）", True, signals


def check(doc, project_type: str = "unknown") -> dict[str, Any]:  # noqa: ANN001
    """对一份文档做资格性核验。`project_type` 用于工程/货物服务门控；unknown 不硬判。"""
    qualifications = [r for r in rules_api.load_rules() if r.category == "资质门槛"]
    items: list[dict[str, Any]] = []
    not_applicable_rule_ids: list[str] = []

    for rule in qualifications:
        if not rules_api.rule_applies(rule, project_type):
            not_applicable_rule_ids.append(rule.id)
            continue
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
            applicable = True
            signals: list[str] = []
            sentence = ""
        else:
            state, note, applicable, signals = _classify(rule, evidence)
            sentence = evidence.get("sentence", "")

        item = {
            "rule_id": rule.id,
            "item": rule.title.replace("未提供", "").replace("缺失", "").strip() or rule.title,
            "title": rule.title,
            "level": rule.level,
            "state": state,
            "applicable": applicable,
            "page": evidence["page"] if evidence else None,
            "char_start": evidence["char_start"] if evidence else None,
            "char_end": evidence["char_end"] if evidence else None,
            "quote": evidence["quote"] if evidence else "",
            "sentence": sentence,
            "matched_pattern": pattern_used,
            "signals": signals,
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
        "not_applicable_rule_ids": not_applicable_rule_ids,
        "passed": not missing_items,
        "conclusion": (
            "资格性材料齐备（文本层面），仍需核对原件"
            if not missing_items
            else f"存在 {len(missing_items)} 项需人工复核的资格材料"
        ),
        "note": "文本核验只判断「是否提供/是否自相矛盾」，不判断证件真伪；不得据此作出废标结论。",
    }
