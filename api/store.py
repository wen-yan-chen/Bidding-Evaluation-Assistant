"""解析结果落盘：原文进 `data/uploads/`，结构化结果进 `data/parsed/{doc_id}.json`。

落盘而不是只放内存，有三个原因：
1. 刷新页面 / 重启容器后还能看到上次的评审对象（演示时非常关键）；
2. 后续核验、评分、报告都从同一份 JSON 读数，保证"报告数值 = 页面数值"；
3. 评测脚本可以离线复算，不依赖服务进程。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from api import config
from api.docmodel import Doc

DOC_ID_RE = re.compile(r"^[0-9]{8}-[0-9a-f]{8}$")


def ensure_dirs() -> None:
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    config.PARSED_DIR.mkdir(parents=True, exist_ok=True)


def valid_doc_id(doc_id: str) -> bool:
    """挡掉 `../` 这类路径穿越：doc_id 只允许 `YYYYMMDD-8位hex`。"""
    return bool(DOC_ID_RE.match(doc_id or ""))


def upload_path(doc_id: str, ext: str) -> Path:
    return config.UPLOAD_DIR / f"{doc_id}{ext}"


def parsed_path(doc_id: str) -> Path:
    return config.PARSED_DIR / f"{doc_id}.json"


def save_upload(doc_id: str, ext: str, blob: bytes) -> Path:
    ensure_dirs()
    path = upload_path(doc_id, ext)
    path.write_bytes(blob)
    return path


def save_doc(doc: Doc) -> Path:
    ensure_dirs()
    path = parsed_path(doc.doc_id)
    path.write_text(
        json.dumps(doc.to_dict(with_text=True), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def load_doc(doc_id: str) -> Doc | None:
    if not valid_doc_id(doc_id):
        return None
    path = parsed_path(doc_id)
    if not path.exists():
        return None
    return Doc.from_dict(json.loads(path.read_text(encoding="utf-8")))


def raw_file(doc_id: str) -> Path | None:
    if not valid_doc_id(doc_id):
        return None
    for path in config.UPLOAD_DIR.glob(f"{doc_id}.*"):
        if path.is_file():
            return path
    return None


def list_docs(limit: int = 200) -> list[dict]:
    """按修改时间倒序列出已解析文档（只读文件头，不加载全文）。"""
    if not config.PARSED_DIR.exists():
        return []
    items: list[dict] = []
    for path in sorted(config.PARSED_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        items.append(
            {
                "doc_id": data.get("doc_id"),
                "file_name": data.get("file_name"),
                "ext": data.get("ext"),
                "page_count": data.get("page_count"),
                "parse_status": data.get("parse_status"),
                "degraded": data.get("degraded") or [],
                "field_count": len(data.get("fields") or []),
                "clause_count": len(data.get("clauses") or []),
                "created_at": (data.get("meta") or {}).get("created_at"),
            }
        )
    return items
