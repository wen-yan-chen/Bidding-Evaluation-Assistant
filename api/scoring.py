"""评分引擎（D5）：按 YAML 细则算分，全部确定性，不经过模型。

为什么算分不能交给模型：验收要求"与专家评分偏差 ±5 分内 ≥ 85%"和"同一输入 3 次一致"，
只有确定性规则能同时满足；模型只负责把 `reason` 写成人话（D7 报告阶段）。

支持三种评分项：
- `price_ratio`：报价 / 最高限价 的比值分档（超过 100% 直接 0 分并触发 R12）
- `duration`   ：工期天数与招标要求比较
- `presence`   ：关键章节/承诺是否提供（默认字面量命中；配置 `content_patterns` 时必须有实质内容，仅标题/套话不算）

每项结果都带 `evidence`（page / quote），与字段、风险使用同一套溯源口径。
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from api import config

SCORING_DIR = config.DATA_DIR / "scoring"
NO_BASIS = "未检索到权威依据"

PRICE_RE = re.compile(r"([0-9][0-9,，]*(?:\.[0-9]{1,2})?)\s*(万元|万|元)?")
DURATION_RE = re.compile(r"([0-9]{1,4})\s*(个?日历天|个?日历日|天|日|个月|月|周|年)")
TIME_NUMBER_RE = re.compile(
    r"[0-9]+\s*(?:个?工作日|日历天|天|日|周|个月|月|年|小时|分钟)"
    r"|[0-9]{4}\s*年\s*[0-9]{1,2}\s*月"
)
NEGATIVE_CONTENT = ("未提供", "未附", "未提交", "未明确", "未展开", "仅列标题", "没有", "不含", "缺少")


@dataclass
class ItemResult:
    item_id: str
    category: str
    name: str
    weight: float
    score: float
    full_score: float
    reason: str
    basis: str
    basis_status: str
    tier: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "item_id": self.item_id,
            "category": self.category,
            "name": self.name,
            "weight": self.weight,
            "score": round(self.score, 2),
            "full_score": self.full_score,
            "reason": self.reason,
            "basis": self.basis if self.basis_status == "verified" else (self.basis or NO_BASIS),
            "basis_status": self.basis_status,
            "tier": self.tier,
        }
        if self.evidence:
            data["evidence"] = self.evidence
        return data


@dataclass
class Profile:
    id: str
    name: str
    version: str
    total: float
    scoring_method: str
    requirements: dict[str, Any]
    items: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "total": self.total,
            "scoring_method": self.scoring_method,
            "requirements": self.requirements,
            "digest": profile_digest(self),
            "item_count": len(self.items),
        }


def _read(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"评分细则格式不对：{path}")
    return data


@lru_cache(maxsize=32)
def load_profile(profile_id: str) -> Profile | None:
    path = SCORING_DIR / f"{profile_id}.yaml"
    if not path.exists():
        return None
    raw = _read(path)
    return Profile(
        id=str(raw["id"]),
        name=str(raw["name"]),
        version=str(raw.get("version", "")),
        total=float(raw.get("total", 100)),
        scoring_method=str(raw.get("scoring_method", "综合评分法")),
        requirements=dict(raw.get("requirements") or {}),
        items=tuple(raw.get("items") or []),
    )


@lru_cache(maxsize=1)
def list_profiles() -> tuple[Profile, ...]:
    profiles: list[Profile] = []
    for path in sorted(SCORING_DIR.glob("*.yaml")):
        profile = load_profile(path.stem)
        if profile:
            profiles.append(profile)
    return tuple(profiles)


def profile_digest(profile: Profile) -> str:
    payload = json.dumps(
        {
            "id": profile.id,
            "version": profile.version,
            "total": profile.total,
            "requirements": profile.requirements,
            "items": profile.items,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- 数值解析


def parse_price(text: str) -> float | None:
    """把「人民币 1,286,000.00 元」「96.8 万元」统一成"元"。"""
    if not text:
        return None
    match = PRICE_RE.search(text.replace("，", ","))
    if not match:
        return None
    number = float(match.group(1).replace(",", ""))
    unit = match.group(2) or "元"
    if unit in ("万元", "万"):
        number *= 10000
    return number


def parse_days(text: str) -> int | None:
    """把「90 日历天」「12 个月」统一成"天"。"""
    if not text:
        return None
    match = DURATION_RE.search(text)
    if not match:
        return None
    number = int(match.group(1))
    unit = match.group(2)
    if unit in ("个月", "月"):
        return number * 30
    if unit == "年":
        return number * 365
    if unit == "周":
        return number * 7
    return number


# ---------------------------------------------------------------- 单项算分


def _find(pattern: str, doc) -> dict[str, Any] | None:  # noqa: ANN001
    text = doc.full_text
    start = text.find(pattern)
    if start < 0:
        return None
    end = start + len(pattern)
    return {
        "page": doc.page_of(start),
        "char_start": start,
        "char_end": end,
        "quote": doc.slice_text(start, end),
    }


def _sentence_text(doc, start: int, end: int) -> str:  # noqa: ANN001
    """取命中所在句/行，避免把相邻句的“未提供”误伤到本句。"""
    text = doc.full_text
    left = 0
    for char in "。；;\n":
        pos = text.rfind(char, 0, start)
        if pos >= left:
            left = pos + 1
    right = len(text)
    for char in "。；;\n":
        pos = text.find(char, end)
        if pos != -1 and pos < right:
            right = pos
    return text[left:right].strip()


def _score_price(item: dict[str, Any], doc, requirements: dict[str, Any]) -> ItemResult:
    weight = float(item["weight"])
    basis = str(item.get("basis") or "")
    basis_status = str(item.get("basis_status", "pending"))
    field = next((f for f in doc.fields if f.name == "报价"), None)
    price = parse_price(field.value) if field else None
    max_price = float(requirements.get("max_price") or 0)

    if price is None:
        return ItemResult(
            item["id"], item["category"], item["name"], weight, 0.0, weight,
            "未抽取到有效报价，无法计算价格分", basis, basis_status, tier="no_price",
        )

    evidence = {
        "page": field.page,
        "char_start": field.char_start,
        "char_end": field.char_end,
        "quote": field.quote,
        "price": price,
    }
    if max_price <= 0:
        return ItemResult(item["id"], item["category"], item["name"], weight, weight, weight,
                          "细则未配置最高限价，价格分按满分计（需补充 requirements.max_price）",
                          basis, basis_status, tier="no_cap", evidence=evidence)

    ratio = price / max_price
    for index, tier in enumerate(item.get("tiers") or []):
        limit = float(tier.get("max_ratio", 99))
        if ratio <= limit + 1e-9:
            score = min(float(tier.get("score", 0)), weight)
            return ItemResult(
                item["id"], item["category"], item["name"], weight, score, weight,
                str(tier.get("reason") or ""), basis, basis_status,
                tier=f"{index + 1}:ratio<={limit}", evidence={**evidence, "ratio": round(ratio, 4)},
            )
    return ItemResult(item["id"], item["category"], item["name"], weight, 0.0, weight,
                      "报价超出全部档位，按 0 分处理", basis, basis_status, tier="over", evidence=evidence)


def _score_duration(item: dict[str, Any], doc, _requirements: dict[str, Any]) -> ItemResult:
    weight = float(item["weight"])
    basis = str(item.get("basis") or "")
    basis_status = str(item.get("basis_status", "pending"))
    field = next((f for f in doc.fields if f.name == "工期"), None)
    days = parse_days(field.value) if field else None

    if days is None:
        return ItemResult(item["id"], item["category"], item["name"], weight, 0.0, weight,
                          "未抽取到工期，无法判定工期响应", basis, basis_status, tier="no_duration")

    evidence = {
        "page": field.page,
        "char_start": field.char_start,
        "char_end": field.char_end,
        "quote": field.quote,
        "days": days,
    }
    for index, tier in enumerate(item.get("tiers") or []):
        limit = int(tier.get("max_days", 9999))
        if days <= limit:
            score = min(float(tier.get("score", 0)), weight)
            return ItemResult(
                item["id"], item["category"], item["name"], weight, score, weight,
                str(tier.get("reason") or ""), basis, basis_status,
                tier=f"{index + 1}:days<={limit}", evidence=evidence,
            )
    return ItemResult(item["id"], item["category"], item["name"], weight, 0.0, weight,
                      "工期超出全部档位", basis, basis_status, tier="over", evidence=evidence)


def _score_presence(item: dict[str, Any], doc, _requirements: dict[str, Any]) -> ItemResult:
    weight = float(item["weight"])
    basis = str(item.get("basis") or "")
    basis_status = str(item.get("basis_status", "pending"))

    # 校准版判据：content_patterns 表示“必须有实质内容”；
    # 只出现章节标题/投标函套话不算响应。未配置时保持原来的 presence 行为。
    content_patterns = [str(p) for p in item.get("content_patterns") or []]
    content_number_patterns = {str(p) for p in item.get("content_number_patterns") or []}
    patterns = content_patterns or [str(p) for p in item.get("patterns") or []]

    for pattern in patterns:
        evidence = _find(pattern, doc)
        if evidence is None:
            continue
        # 收紧：进度安排/工期安排/节点/响应时限等泛词，必须邻近“数字+时间单位”，
        # 避免“我方将按工期安排组织施工”这种套话通过。
        sentence = _sentence_text(doc, evidence["char_start"], evidence["char_end"])
        if pattern in content_number_patterns and not TIME_NUMBER_RE.search(sentence):
            continue
        # 负向句里的“未提供项目管理机构/仅列标题”不能算已提供。
        if content_patterns and any(word in sentence for word in NEGATIVE_CONTENT):
            continue
        tiers = {str(t.get("state")): t for t in item.get("tiers") or []}
        tier = tiers.get("provided") or {}
        score = min(float(tier.get("score", weight)), weight)
        return ItemResult(
            item["id"], item["category"], item["name"], weight, score, weight,
            str(tier.get("reason") or ""), basis, basis_status, tier="provided",
            evidence={**evidence, "pattern": pattern, "content_pattern": bool(content_patterns)},
        )

    tiers = {str(t.get("state")): t for t in item.get("tiers") or []}
    tier = tiers.get("missing") or {}
    return ItemResult(
        item["id"], item["category"], item["name"], weight,
        min(float(tier.get("score", 0)), weight), weight,
        str(tier.get("reason") or ""), basis, basis_status, tier="missing",
    )


SCORERS = {
    "price_ratio": _score_price,
    "duration": _score_duration,
    "presence": _score_presence,
}


# ---------------------------------------------------------------- 对外入口


def score_doc(doc, profile_id: str) -> dict[str, Any]:  # noqa: ANN001
    """按细则给一份文档算分。细则不存在时返回 error，不抛异常。"""
    profile = load_profile(profile_id)
    if profile is None:
        return {"error": f"评分细则不存在：{profile_id}", "available": [p.id for p in list_profiles()]}

    results: list[ItemResult] = []
    for item in profile.items:
        scorer = SCORERS.get(str(item.get("type")))
        if scorer is None:
            results.append(
                ItemResult(
                    str(item.get("id")), str(item.get("category")), str(item.get("name")),
                    float(item.get("weight", 0)), 0.0, float(item.get("weight", 0)),
                    f"不支持的评分项类型：{item.get('type')}",
                    str(item.get("basis") or ""), str(item.get("basis_status", "pending")), tier="unsupported",
                )
            )
            continue
        results.append(scorer(item, doc, profile.requirements))

    items = [r.to_dict() for r in results]
    by_category: dict[str, dict[str, float]] = {}
    for result in results:
        bucket = by_category.setdefault(result.category, {"score": 0.0, "full": 0.0})
        bucket["score"] += result.score
        bucket["full"] += result.full_score

    total_score = round(sum(r.score for r in results), 2)
    total_full = round(sum(r.full_score for r in results), 2)
    return {
        "profile": profile.to_dict(),
        "requirements": profile.requirements,
        "items": items,
        "by_category": {
            k: {"score": round(v["score"], 2), "full": v["full"]} for k, v in by_category.items()
        },
        "total": total_score,
        "total_full": total_full,
        "score_ratio": round(total_score / total_full, 4) if total_full else 0.0,
        "deductions": [
            {"item_id": i["item_id"], "reason": i["reason"], "lost": round(i["full_score"] - i["score"], 2)}
            for i in items
            if i["score"] < i["full_score"]
        ],
    }
