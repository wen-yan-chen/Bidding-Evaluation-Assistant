"""解析器集合：文件字节 → `Doc`（只负责"读文本 + 建页码"，不碰字段抽取）。

分工：
- `docx_parser`  段落与表格按文档顺序取出；页码优先用分页符，没有就估算并标 degraded
- `pdf_parser`   逐页取文本层，页码天然精确；空页（扫描件）如实标记
- `txt_parser`   编码嗅探（utf-8 / gb18030 / utf-16），换页符拆分
- `clauses`      条款切分（章 / 条 / 一、 / 1.1 四类）
- `dispatch`     按扩展名分发 + 统一异常兜底（失败也返回 Doc，不抛给路由层）
"""

from __future__ import annotations

from pathlib import Path

SUPPORTED_EXTS = {".docx", ".pdf", ".txt", ".md"}


class ParseError(Exception):
    """不可恢复的解析失败（如加密 PDF、文件损坏）。"""


def ext_of(file_name: str) -> str:
    return Path(file_name).suffix.lower()
