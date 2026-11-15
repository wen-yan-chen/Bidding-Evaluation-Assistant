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


def scan_doc(doc: Any, rules: tuple[Rule, ...] | None = None) -> list[dict[str, Any]]:
    """确定性扫描：只跑 `detect=pattern` 的规则，按条款做字面量匹配。

    返回每条命中都带条款、页码与原文片段；同一规则在同一文档最多保留 3 处命中。
    """
    rules = rules or load_rules()
    hits: list[dict[str, Any]] = []
    for rule in rules:
        if rule.detect != "pattern" or not rule.patterns:
            continue
        found = 0
        for clause in doc.clauses:
            text = clause.text
            for pattern in rule.patterns:
                pos = text.find(pattern)
                if pos < 0:
                    continue
                start = clause.char_start + pos
                end = start + len(pattern)
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
                        "needs_review": True,
                    }
                )
                found += 1
                break
            if found >= 3:
                break
    return hits
