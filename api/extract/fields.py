"""结构化字段抽取（只为 D2 的 6 个关键字段）：全部是确定性规则，不经过模型。

为什么不用 LLM 抽字段：本课题的验收要"字段准确率 ≥ 90%"和"quote 必为原文子串"，
用正则 + 逐字切片可以做到**同一输入永远同一结果**；模型抽字段一旦改写措辞，
溯源就会失效。模型的价值在后面的"解释为什么是风险"，不在这里。

每个字段都带 `{page, char_start, char_end, quote}`，并做一次自校验：
`doc.slice_text(start, end) == quote`，不成立就丢弃该字段（宁缺勿错）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from api.docmodel import Doc, SourceField

# 行首/单元格里常见的前缀噪声
LEAD = " \t\u3000:：为是"
TRAIL = " \t\u3000；;，,。"
MAX_TEXT_VALUE = 60

MONEY_RE = re.compile(r"^(?P<cur>人民币|RMB|¥|￥)?\s*(?P<num>[0-9][0-9,，]*(?:\.[0-9]{1,2})?)\s*(?P<unit>万元|元|万)?")
DURATION_RE = re.compile(
    r"^(?:为|共|计|约)?\s*([0-9]{1,4})\s*(个?日历天|个?日历日|天|日|个月|月|周|年)"
)


@dataclass(frozen=True)
class FieldSpec:
    name: str
    patterns: tuple[str, ...]
    kind: str  # text | money | duration


FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec(
        "项目名称",
        (
            r"(?:项目名称|采购项目名称|招标项目名称|工程名称)\s*[:：]",
        ),
        "text",
    ),
    FieldSpec(
        "项目编号",
        (
            r"(?:项目编号|招标编号|采购编号|标书编号|项目编码|招标文件编号)\s*[:：]",
        ),
        "text",
    ),
    FieldSpec(
        "采购人",
        (
            r"(?:采购人名称|采购人|招标人|采购单位|招标单位|采购机构)\s*[:：]",
        ),
        "text",
    ),
    FieldSpec(
        "投标人",
        (
            r"(?:投标人名称|投标单位名称|供应商名称|投标人|投标单位|供应商)"
            r"(?!资格|须知|数量|要求|授权|代表|名称要求)\s*[:：]",
        ),
        "text",
    ),
    FieldSpec(
        "报价",
        (
            r"(?:投标报价|投标总价|总报价|报价|投标价|合同报价)\s*[:：]?",
        ),
        "money",
    ),
    FieldSpec(
        "工期",
        (
            r"(?:计划工期|履约期限|服务期限|工期|服务期|交货期|交付期)\s*[:：]?",
        ),
        "duration",
    ),
)


def _line_end(text: str, start: int, cap: int = 200) -> int:
    newline = text.find("\n", start)
    if newline == -1:
        newline = len(text)
    return min(newline, start + cap)


def _extract_one(doc: Doc, spec: FieldSpec) -> SourceField | None:
    text = doc.full_text
    for pattern in spec.patterns:
        for match in re.finditer(pattern, text, re.M):
            label_start = match.start()
            rest_start = match.end()
            rest = text[rest_start : _line_end(text, rest_start)]
            if not rest.strip():
                continue

            leading = len(rest) - len(rest.lstrip(LEAD))
            rest2 = rest[leading:]

            if spec.kind == "money":
                money = MONEY_RE.match(rest2)
                if not money:
                    continue
                number = money.group("num").replace("，", ",")
                unit = money.group("unit") or ""
                if not unit and money.group("cur") in ("¥", "￥"):
                    unit = "元"  # ￥968,000.00 这种写法在国内标书里很常见
                if not unit:  # 没有单位的数字不当报价（可能是编号、页码）
                    continue
                value = f"{number} {unit}"
                used = leading + money.end()
            elif spec.kind == "duration":
                duration = DURATION_RE.match(rest2)
                if not duration:
                    continue
                value = f"{duration.group(1)} {duration.group(2)}"
                used = leading + duration.end()
            else:
                trimmed = rest2.rstrip(TRAIL)
                if not trimmed.strip():
                    continue
                if len(trimmed) > MAX_TEXT_VALUE:
                    trimmed = trimmed[:MAX_TEXT_VALUE]
                value = trimmed.strip()
                used = leading + len(trimmed)

            end = rest_start + used
            # 去掉尾部空白，保证 quote 与切片严格一致
            while end > rest_start and text[end - 1] in " \t\u3000":
                end -= 1
            if end <= label_start:
                continue

            quote = doc.slice_text(label_start, end)
            if not quote.strip():
                continue
            # 自校验：切片必须逐字等于 quote，否则宁可不要这个字段
            if text[label_start:end] != quote:
                continue

            return SourceField(
                name=spec.name,
                value=value,
                page=doc.page_of(label_start),
                char_start=label_start,
                char_end=end,
                quote=quote,
            )
    return None


def extract_fields(doc: Doc) -> list[SourceField]:
    """抽取 6 个关键字段；抽不到就不返回，不猜、不补默认值。"""
    fields: list[SourceField] = []
    for spec in FIELD_SPECS:
        field = _extract_one(doc, spec)
        if field is not None:
            fields.append(field)
    return fields


def field_values(doc: Doc) -> dict[str, str]:
    """给评测与前端用的扁平视图。"""
    return {f.name: f.value for f in doc.fields}
