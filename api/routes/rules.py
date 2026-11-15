"""规则库接口（D4）：列表、详情、统计。

页面与报告都从这里取"规则库指纹"，保证"报告里写的规则版本 = 页面展示的规则版本"。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from api import rules as rules_api

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", summary="规则库统计 + 全部规则")
def list_rules(category: str | None = None, level: str | None = None) -> dict[str, Any]:
    items = [rule.to_dict() for rule in rules_api.load_rules()]
    if category:
        items = [i for i in items if i["category"] == category]
    if level:
        items = [i for i in items if i["level"] == level]
    return {
        "stats": rules_api.stats(),
        "count": len(items),
        "items": items,
    }


@router.get("/stats", summary="规则库统计（条数 / 分类 / 依据状态 / 指纹）")
def rule_stats() -> dict[str, Any]:
    return rules_api.stats()


@router.get("/{rule_id}", summary="单条规则（含依据三态解析结果）")
def get_rule(rule_id: str) -> dict[str, Any]:
    rule = rules_api.get_rule(rule_id.upper())
    if rule is None:
        raise HTTPException(404, f"规则不存在：{rule_id}")
    return rule.to_dict()
