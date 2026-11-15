"""文档接口：上传解析、查询结果、取原文（D2 上线）。

设计要点：
- 解析失败不报 500，返回 `parse_status=failed` + 原因，前端可直接展示；
- 文档 ID 是 `YYYYMMDD-8位hex`，服务端做正则校验，挡路径穿越；
- 结果落盘，重启后仍可查询（演示与复算都依赖这一点）。
"""

from __future__ import annotations

import hashlib
import mimetypes
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from api import config, store
from api.extract import extract_fields
from api.parsers.dispatch import SUPPORTED_EXTS, parse_file

router = APIRouter(prefix="/api", tags=["docs"])
MAX_BYTES = config.settings.max_upload_mb * 1024 * 1024


def _new_doc_id() -> str:
    return f"{datetime.now(config.CST):%Y%m%d}-{uuid4().hex[:8]}"


def _summary(doc) -> dict[str, Any]:  # noqa: ANN001 - Doc，避免循环导入
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
    }


@router.post("/upload", summary="上传招标/投标文件并解析")
async def upload(file: UploadFile = File(..., description="docx / pdf / txt / md")) -> dict[str, Any]:
    name = (file.filename or "unnamed").strip()
    ext = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(415, f"不支持的文件类型：{ext or '无扩展名'}（支持 {' / '.join(SUPPORTED_EXTS)}）")

    blob = await file.read()
    if not blob:
        raise HTTPException(400, "上传的文件是空的")
    if len(blob) > MAX_BYTES:
        raise HTTPException(413, f"文件超过 {config.settings.max_upload_mb} MB 限制")

    doc_id = _new_doc_id()
    sha256 = hashlib.sha256(blob).hexdigest()
    store.save_upload(doc_id, ext, blob)

    doc = parse_file(blob, name, doc_id, sha256)
    doc.fields = extract_fields(doc)
    doc.meta.update(
        {
            "created_at": config.iso(config.now()),
            "size_bytes": len(blob),
            "content_type": file.content_type or mimetypes.guess_type(name)[0] or "application/octet-stream",
        }
    )
    store.save_doc(doc)

    return _summary(doc)


@router.get("/documents", summary="已解析文档列表")
def list_documents() -> dict[str, Any]:
    items = store.list_docs()
    return {"count": len(items), "items": items}


@router.get("/doc/{doc_id}", summary="取解析结果（含全文、页码表、条款、字段）")
def get_document(doc_id: str) -> dict[str, Any]:
    if not store.valid_doc_id(doc_id):
        raise HTTPException(400, "文档 ID 格式不合法")
    doc = store.load_doc(doc_id)
    if doc is None:
        raise HTTPException(404, "文档不存在或尚未解析")
    return doc.to_dict(with_text=True)


@router.get("/doc/{doc_id}/raw", summary="取上传的原始文件（双栏对照用）")
def get_raw(doc_id: str) -> FileResponse:
    if not store.valid_doc_id(doc_id):
        raise HTTPException(400, "文档 ID 格式不合法")
    path = store.raw_file(doc_id)
    if path is None:
        raise HTTPException(404, "原始文件不存在")
    media = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media, filename=path.name)
