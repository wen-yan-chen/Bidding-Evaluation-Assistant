"""条款切分：把全文切成可引用的条款片段，且保留精确偏移。

识别四类编号（按优先级）：
1. `第X章`  / `第X条`  → 招标文件、投标函、合同的主要骨架
2. `一、` `二、`        → 资格要求、评分办法常用
3. `1.1` / `2.3.1`      → 技术规格、评分细则
4. `（一）`              → 子项

切分是**纯位置计算**，不做语义判断：任何下游"引用第 X 条"都必须来自这里的 clause_id，
不允许模型自己数条号（数错是溯源事故的主要来源）。
"""

from __future__ import annotations

import re

from api.docmodel import Clause, Doc

CN_NUM = "一二三四五六七八九十百零〇两0-9"
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("chapter", re.compile(rf"^[ \t\u3000]*第[{CN_NUM}]{{1,6}}章[ \t\u3000]*(?P<title>[^\n]{{0,40}})", re.M)),
    ("article", re.compile(rf"^[ \t\u3000]*第[{CN_NUM}]{{1,6}}条[ \t\u3000]*(?P<title>[^\n]{{0,40}})", re.M)),
    ("section", re.compile(r"^[ \t\u3000]*[一二三四五六七八九十]{1,3}、[ \t\u3000]*(?P<title>[^\n]{0,40})", re.M)),
    ("numbered", re.compile(r"^[ \t\u3000]*(?P<title>\d{1,2}(?:\.\d{1,2}){0,3})[ \t\u3000、.．]{1,3}(?P<rest>[^\n]{0,40})", re.M)),
    ("paren", re.compile(r"^[ \t\u3000]*（[一二三四五六七八九十]{1,3}）[ \t\u3000]*(?P<title>[^\n]{0,40})", re.M)),
)


def _label_of(kind: str, raw: str) -> str:
    """从匹配行里截出编号本身（`第三条 投标人资格` → `第三条`）。"""
    raw = raw.strip()
    if kind in ("chapter", "article", "section", "paren"):
        for sep in (" ", "\t", "\u3000", "、"):
            raw = raw.split(sep, 1)[0]
        return raw.strip()
    return raw.split()[0].strip() if raw.split() else raw


def split_clauses(doc: Doc, min_len: int = 2) -> list[Clause]:
    text = doc.full_text
    marks: list[tuple[int, int, str, str, str]] = []  # (start, priority, kind, label, title)

    for priority, (kind, pattern) in enumerate(PATTERNS):
        for match in pattern.finditer(text):
            line = match.group(0).strip()
            title = (match.groupdict().get("title") or "").strip()
            if kind == "numbered":
                # `1.1 项目概况` 的 title 是编号本身，标题在 rest 里
                rest = (match.groupdict().get("rest") or "").strip()
                label = title
                title = rest
            else:
                label = _label_of(kind, line)
            marks.append((match.start(), priority, kind, label, title))

    marks.sort(key=lambda m: (m[0], m[1]))

    # 同一位置被多个规则命中时只留优先级最高的（章 > 条 > 一、 > 1.1 > （一））
    deduped: list[tuple[int, int, str, str, str]] = []
    for mark in marks:
        if deduped and mark[0] == deduped[-1][0]:
            continue
        deduped.append(mark)

    clauses: list[Clause] = []
    for index, (start, _priority, kind, label, title) in enumerate(deduped):
        end = deduped[index + 1][0] if index + 1 < len(deduped) else len(text)
        body = doc.slice_text(start, end)
        if len(body.strip()) < min_len:
            continue
        clauses.append(
            Clause(
                clause_id=f"C{len(clauses) + 1:03d}",
                label=label or f"C{len(clauses) + 1:03d}",
                title=(title or body.strip().split("\n", 1)[0])[:60],
                page=doc.page_of(start),
                char_start=start,
                char_end=end,
                text=body,
            )
        )

    return clauses
