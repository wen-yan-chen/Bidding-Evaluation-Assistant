"""文档接口：上传解析、查询结果、取原文（D2 上线，D7 起复用 ingest 统一入库）。

设计要点：
- 解析失败不报 500，返回 `parse_status=failed` + 原因，前端可直接展示；
- 文档 ID 是 `YYYYMMDD-8位hex`，服务端做正则校验，挡路径穿越；
- 结果落盘，重启后仍可查询（演示与复算都依赖这一点）；
- 页面传的文件与聊天附件（MCP `parse_attachment`）走同一个 `api.ingest`，口径一致。
"""

from __future__ import annotations

import mimetypes
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from api import config, ingest, store
from api.parsers import ParseError, ext_of
from api.parsers.dispatch import SUPPORTED_EXTS

router = APIRouter(prefix="/api", tags=["docs"])
MAX_BYTES = config.settings.max_upload_mb * 1024 * 1024


@router.post("/upload", summary="上传招标/投标文件并解析")
async def upload(file: UploadFile = File(..., description="docx / pdf / txt / md")) -> dict[str, Any]:
    name = (file.filename or "unnamed").strip()
    ext = ext_of(name)
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(415, f"不支持的文件类型：{ext or '无扩展名'}（支持 {' / '.join(SUPPORTED_EXTS)}）")

    blob = await file.read()
    if not blob:
        raise HTTPException(400, "上传的文件是空的")
    if len(blob) > MAX_BYTES:
        raise HTTPException(413, f"文件超过 {config.settings.max_upload_mb} MB 限制")

    try:
        doc = ingest.ingest(blob, name, source="upload")
    except ParseError as exc:
        raise HTTPException(415, str(exc)) from exc
    return ingest.summary(doc)


@router.get("/documents", summary="已解析文档列表")
def list_documents(limit: int = 200) -> dict[str, Any]:
    items = store.list_docs(limit=limit)
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
