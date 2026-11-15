"""报告生成服务：供 HTTP 接口与 MCP 工具共用（幂等、落盘）。

放在 service 层而不是路由里，是为了让 MCP 工具（`export_report`）与 HTTP 接口
（`POST /api/report`）走完全相同的生成逻辑——否则两份实现迟早不一致。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from api import config, store
from api.report import builder, docx_export, pdf_export
from api.review import service as review_service

REPORTS_DIR = config.DATA_DIR / "reports"
FORMATS = ("docx", "pdf")


class ReportError(Exception):
    """报告生成失败（评审不存在 / 文档丢失 / 格式不支持）。"""


def report_path(review_id: str, fmt: str) -> Path:
    return REPORTS_DIR / f"{review_id}.{fmt}"


def load_review(review_id: str) -> dict[str, Any]:
    review = review_service.load(review_id)
    if review is None:
        raise ReportError(f"评审结果不存在：{review_id}")
    return review


def build_data(review: dict[str, Any]) -> dict[str, Any]:
    doc = store.load_doc(review["doc_id"])
    if doc is None:
        raise ReportError(f"评审对应的文档已不存在：{review['doc_id']}")
    return builder.build(review, doc)


def generate(review_id: str, fmt: str = "docx") -> tuple[Path, dict[str, Any]]:
    """生成（或复用）报告，返回 (文件路径, 报告数据)。"""
    fmt = (fmt or "docx").lower()
    if fmt not in FORMATS:
        raise ReportError(f"不支持的格式：{fmt}（支持 {' / '.join(FORMATS)}）")

    review = load_review(review_id)
    data = build_data(review)

    out = report_path(review_id, fmt)
    if out.exists() and out.stat().st_size > 0:
        return out, data

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if fmt == "docx":
        docx_export.render(data, out)
    else:
        pdf_export.render(data, out)
    return out, data


def media_type(path: Path) -> str:
    if path.suffix == ".pdf":
        return "application/pdf"
    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def summary(review_id: str, fmt: str = "docx") -> dict[str, Any]:
    path, data = generate(review_id, fmt)
    return {
        "review_id": review_id,
        "format": path.suffix.lstrip("."),
        "path": str(path),
        "file_name": path.name,
        "size_bytes": path.stat().st_size,
        "download_url": f"/api/report/{review_id}?format={path.suffix.lstrip('.')}",
        "numbers": {
            "total": data["scoring"]["total"],
            "total_full": data["scoring"]["total_full"],
            "risk_count": data["risks"]["counts"]["合计"],
            "qualification_counts": data["qualification"]["counts"],
            "profile_digest": data["basis"]["profile_digest"],
            "rule_digest": data["basis"]["rule_digest"],
        },
    }
