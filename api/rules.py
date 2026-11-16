"""规则库加载与确定性扫描（D4）。

设计原则（手册 §5.1）：
- **规则数据只存在 YAML 里**，代码只负责加载与匹配；改一条依据不用改代码、不用发版；
- 判定是**字面量匹配**，不做语义推理：同一输入永远同一结果，"重复 3 次一致"才站得住；
- 每条命中都带 `clause_id / page / char_start / char_end / quote`，溯源口径与字段抽取完全一致；
- `basis_status=pending` 的规则，运行期一律输出「未检索到权威依据」，绝不编造条号。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from api import config

RULES_FILE = config.DATA_DIR / "rules" / "rules.yaml"
NO_BASIS = "未检索到权威依据"
NO_BASIS_NA = "经验判据，无法条依据"

DETECT_LABEL = {"pattern": "关键词命中", "manual": "人工核对", "price": "报价计算"}


@dataclass(frozen=True)
class Rule:
    id: str
    category: str
    level: str
    title: str
    condition: str
    detect: str
    patterns: tuple[str, ...] = ()
    basis_status: str = "pending"
    basis: str = ""
    basis_note: str = ""
    compliant: tuple[str, ...] = field(default_factory=tuple)
    project_types: tuple[str, ...] = ()
    legal_system: str = "both"
    requires_tender: bool = False

    @property
    def legal_basis(self) -> str:
        """依据三态的唯一出口：pending/na 不编造。"""
        if self.basis_status == "verified" and self.basis:
            return self.basis
        if self.basis_status == "na":
            return NO_BASIS_NA
        return NO_BASIS

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["patterns"] = list(self.patterns)
        data["compliant"] = list(self.compliant)
        data["project_types"] = list(self.project_types)
        data["legal_basis"] = self.legal_basis
        data["detect_label"] = DETECT_LABEL.get(self.detect, self.detect)
        return data


def _read_yaml(path: Path = RULES_FILE) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"规则库格式不对：{path}")
    return data


def _build(raw: dict[str, Any]) -> list[Rule]:
    rules: list[Rule] = []
    for item in raw.get("rules") or []:
        rules.append(
            Rule(
                id=str(item["id"]),
                category=str(item["category"]),
                level=str(item["level"]),
                title=str(item["title"]),
                condition=str(item["condition"]),
                detect=str(item.get("detect", "manual")),
                patterns=tuple(str(p) for p in item.get("patterns") or []),
                basis_status=str(item.get("basis_status", "pending")),
                basis=str(item.get("basis") or ""),
                basis_note=str(item.get("basis_note") or ""),
                compliant=tuple(str(c) for c in item.get("compliant") or []),
                project_types=tuple(str(t) for t in item.get("project_types") or []),
                legal_system=str(item.get("legal_system") or "both"),
                requires_tender=bool(item.get("requires_tender") or False),
            )
        )
    return rules


@lru_cache(maxsize=1)
def load_rules() -> tuple[Rule, ...]:
    return tuple(_build(_read_yaml()))


@lru_cache(maxsize=1)
def rules_digest() -> str:
    """规则库指纹：报告与知识库都引用同一个值，保证"规则库 ↔ 知识库"同源可核对。"""
    payload = json.dumps(
        [r.to_dict() for r in load_rules()],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def stats() -> dict[str, Any]:
    rules = load_rules()
    by_category: dict[str, int] = {}
    by_level: dict[str, int] = {}
    by_basis: dict[str, int] = {}
    by_detect: dict[str, int] = {}
    for rule in rules:
        by_category[rule.category] = by_category.get(rule.category, 0) + 1
        by_level[rule.level] = by_level.get(rule.level, 0) + 1
        by_basis[rule.basis_status] = by_basis.get(rule.basis_status, 0) + 1
        by_detect[rule.detect] = by_detect.get(rule.detect, 0) + 1
    return {
        "total": len(rules),
        "digest": rules_digest(),
        "baseline": NO_BASIS,
        "by_category": by_category,
        "by_level": by_level,
        "by_basis_status": by_basis,
        "by_detect": by_detect,
    }


def get_rule(rule_id: str) -> Rule | None:
    for rule in load_rules():
        if rule.id == rule_id:
            return rule
    return None


NEGATIVE_CONTEXT = ("无需", "不需要", "不要求", "免于", "不必", "没收", "不予退还", "扣除")


def _is_compliant(clause_text: str, rule: Rule) -> bool:
    """合规定式命中：条款写法已明确合规，不报本条。"""
    return any(phrase and phrase in clause_text for phrase in rule.compliant)


def _has_negative_context(text: str, start: int, end: int, window: int = 18) -> bool:
    """命中词附近出现"无需/不要求"等否定语，说明不是问题条款。"""
    context = text[max(0, start - window) : min(len(text), end + window)]
    return any(word in context for word in NEGATIVE_CONTEXT)


def rule_applies(rule: Rule, project_type: str | None) -> bool:
    """项目类型门控：未指定/unknown 时不硬判；工程类只匹配“工程”，货物服务匹配“货物/服务”。"""
    if not rule.project_types or not project_type or project_type == "unknown":
        return True
    if project_type == "engineering":
        return "工程" in rule.project_types
    if project_type == "goods_services":
        return bool({"货物", "服务"} & set(rule.project_types))
    return True


def scan_doc(
    doc: Any,
    rules: tuple[Rule, ...] | None = None,
    context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """确定性扫描：关键词规则（带合规/否定过滤）+ 计算型规则。

    `context` 用于计算型规则的外部参照，例如：
    `{"max_price": 2000000, "min_validity_days": 90, "below_cost_ratio": 0.6, "near_cap_ratio": 0.97}`
    没传时，最高限价优先从文档正文里读。
    """
    from api import checks

    rules = rules or load_rules()
    context = context or {}
    hits: list[dict[str, Any]] = []

    for rule in rules:
        # 资质门槛由 qualification.py 按三态核验，这里不重复扫描（否则"授权书"这类章节标题会被误报）
        if rule.category == "资质门槛":
            continue
        if not rule_applies(rule, context.get("project_type")):
            continue
        if rule.detect == "pattern" and rule.patterns:
            found = 0
            for clause in doc.clauses:
                text = clause.text
                if _is_compliant(text, rule):
                    continue
                for pattern in rule.patterns:
                    pos = text.find(pattern)
                    if pos < 0:
                        continue
                    start = clause.char_start + pos
                    end = start + len(pattern)
                    if _has_negative_context(doc.full_text, start, end):
                        continue
                    hits.append(
                        {
                            "rule_id": rule.id,
                            "category": rule.category,
                            "level": rule.level,
                            "title": rule.title,
                            "clause_id": clause.clause_id,
                            "page": doc.page_of(start),
                            "char_start": start,
                            "char_end": end,
                            "quote": doc.slice_text(start, end),
                            "legal_basis": rule.legal_basis,
                            "basis_status": rule.basis_status,
                            "matched_pattern": pattern,
                            "detect": "pattern",
                            "needs_review": True,
                        }
                    )
                    found += 1
                    break
                if found >= 3:
                    break
        elif rule.detect == "price" and rule.id in checks.CHECKS:
            for raw in checks.CHECKS[rule.id](doc, context):
                hits.append(
                    {
                        "rule_id": rule.id,
                        "category": rule.category,
                        "level": rule.level,
                        "title": rule.title,
                        "clause_id": None,
                        "page": raw["page"],
                        "char_start": raw["char_start"],
                        "char_end": raw["char_end"],
                        "quote": raw["quote"],
                        "legal_basis": rule.legal_basis,
                        "basis_status": rule.basis_status,
                        "matched_pattern": rule.id,
                        "detect": "check",
                        "reason": raw.get("reason", ""),
                        "values": raw.get("values", {}),
                        "needs_review": True,
                    }
                )
    # 同一规则在单份文档里只保留第一条证据：同一问题多处出现时，避免风险数被重复计高。
    # 需要展示多处证据时，由 UI/报告按 rule_id 聚合，而不是把同一规则计成多条风险。
    deduped: dict[str, dict[str, Any]] = {}
    for hit in hits:
        deduped.setdefault(str(hit["rule_id"]), hit)
    return list(deduped.values())


def scan_notes(doc: Any, rules: tuple[Rule, ...] | None = None) -> list[str]:
    """说明哪些规则本次不参与自动扫描（人工核对 / 未实现的计算型），供报告如实展示。"""
    from api import checks

    rules = rules or load_rules()
    notes: list[str] = []
    manual = [r.id for r in rules if r.detect == "manual"]
    unimplemented = [r.id for r in rules if r.detect == "price" and r.id not in checks.CHECKS]
    if manual:
        notes.append(f"需人工核对的规则（{len(manual)} 条）：{'、'.join(manual)}")
    if unimplemented:
        notes.append(f"暂未实现自动检测的报价类规则（{len(unimplemented)} 条）：{'、'.join(unimplemented)}")
    if not checks.CAP_RE.search(doc.full_text):
        notes.append("文档未载明最高投标限价，R12/R13/R31 未参与判定（避免拿别的项目限价硬比）")
    return notes
