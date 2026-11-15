"""文件入库（解析 + 字段抽取 + 落盘）的统一入口。

两个调用方：
- `POST /api/upload`（前端上传）
- MCP 的 `parse_attachment`（Nexent 聊天里上传的附件，从 S3 取回后解析）

抽出来是为了保证"不管是页面传的还是聊天里传的，解析口径完全一致"。
"""

from __future__ import annotations

import hashlib
import mimetypes
from datetime import datetime
from typing import Any
from uuid import uuid4

from api import config, store
from api.extract import extract_fields
from api.parsers import ParseError, ext_of
from api.parsers.dispatch import SUPPORTED_EXTS, parse_file


def new_doc_id() -> str:
    return f"{datetime.now(config.CST):%Y%m%d}-{uuid4().hex[:8]}"


def ingest(blob: bytes, file_name: str, source: str = "upload") -> Any:
    """把一段文件字节变成已落盘的 Doc（含字段）。失败也返回 Doc（parse_status=failed）。"""
    ext = ext_of(file_name)
    if ext not in SUPPORTED_EXTS:
        raise ParseError(f"不支持的文件类型：{ext or '无扩展名'}（支持 {' / '.join(SUPPORTED_EXTS)}）")

    doc_id = new_doc_id()
    sha256 = hashlib.sha256(blob).hexdigest()
    store.save_upload(doc_id, ext, blob)

    doc = parse_file(blob, file_name, doc_id, sha256)
    doc.fields = extract_fields(doc)
    doc.meta.update(
        {
            "created_at": config.iso(config.now()),
            "size_bytes": len(blob),
            "content_type": mimetypes.guess_type(file_name)[0] or "application/octet-stream",
            "source": source,
        }
    )
    store.save_doc(doc)
    return doc


def summary(doc) -> dict[str, Any]:  # noqa: ANN001
    """上传接口与 MCP 工具共用的返回结构。"""
    return {
        "doc_id": doc.doc_id,
        "file_name": doc.file_name,
        "ext": doc.ext,
        "sha256": doc.sha256,
        "page_count": len(doc.pages),
        "char_count": len(doc.full_text),
        "page_source": doc.page_source,
        "parse_status": doc.parse_status,
        "degraded": doc.degraded,
        "text_pages": doc.meta.get("text_pages") or [],
        "ocr_pages": doc.meta.get("ocr_pages") or [],
        "empty_pages": doc.meta.get("empty_pages") or [],
        "clause_count": len(doc.clauses),
        "fields": [
            {
                "name": f.name,
                "value": f.value,
                "page": f.page,
                "char_start": f.char_start,
                "char_end": f.char_end,
                "quote": f.quote,
            }
            for f in doc.fields
        ],
        "missing_fields": [
            name
            for name in ("项目名称", "项目编号", "采购人", "投标人", "报价", "工期")
            if all(f.name != name for f in doc.fields)
        ],
        "created_at": doc.meta.get("created_at"),
        "source": doc.meta.get("source"),
    }
