"""评审编排（D5）：一次评审 = 资格性核验 + 分项评分 + 风险扫描，结果落盘。

顺序有讲究（对应手册 §5.3 的时序）：
1. 资格性核验（决定"能不能进详细评审"）；
2. 分项评分（按当前细则 YAML）；
3. 风险扫描（规则库 `detect=pattern` 的部分）；
4. 汇总（总分、扣分项、高风险条数），并把**细则指纹**写进结果——
   报告里必须能回答"这份分数是用哪套细则、哪个版本算出来的"。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from api import config, rules as rules_api, scoring

REVIEWS_DIR = config.DATA_DIR / "reviews"


def _review_id() -> str:
    return f"rv-{datetime.now(config.CST):%Y%m%d-%H%M%S}-{uuid4().hex[:6]}"


def run(doc, profile_id: str = "profile-a") -> dict[str, Any]:  # noqa: ANN001
    from api.review import qualification

    qualification_result = qualification.check(doc)
    scoring_result = scoring.score_doc(doc, profile_id)
    if "error" in scoring_result:
        return scoring_result

    risks = rules_api.scan_doc(doc)
    risks.sort(key=lambda h: ({"高": 0, "中": 1, "低": 2}.get(h["level"], 3), h["page"]))

    high = [r for r in risks if r["level"] == "高"]
    review = {
        "review_id": _review_id(),
        "doc_id": doc.doc_id,
        "file_name": doc.file_name,
        "created_at": config.iso(config.now()),
        "profile": scoring_result["profile"],
        "rule_digest": rules_api.rules_digest(),
        "qualification": qualification_result,
        "scoring": {
            "items": scoring_result["items"],
            "by_category": scoring_result["by_category"],
            "total": scoring_result["total"],
            "total_full": scoring_result["total_full"],
            "deductions": scoring_result["deductions"],
        },
        "risks": risks,
        "summary": {
            "total_score": scoring_result["total"],
            "total_full": scoring_result["total_full"],
            "qualification_missing": qualification_result["counts"]["missing"],
            "qualification_insufficient": qualification_result["counts"]["insufficient"],
            "risk_high": len(high),
            "risk_total": len(risks),
            "conclusion": _conclusion(qualification_result, scoring_result, high),
        },
        "disclaimer": config.DISCLAIMER,
    }
    save(review)
    return review


def _conclusion(qualification_result: dict[str, Any], scoring_result: dict[str, Any], high: list[dict]) -> str:
    parts: list[str] = []
    if qualification_result["counts"]["missing"]:
        parts.append(f"资格性材料缺失 {qualification_result['counts']['missing']} 项")
    if qualification_result["counts"]["insufficient"]:
        parts.append(f"资格性材料需复核 {qualification_result['counts']['insufficient']} 项")
    if high:
        parts.append(f"高风险条款 {len(high)} 条")
    parts.append(f"当前细则得分 {scoring_result['total']}/{scoring_result['total_full']}")
    return "；".join(parts) + "。以上为辅助评审建议，最终以评标委员会结论为准。"


def save(review: dict[str, Any]) -> None:
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    path = REVIEWS_DIR / f"{review['review_id']}.json"
    path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load(review_id: str) -> dict[str, Any] | None:
    if not review_id or not review_id.startswith("rv-") or "/" in review_id or "\\" in review_id:
        return None
    path = REVIEWS_DIR / f"{review_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_reviews(limit: int = 50) -> list[dict[str, Any]]:
    if not REVIEWS_DIR.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(REVIEWS_DIR.glob("rv-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        items.append(
            {
                "review_id": data.get("review_id"),
                "doc_id": data.get("doc_id"),
                "file_name": data.get("file_name"),
                "profile": (data.get("profile") or {}).get("id"),
                "total": (data.get("summary") or {}).get("total_score"),
                "created_at": data.get("created_at"),
            }
        )
    return items


def list_for_doc(doc_id: str) -> list[dict[str, Any]]:
    """返回引用某文档的全部评审（管理员级联删除用）。"""
    if not REVIEWS_DIR.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in REVIEWS_DIR.glob("rv-*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("doc_id") == doc_id:
            items.append(data)
    return items


def delete(review_id: str) -> bool:
    """删除评审 JSON；文件名只接受 rv- 开头的安全 ID。"""
    if not review_id or not review_id.startswith("rv-") or "/" in review_id or "\\" in review_id:
        return False
    path = REVIEWS_DIR / f"{review_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True
