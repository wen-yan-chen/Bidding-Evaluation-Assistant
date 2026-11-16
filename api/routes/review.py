"""评审接口（D5）：细则列表、触发评审、取结果。

约定：
- 算分与核验全部来自确定性代码；接口只做编排与落盘；
- 结果里带 `profile.digest` 与 `rule_digest`，报告与页面都引用同一个指纹，保证"换细则"可追溯；
- 同一 `doc_id + profile_id` 重复调用结果一致（不含随机量），符合"重复 3 次一致"。
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api import store
from api.review import service as review_service
from api.scoring import list_profiles

router = APIRouter(prefix="/api", tags=["review"])


class ReviewRequest(BaseModel):
    doc_id: str = Field(..., description="已解析文档 ID")
    profile_id: str = Field("profile-a", description="评分细则 ID")
    project_type: Literal["engineering", "goods_services", "unknown"] = Field(
        "unknown", description="项目类型：engineering / goods_services / unknown"
    )


@router.get("/scoring/profiles", summary="可用评分细则（含指纹与权重摘要）")
def scoring_profiles() -> dict[str, Any]:
    profiles = [p.to_dict() for p in list_profiles()]
    return {"count": len(profiles), "items": profiles}


@router.post("/review", summary="触发一次评审（资格性核验 + 分项评分 + 风险扫描）")
def create_review(payload: ReviewRequest) -> dict[str, Any]:
    doc = store.load_doc(payload.doc_id)
    if doc is None:
        raise HTTPException(404, f"文档不存在：{payload.doc_id}")
    result = review_service.run(doc, payload.profile_id, project_type=payload.project_type)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/review", summary="最近评审列表")
def list_reviews() -> dict[str, Any]:
    items = review_service.list_reviews()
    return {"count": len(items), "items": items}


@router.get("/review/{review_id}", summary="取评审结果（含分项得分与风险溯源）")
def get_review(review_id: str) -> dict[str, Any]:
    review = review_service.load(review_id)
    if review is None:
        raise HTTPException(404, f"评审结果不存在：{review_id}")
    return review
