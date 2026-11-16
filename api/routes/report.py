"""报告接口（D7）：评审 → docx / pdf，支持重复下载与元信息查询。

具体生成逻辑在 `api.report.service`，与 MCP 的 `export_report` 共用同一份实现。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from api.report import service as report_service

router = APIRouter(prefix="/api", tags=["report"])


class ReportRequest(BaseModel):
    review_id: str
    format: str = Field("docx", description="docx 或 pdf")


def _file_response(review_id: str, fmt: str, inline: bool = False) -> FileResponse:
    try:
        path, _data = report_service.generate(review_id, fmt)
    except report_service.ReportError as exc:
        message = str(exc)
        raise HTTPException(404 if "不存在" in message else 400, message) from exc
    return FileResponse(
        path,
        media_type=report_service.media_type(path),
        filename=path.name,
        content_disposition_type="inline" if inline else "attachment",
    )


@router.post("/report", summary="生成并下载报告（docx / pdf）")
def create_report(payload: ReportRequest) -> FileResponse:
    return _file_response(payload.review_id, payload.format)


@router.get("/report/{review_id}", summary="下载报告（不存在则即时生成）")
def download_report(review_id: str, format: str = "docx", inline: bool = False) -> FileResponse:
    return _file_response(review_id, format, inline=inline)


@router.get("/report/{review_id}/meta", summary="报告元信息（是否已生成 / 大小 / 数值摘要）")
def report_meta(review_id: str) -> dict[str, Any]:
    try:
        review = report_service.load_review(review_id)
        data = report_service.build_data(review)
    except report_service.ReportError as exc:
        raise HTTPException(404, str(exc)) from exc

    files: dict[str, Any] = {}
    for fmt in report_service.FORMATS:
        path = report_service.report_path(review_id, fmt)
        files[fmt] = {"exists": path.exists(), "size": path.stat().st_size if path.exists() else 0}

    return {
        "review_id": review_id,
        "files": files,
        "numbers": {
            "total": data["scoring"]["total"],
            "total_full": data["scoring"]["total_full"],
            "risk_count": data["risks"]["counts"]["合计"],
            "qualification": data["qualification"]["counts"],
            "profile_digest": data["basis"]["profile_digest"],
            "rule_digest": data["basis"]["rule_digest"],
        },
    }
