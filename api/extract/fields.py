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
    FieldSpec(
        "资质清单",
        (r"(?m)^[ \t]*(?:#{1,6}[ \t]*)?(?:资质清单|资格清单|资格证明材料清单)[ \t]*[:：]?[ \t]*$",),
        "qual_list",
    ),
    FieldSpec(
        "业绩清单",
        (r"(?m)^[ \t]*(?:#{1,6}[ \t]*)?(?:业绩清单|类似项目业绩清单|业绩一览表)[ \t]*[:：]?[ \t]*$",),
        "perf_list",
    ),
)

LIST_END_RE = re.compile(
    r"\n\s*(?:#{1,6}\s*)?(?:第[一二三四五六七八九十]+[章节]|报价明细|商务|技术|其他资料|附件|"
    r"业绩清单|资质清单|资格清单)\b"
)
LIST_LINE_RE = re.compile(r"^\s*(?:\d+[.、]|[-*])\s*(.+)$")


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


def _extract_list(doc: Doc, spec: FieldSpec) -> SourceField | None:
    """从显式“资质清单/业绩清单”段落抽结构化条目。

    只认显式清单标题，避免把普通“资格证明文件”章节硬塞成清单；
    抽不到条目就返回 None（按缺失处理），不编造。
    """
    text = doc.full_text
    for pattern in spec.patterns:
        heading = re.search(pattern, text, re.M)
        if not heading:
            continue
        body_start = heading.end()
        end_match = LIST_END_RE.search(text, body_start)
        body_end = end_match.start() if end_match else min(len(text), body_start + 2000)
        items: list[dict[str, object]] = []
        first_line_end = body_start
        for line_match in re.finditer(r"[^\n]+", text[body_start:body_end]):
            raw = line_match.group(0)
            line_start = body_start + line_match.start()
            stripped = raw.strip()
            if not stripped or set(stripped) <= {"-", "|", " ", "\t"}:
                continue
            line = stripped
            bullet = LIST_LINE_RE.match(line)
            if bullet:
                line = bullet.group(1).strip()
            if "|" not in line and not bullet:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")] if "|" in line else [line]
            cells = [c for c in cells if c]
            if not cells:
                continue
            if spec.kind == "qual_list":
                name = cells[0]
                if name in {"资质名称", "材料名称", "序号"}:
                    continue
                item = {
                    "name": name,
                    "issuer": cells[1] if len(cells) > 1 else "",
                    "number": cells[2] if len(cells) > 2 else "",
                    "valid_until": cells[3] if len(cells) > 3 else "",
                }
            else:
                name = cells[0]
                if name in {"项目名称", "业绩名称", "序号"}:
                    continue
                item = {
                    "project_name": name,
                    "amount": cells[1] if len(cells) > 1 else "",
                    "owner": cells[2] if len(cells) > 2 else "",
                    "date": cells[3] if len(cells) > 3 else "",
                }
            if not name:
                continue
            lead = len(raw) - len(raw.lstrip())
            start = line_start + lead
            quote = doc.slice_text(start, start + len(stripped))
            if not quote:
                continue
            item.update({"page": doc.page_of(start), "char_start": start, "char_end": start + len(quote), "quote": quote})
            items.append(item)
            if first_line_end == body_start:
                first_line_end = start + len(quote)
        if not items:
            continue
        names = [str(i.get("name") or i.get("project_name") or "") for i in items]
        value = f"{len(items)} 项：" + "、".join(names)
        if len(value) > 100:
            value = value[:100] + "…"
        quote = doc.slice_text(heading.start(), first_line_end)
        return SourceField(
            name=spec.name,
            value=value,
            page=doc.page_of(heading.start()),
            char_start=heading.start(),
            char_end=first_line_end,
            quote=quote,
            items=items,
        )
    return None


def extract_fields(doc: Doc) -> list[SourceField]:
    """抽取关键字段；列表型字段只在显式“资质清单/业绩清单”标题下出现。"""
    fields: list[SourceField] = []
    for spec in FIELD_SPECS:
        field = _extract_list(doc, spec) if spec.kind.endswith("_list") else _extract_one(doc, spec)
        if field is not None:
            fields.append(field)
    return fields


def field_values(doc: Doc) -> dict[str, str]:
    """给评测与前端用的扁平视图。"""
    return {f.name: f.value for f in doc.fields}
