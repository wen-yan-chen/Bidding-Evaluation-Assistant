"""计算型风险检查（D6）：需要"算一下"才能判断的规则，不能靠关键词。

覆盖的规则：
- R12 投标报价超过最高投标限价（报价 > 限价）
- R13 投标报价低于成本（报价 < 限价 × 阈值，默认 0.60）
- R17 投标有效期不足（承诺天数 < 招标要求）
- R31 报价贴近最高限价（比值 ≥ 0.97）
- R34 分项合计与总价不一致（总价 vs 按单价汇总）
- R36 暂列金额/暂估价未按招标文件计取
- R37 报价大写与小写不一致（中文数字解析后比对）
- R38 单价 × 数量 ≠ 该项合价（参照 59/51）
- R39 报价缺漏项（必报分项对比）

每个检查返回**命中列表**（可为空）；无法判断时返回空列表并在 `reason` 中说明，
由上层决定是否展示"该规则本次不可判定"，绝不靠猜。
"""

from __future__ import annotations

import re
from typing import Any

from api import scoring

CN_DIGITS = {
    "零": 0, "〇": 0, "壹": 1, "贰": 2, "叁": 3, "肆": 4, "伍": 5,
    "陆": 6, "柒": 7, "捌": 8, "玖": 9, "一": 1, "二": 2, "两": 2, "三": 3,
    "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}
CN_UNITS = {"拾": 10, "十": 10, "佰": 100, "百": 100, "仟": 1000, "千": 1000}
CN_BIG = {"万": 10000, "亿": 100000000}

CAP_RE = re.compile(r"最高投标限价[^0-9]{0,12}([0-9][0-9,，.]*)\s*(万元|元)")
VALIDITY_RE = re.compile(r"投标有效期[^。\n]{0,30}?([0-9]{1,3})\s*个?\s*日历?[天日]")
UPPER_RE = re.compile(r"大写[：: ]\s*([零〇壹贰叁肆伍陆柒捌玖拾佰仟万亿一二三四五六七八九十百千两]+)[元圆]?整?")
LOWER_RE = re.compile(r"([0-9][0-9,，]*(?:\.[0-9]{1,2})?)\s*(万元|元)")


def cn_to_int(text: str) -> int | None:
    """中文大写金额 → 整数元。支持「壹佰贰拾捌万陆仟元整」「玖拾陆万捌仟元」等常见写法。"""
    if not text:
        return None
    text = text.replace("元整", "").replace("元", "").replace("整", "")
    total = 0
    section = 0
    number = 0
    for char in text:
        if char in CN_DIGITS:
            number = CN_DIGITS[char]
        elif char in CN_UNITS:
            section += (number or 1) * CN_UNITS[char]
            number = 0
        elif char in CN_BIG:
            section += number
            total += section * CN_BIG[char]
            section = 0
            number = 0
        else:
            continue
    return total + section + number


def _money_hit(rule_id: str, doc, page: int, start: int, end: int, **extra: Any) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "page": page,
        "char_start": start,
        "char_end": end,
        "quote": doc.slice_text(start, end),
        **extra,
    }


def _price_of(doc):  # noqa: ANN001
    field = next((f for f in doc.fields if f.name == "报价"), None)
    if field is None:
        return None, None
    return scoring.parse_price(field.value), field


def _cap_of(doc, context: dict[str, Any]) -> tuple[float | None, int | None, str]:
    """最高限价只认**文档正文里写明的值**。

    早先版本会回退到全局 context 的 max_price，实测导致大量误报：
    每份标书都有自己的限价，拿别的项目限价去比，等于凭空造出"超限价"。
    只有调用方显式传 `allow_context_cap=True`（例如已经确认是同一项目）才允许回退。
    """
    match = CAP_RE.search(doc.full_text)
    if match:
        number = float(match.group(1).replace(",", "").replace("，", ""))
        if (match.group(2) or "") == "万元":
            number *= 10000
        return number, match.start(), "document"
    if context.get("allow_context_cap") and context.get("max_price"):
        return float(context["max_price"]), None, "context"
    return None, None, "none"


def check_over_cap(doc, context: dict[str, Any]) -> list[dict[str, Any]]:
    price, field = _price_of(doc)
    cap, cap_pos, source = _cap_of(doc, context)
    if price is None or cap is None:
        return []
    if price > cap:
        start = cap_pos if cap_pos is not None else field.char_start
        end = (cap_pos + 40) if cap_pos is not None else field.char_end
        return [
            _money_hit(
                "R12", doc, doc.page_of(field.char_start),
                field.char_start, field.char_end,
                reason=f"报价 {price:,.2f} 元 > 最高限价 {cap:,.2f} 元（限价来源：{source}）",
                values={"price": price, "cap": cap, "ratio": round(price / cap, 4)},
            )
        ]
    return []


def check_below_cost(doc, context: dict[str, Any]) -> list[dict[str, Any]]:
    price, field = _price_of(doc)
    cap, _pos, source = _cap_of(doc, context)
    ratio_limit = float(context.get("below_cost_ratio", 0.60))
    if price is None or cap is None:
        return []
    ratio = price / cap
    if ratio < ratio_limit:
        return [
            _money_hit(
                "R13", doc, doc.page_of(field.char_start),
                field.char_start, field.char_end,
                reason=f"报价仅为最高限价的 {ratio:.1%}（阈值 {ratio_limit:.0%}），疑似低于成本，需投标人说明（限价来源：{source}）",
                values={"price": price, "cap": cap, "ratio": round(ratio, 4)},
            )
        ]
    return []


def check_near_cap(doc, context: dict[str, Any]) -> list[dict[str, Any]]:
    price, field = _price_of(doc)
    cap, _pos, _source = _cap_of(doc, context)
    threshold = float(context.get("near_cap_ratio", 0.97))
    if price is None or cap is None:
        return []
    ratio = price / cap
    if threshold <= ratio <= 1.0:
        return [
            _money_hit(
                "R31", doc, doc.page_of(field.char_start),
                field.char_start, field.char_end,
                reason=f"报价达到最高限价的 {ratio:.1%}（阈值 {threshold:.0%}），存在贴标嫌疑",
                values={"price": price, "cap": cap, "ratio": round(ratio, 4)},
            )
        ]
    return []


def check_validity(doc, context: dict[str, Any]) -> list[dict[str, Any]]:
    required = int(context.get("min_validity_days", 90))
    match = VALIDITY_RE.search(doc.full_text)
    if not match:
        return []
    days = int(match.group(1))
    if days < required:
        return [
            _money_hit(
                "R17", doc, doc.page_of(match.start()),
                match.start(), match.end(),
                reason=f"投标有效期 {days} 天 < 要求 {required} 天",
                values={"days": days, "required": required},
            )
        ]
    return []


def check_amount_case(doc, _context: dict[str, Any]) -> list[dict[str, Any]]:
    """大小写金额不一致：解析大写金额，与报价字段或小写金额比较。"""
    upper = UPPER_RE.search(doc.full_text)
    if not upper:
        return []
    upper_value = cn_to_int(upper.group(1))
    if not upper_value:
        return []

    price, field = _price_of(doc)
    if price is None:
        lower = LOWER_RE.search(doc.full_text)
        price = scoring.parse_price(lower.group(0)) if lower else None
    if price is None:
        return []

    if abs(upper_value - price) >= 1:
        start = upper.start()
        return [
            _money_hit(
                "R37", doc, doc.page_of(start), start, upper.end(),
                reason=f"大写金额 {upper_value:,.2f} 元 ≠ 小写 {price:,.2f} 元",
                values={"upper": upper_value, "lower": price, "diff": round(upper_value - price, 2)},
            )
        ]
    return []


def _iter_table_rows(doc):
    """按行扫描简单表格；返回 (line_start, quote, cells)。不依赖 docx 表格对象。"""
    offset = 0
    for raw in doc.full_text.splitlines(keepends=True):
        line_start = offset
        offset += len(raw)
        line = raw.rstrip("\r\n")
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        if all(set(c) <= {"-", ":", " "} for c in cells):
            continue
        yield line_start, line, cells


def _amount(cell: str) -> float | None:
    text = (cell or "").strip().replace("，", ",").replace("￥", "").replace("¥", "")
    match = re.search(r"[0-9][0-9,]*(?:\.[0-9]{1,2})?\s*(万元|元)?", text)
    if not match:
        return None
    try:
        value = float(match.group(0).replace(",", "").replace("万元", "").replace("元", "").strip())
    except ValueError:
        return None
    if "万元" in match.group(0):
        value *= 10000
    return value


def _table_header(doc) -> tuple[int, list[str]] | None:
    for start, _line, cells in _iter_table_rows(doc):
        joined = "|".join(cells)
        if ("单价" in joined or "数量" in joined or "合价" in joined or "金额" in joined):
            return start, cells
    return None


def check_total_consistency(doc, _context: dict[str, Any]) -> list[dict[str, Any]]:
    """R34：报价明细分项合计与投标总价不一致（按 87 号令 59(4) 措辞）。"""
    price, field = _price_of(doc)
    if price is None:
        return []
    amounts: list[float] = []
    total_row: tuple[int, str, list[str]] | None = None
    for start, line, cells in _iter_table_rows(doc):
        if any("合计" in c for c in cells):
            value = _amount(cells[-1])
            if value is not None:
                total_row = (start, line, cells)
            continue
        if not cells or not re.fullmatch(r"\d+", cells[0]):
            continue
        value = _amount(cells[-1])
        if value is not None:
            amounts.append(value)
    if not amounts:
        return []
    computed = sum(amounts)
    declared = total_row[1] if total_row else ""
    declared_amount = _amount(total_row[2][-1]) if total_row else None
    if abs(computed - price) < 1:
        return []
    start = total_row[0] if total_row else field.char_start
    quote = total_row[1] if total_row else doc.slice_text(field.char_start, field.char_end)
    return [
        _money_hit(
            "R34", doc, doc.page_of(start), start, start + len(quote),
            reason=f"分项合计 {computed:,.2f} 元 ≠ 投标总价 {price:,.2f} 元"
                   + (f"（表内合计 {declared_amount:,.2f} 元）" if declared_amount is not None else ""),
            values={"sum_items": round(computed, 2), "price": round(price, 2),
                    "table_total": round(declared_amount, 2) if declared_amount is not None else None},
        )
    ]


def check_unit_product(doc, _context: dict[str, Any]) -> list[dict[str, Any]]:
    """R38：单价 × 数量 ≠ 该项合价（参照 59 修正顺序 / 51 澄清）。"""
    header = _table_header(doc)
    if not header:
        return []
    _start, cells = header
    try:
        qty_idx = next(i for i, c in enumerate(cells) if "数量" in c)
        unit_idx = next(i for i, c in enumerate(cells) if "单价" in c)
        total_idx = next(i for i, c in enumerate(cells) if ("合价" in c or "金额" in c))
    except StopIteration:
        return []
    hits = []
    for start, line, row in _iter_table_rows(doc):
        if len(row) <= max(qty_idx, unit_idx, total_idx):
            continue
        if not re.fullmatch(r"\d+", row[0]):
            continue
        qty, unit, total = _amount(row[qty_idx]), _amount(row[unit_idx]), _amount(row[total_idx])
        if qty is None or unit is None or total is None:
            continue
        if abs(qty * unit - total) < 1:
            continue
        hits.append(_money_hit(
            "R38", doc, doc.page_of(start), start, start + len(line),
            reason=f"{row[1] if len(row) > 1 else row[0]}：{qty:g} × {unit:,.2f} = {qty * unit:,.2f}，表内合价 {total:,.2f}",
            values={"qty": qty, "unit_price": unit, "line_total": total, "calc": round(qty * unit, 2)},
        ))
        if len(hits) >= 3:
            break
    return hits


def check_provisional_amount(doc, _context: dict[str, Any]) -> list[dict[str, Any]]:
    """R36：暂列金额/暂估价被明确写成未计入/未计取。"""
    hits = []
    for match in re.finditer(r"[^\n]*(?:暂列金额|暂估价)[^\n]*", doc.full_text):
        line = match.group(0)
        if not any(word in line for word in ("未计入", "不计入", "未计取", "漏计", "未包含", "为0", "为 0")):
            continue
        start = match.start()
        hits.append(_money_hit(
            "R36", doc, doc.page_of(start), start, match.end(),
            reason="暂列金额/暂估价被明确写成未计入/未计取，需按招标文件核对",
            values={"line": line.strip()[:120]},
        ))
    return hits[:3]


def check_missing_items(doc, _context: dict[str, Any]) -> list[dict[str, Any]]:
    """R39：招标文件/样本写明必报分项，但报价明细缺少该项。"""
    match = re.search(r"必报分项\s*[:：]\s*([^\n]+)", doc.full_text)
    if not match:
        return []
    required = [x.strip() for x in re.split(r"[、,，;；]", match.group(1)) if x.strip()]
    if not required:
        return []
    table_items = []
    for _start, _line, cells in _iter_table_rows(doc):
        if len(cells) >= 2 and not re.fullmatch(r"\d+", cells[0]) and "合计" not in cells[0]:
            table_items.append(cells[1] if len(cells) > 1 else cells[0])
        elif len(cells) >= 2 and re.fullmatch(r"\d+", cells[0]):
            table_items.append(cells[1])
    missing = [name for name in required if not any(name in item or item in name for item in table_items)]
    if not missing:
        return []
    start = match.start()
    return [_money_hit(
        "R39", doc, doc.page_of(start), start, match.end(),
        reason=f"必报分项缺少：{'、'.join(missing)}；需按招标文件核对是否作无效投标",
        values={"required": required, "missing": missing, "table_items": table_items},
    )]


CHECKS = {
    "R12": check_over_cap,
    "R13": check_below_cost,
    "R17": check_validity,
    "R31": check_near_cap,
    "R34": check_total_consistency,
    "R36": check_provisional_amount,
    "R37": check_amount_case,
    "R38": check_unit_product,
    "R39": check_missing_items,
}
