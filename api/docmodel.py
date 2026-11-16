"""文档模型：解析层与下游（核验 / 评分 / 扫描 / 报告）之间唯一的契约。

D2 的核心不是"能读出字"，而是**读出来的每个字都能指回原文件的位置**。
所以这里只做三件事：

1. `full_text` 是唯一的文本容器，`pages` 记录每页在 `full_text` 中的区间；
2. 页码换算只有一条路径：`page_of(offset)`，用二分查，O(log n)；
3. 字段、条款、风险都存 `{page, char_start, char_end, quote}`，且强制
   `full_text[char_start:char_end] == quote`（见 `SourceField` 与 tools/validate_quotes.py）。

约定：页码从 1 开始；偏移是 Python 字符串下标（对中文按字符计，不是字节）。
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import asdict, dataclass, field
from typing import Any

PAGE_CHAR_BUDGET = 1100  # 无分页符时，一页按约 1100 字符估算（A4 / 小四 / 1.5 倍行距）


@dataclass(slots=True)
class PageSpan:
    """一页在 full_text 中的字符区间 [start, end)。"""

    page: int
    start: int
    end: int


@dataclass(slots=True)
class Clause:
    """条款切片。`label` 是编号（第X章/第X条/一、/1.1），`title` 是标题或首句。"""

    clause_id: str
    label: str
    title: str
    page: int
    char_start: int
    char_end: int
    text: str


@dataclass(slots=True)
class SourceField:
    """结构化字段 + 溯源三元组。`quote` 必须是 `full_text[char_start:char_end]`。

    `items` 只给“资质清单/业绩清单”这类结构化列表字段使用；普通字段为空列表。
    """

    name: str
    value: str
    page: int
    char_start: int
    char_end: int
    quote: str
    items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Doc:
    doc_id: str
    file_name: str
    ext: str
    sha256: str
    page_source: str  # native（pdf 文本层/分页符）| estimated（估算）| single（txt 单页）
    full_text: str = ""
    pages: list[PageSpan] = field(default_factory=list)
    clauses: list[Clause] = field(default_factory=list)
    fields: list[SourceField] = field(default_factory=list)
    parse_status: str = "ok"  # ok | degraded | failed
    degraded: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._starts = [p.start for p in self.pages]

    # ---------------------------------------------------------------- 页码映射

    def page_of(self, offset: int) -> int:
        """字符偏移 → 页码。越界时夹到首/末页，绝不抛异常（下游到处在调）。"""
        if not self.pages:
            return 1
        if offset <= 0:
            return 1
        idx = bisect_right(self._starts, offset) - 1
        return self.pages[max(0, min(idx, len(self.pages) - 1))].page

    def slice_text(self, start: int, end: int) -> str:
        """安全切片：越界自动夹取，避免下游因为一个坏偏移整个请求 500。"""
        start = max(0, min(start, len(self.full_text)))
        end = max(start, min(end, len(self.full_text)))
        return self.full_text[start:end]

    def add_degraded(self, note: str) -> None:
        """记录降级原因（去重、保序）。页面与报告都会展示这段说明。"""
        if note and note not in self.degraded:
            self.degraded.append(note)
        if self.parse_status == "ok":
            self.parse_status = "degraded"

    # ---------------------------------------------------------------- 序列化

    def to_dict(self, with_text: bool = True) -> dict[str, Any]:
        data = {
            "doc_id": self.doc_id,
            "file_name": self.file_name,
            "ext": self.ext,
            "sha256": self.sha256,
            "page_source": self.page_source,
            "parse_status": self.parse_status,
            "degraded": list(self.degraded),
            "page_count": len(self.pages),
            "char_count": len(self.full_text),
            "pages": [asdict(p) for p in self.pages],
            "clauses": [asdict(c) for c in self.clauses],
            "fields": [asdict(f) for f in self.fields],
            "meta": dict(self.meta),
        }
        if with_text:
            data["full_text"] = self.full_text
        else:
            data["preview"] = self.full_text[:200]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Doc:
        doc = cls(
            doc_id=data["doc_id"],
            file_name=data.get("file_name", ""),
            ext=data.get("ext", ""),
            sha256=data.get("sha256", ""),
            page_source=data.get("page_source", "single"),
            full_text=data.get("full_text", ""),
            pages=[PageSpan(**p) for p in data.get("pages") or []],
            clauses=[Clause(**c) for c in data.get("clauses") or []],
            fields=[SourceField(**f) for f in data.get("fields") or []],
            parse_status=data.get("parse_status", "ok"),
            degraded=list(data.get("degraded") or []),
            meta=dict(data.get("meta") or {}),
        )
        return doc


def build_pages(chunks: list[str], first_page: int = 1) -> tuple[str, list[PageSpan]]:
    """把逐页文本拼成 full_text，同时记录每页区间。空文档给一页空区间。"""
    text = ""
    spans: list[PageSpan] = []
    for i, chunk in enumerate(chunks):
        start = len(text)
        text += chunk
        spans.append(PageSpan(page=first_page + i, start=start, end=len(text)))
    if not spans:
        spans.append(PageSpan(page=first_page, start=0, end=0))
    return text, spans


def estimate_pages(text: str, budget: int = PAGE_CHAR_BUDGET) -> list[str]:
    """按字符预算切页，只用于没有分页符的 docx/纯文本。

    不追求精确：目的只是让"跳到第 N 页"有个合理落点，并在 degraded 里如实说明。
    """
    if not text:
        return [""]
    budget = max(200, budget)
    return [text[i : i + budget] for i in range(0, len(text), budget)]
