"""管理员接口：登录 / 会话 / 数据概览 / 删除与清理。

安全边界（演示级）：
- 登录账号来自环境变量 ADMIN_USER / ADMIN_PASSWORD；
- 成功登录写 HttpOnly 签名 Cookie；删除类接口必须 `Depends(require_admin)`；
- 健康检查与 `/api/info` 保持公开（容器探针/版本核对），真正的删改只在 `/api/admin/*`。
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from api import admin, config, store
from api.report import service as report_service
from api.review import service as review_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


class CleanupRequest(BaseModel):
    mode: str = Field(..., description="duplicates / orphan_reviews")


def _cascade_delete_doc(doc_id: str) -> dict[str, Any]:
    reviews = review_service.list_for_doc(doc_id)
    deleted_reports: list[str] = []
    deleted_reviews: list[str] = []
    for review in reviews:
        review_id = review.get("review_id")
        if not review_id:
            continue
        deleted_reports.extend(report_service.delete_reports(review_id))
        if review_service.delete(review_id):
            deleted_reviews.append(review_id)
    removed = store.delete_doc(doc_id)
    return {
        "doc_id": doc_id,
        "deleted_reviews": len(deleted_reviews),
        "review_ids": deleted_reviews,
        "deleted_reports": len(deleted_reports),
        "deleted_files": removed["files"],
    }


def _mtime(doc_id: str) -> float:
    try:
        return store.parsed_path(doc_id).stat().st_mtime
    except OSError:
        return 0.0


@router.post("/login", summary="管理员登录（写 HttpOnly 会话 Cookie）")
def login(payload: LoginRequest, response: Response) -> dict[str, Any]:
    if not admin.check_credentials(payload.username, payload.password):
        raise HTTPException(401, "账号或密码错误")
    user = config.admin_user()
    admin.set_session_cookie(response, user)
    return {
        "authenticated": True,
        "user": user,
        "expires_in": config.admin_session_ttl(),
        "note": "管理员会话仅用于系统状态与数据管理",
    }


@router.get("/session", summary="当前管理员会话状态")
def session(user: str | None = Depends(admin.current_admin_optional)) -> dict[str, Any]:
    return {"authenticated": bool(user), "user": user}


@router.post("/logout", summary="退出管理员会话")
def logout(response: Response) -> dict[str, Any]:
    admin.clear_session_cookie(response)
    return {"authenticated": False}


@router.get("/overview", summary="数据管理概览（文档 / 评审 / 报告）")
def overview(_: str = Depends(admin.require_admin)) -> dict[str, Any]:
    docs = store.list_docs(limit=1000)
    reviews = review_service.list_reviews(limit=300)
    report_bytes = 0
    report_count = 0
    review_rows: list[dict[str, Any]] = []
    for review in reviews:
        files = report_service.report_sizes(str(review.get("review_id") or ""))
        for info in files.values():
            if info["exists"]:
                report_count += 1
                report_bytes += int(info["size"])
        review_rows.append({**review, "reports": files})

    uploads = len(list(config.UPLOAD_DIR.glob("*"))) if config.UPLOAD_DIR.exists() else 0
    return {
        "docs": docs,
        "reviews": review_rows,
        "counts": {
            "docs": len(docs),
            "reviews": len(review_rows),
            "reports": report_count,
            "report_bytes": report_bytes,
            "uploads": uploads,
        },
        "storage": {
            "upload_dir": str(config.UPLOAD_DIR),
            "parsed_dir": str(config.PARSED_DIR),
            "reviews_dir": str(review_service.REVIEWS_DIR),
            "reports_dir": str(report_service.REPORTS_DIR),
        },
    }


@router.delete("/doc/{doc_id}", summary="删除文档（级联删除其评审与报告）")
def delete_doc(doc_id: str, _: str = Depends(admin.require_admin)) -> dict[str, Any]:
    if not store.valid_doc_id(doc_id):
        raise HTTPException(400, "文档 ID 格式不合法")
    if store.load_doc(doc_id) is None:
        raise HTTPException(404, f"文档不存在：{doc_id}")
    return _cascade_delete_doc(doc_id)


@router.delete("/review/{review_id}", summary="删除评审及其报告")
def delete_review(review_id: str, _: str = Depends(admin.require_admin)) -> dict[str, Any]:
    review = review_service.load(review_id)
    if review is None:
        raise HTTPException(404, f"评审不存在：{review_id}")
    deleted_reports = report_service.delete_reports(review_id)
    deleted = review_service.delete(review_id)
    return {
        "review_id": review_id,
        "deleted": deleted,
        "deleted_reports": len(deleted_reports),
        "report_files": deleted_reports,
    }


@router.delete("/report/{review_id}", summary="只删除报告文件（保留评审）")
def delete_report(review_id: str, _: str = Depends(admin.require_admin)) -> dict[str, Any]:
    if review_service.load(review_id) is None:
        raise HTTPException(404, f"评审不存在：{review_id}")
    deleted = report_service.delete_reports(review_id)
    if not deleted:
        raise HTTPException(404, "该评审还没有生成报告文件")
    return {"review_id": review_id, "deleted_reports": len(deleted), "files": deleted}


@router.post("/cleanup", summary="批量清理：重复文档 / 无文档评审")
def cleanup(payload: CleanupRequest, _: str = Depends(admin.require_admin)) -> dict[str, Any]:
    mode = (payload.mode or "").strip()
    if mode == "duplicates":
        docs = store.list_docs(limit=1000)
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for doc in docs:
            key = str(doc.get("file_name") or doc.get("doc_id") or "")
            groups[key].append(doc)
        deleted_docs = 0
        deleted_reviews = 0
        deleted_reports = 0
        for group in groups.values():
            if len(group) <= 1:
                continue
            group.sort(
                key=lambda item: _mtime(str(item.get("doc_id"))),
                reverse=True,
            )
            for doc in group[1:]:
                result = _cascade_delete_doc(str(doc.get("doc_id")))
                deleted_docs += 1
                deleted_reviews += result["deleted_reviews"]
                deleted_reports += result["deleted_reports"]
        return {
            "mode": mode,
            "deleted_docs": deleted_docs,
            "deleted_reviews": deleted_reviews,
            "deleted_reports": deleted_reports,
            "kept_per_name": 1,
        }

    if mode == "orphan_reviews":
        reviews = review_service.list_reviews(limit=1000)
        deleted_reviews = 0
        deleted_reports = 0
        for review in reviews:
            doc_id = str(review.get("doc_id") or "")
            if store.load_doc(doc_id) is not None:
                continue
            deleted_reports += len(report_service.delete_reports(str(review.get("review_id"))))
            if review_service.delete(str(review.get("review_id"))):
                deleted_reviews += 1
        return {
            "mode": mode,
            "deleted_reviews": deleted_reviews,
            "deleted_reports": deleted_reports,
        }

    raise HTTPException(400, "mode 只支持 duplicates / orphan_reviews")
