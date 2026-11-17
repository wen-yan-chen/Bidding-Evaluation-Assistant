"""验收测评公共库（只读调用被测系统；本文件属于测评脚本，不属于被测代码）。

- 不 import 被测 api.* 模块，避免“用被测实现验证被测实现”；
- 只通过 HTTP 调用 18080，独立解析 YAML 与 JSON。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import time
import uuid
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[3]  # docs/评审功能测评数据/scripts -> 项目根
BASE = os.getenv("QA_BASE", "http://127.0.0.1:18080")
DATA = ROOT / "docs" / "评审功能测评数据"
RAW = DATA / "raw"
PERF = DATA / "perf"
SHOTS = ROOT / "docs" / "screenshots"
PREFIX = "QA20261116-"
SESSION = requests.Session()
SESSION.trust_env = False


def ensure_dirs() -> None:
    for path in (RAW, PERF, SHOTS):
        path.mkdir(parents=True, exist_ok=True)


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def jdump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def jload(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def upload(path: Path, name: str | None = None, timeout: float = 240.0) -> dict[str, Any]:
    name = name or (PREFIX + path.name)
    t0 = time.perf_counter()
    with path.open("rb") as fh:
        resp = SESSION.post(BASE + "/api/upload", files={"file": (name, fh)}, timeout=timeout)
    ms = (time.perf_counter() - t0) * 1000
    try:
        body = resp.json()
    except ValueError:
        body = {"_text": resp.text[:2000]}
    return {"status": resp.status_code, "ms": ms, "body": body, "file": path.name, "sent_name": name}


def upload_bytes(content: bytes, name: str, timeout: float = 240.0) -> dict[str, Any]:
    t0 = time.perf_counter()
    resp = SESSION.post(BASE + "/api/upload", files={"file": (name, content)}, timeout=timeout)
    ms = (time.perf_counter() - t0) * 1000
    try:
        body = resp.json()
    except ValueError:
        body = {"_text": resp.text[:2000]}
    return {"status": resp.status_code, "ms": ms, "body": body, "sent_name": name}


def review(doc_id: str, profile_id: str = "profile-a") -> dict[str, Any]:
    t0 = time.perf_counter()
    resp = SESSION.post(BASE + "/api/review", json={"doc_id": doc_id, "profile_id": profile_id}, timeout=120)
    ms = (time.perf_counter() - t0) * 1000
    return {"status": resp.status_code, "ms": ms, "body": _json(resp)}


def get(path: str, **kwargs) -> requests.Response:
    return SESSION.get(BASE + path, timeout=kwargs.pop("timeout", 120), **kwargs)


def get_json(path: str, **kwargs) -> Any:
    return _json(get(path, **kwargs))


def _json(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return {"_status": resp.status_code, "_text": resp.text[:2000]}


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def perf_summary(values: list[float]) -> dict[str, float]:
    return {
        "n": len(values),
        "min": round(min(values), 1) if values else 0.0,
        "p50": round(pct(values, 0.50), 1),
        "p95": round(pct(values, 0.95), 1),
        "max": round(max(values), 1) if values else 0.0,
        "mean": round(statistics.fmean(values), 1) if values else 0.0,
    }


# ---------------------------------------------------------------- 独立评分复算（只读 YAML）
PRICE_RE = re.compile(r"([0-9][0-9,，]*(?:\.[0-9]{1,2})?)\s*(万元|万|元)?")
DAYS_RE = re.compile(r"([0-9]{1,4})\s*(个?日历天|个?日历日|天|日|个月|月|周|年)")


def parse_price(text: str) -> float | None:
    if not text:
        return None
    m = PRICE_RE.search(text.replace("，", ","))
    if not m:
        return None
    num = float(m.group(1).replace(",", ""))
    return num * 10000 if (m.group(2) or "") in ("万", "万元") else num


def parse_days(text: str) -> int | None:
    if not text:
        return None
    m = DAYS_RE.search(text)
    if not m:
        return None
    num, unit = int(m.group(1)), m.group(2)
    if unit in ("个月", "月"):
        return num * 30
    if unit == "年":
        return num * 365
    if unit == "周":
        return num * 7
    return num


def load_yaml(profile_id: str) -> dict[str, Any]:
    import yaml

    return yaml.safe_load((ROOT / "data" / "scoring" / f"{profile_id}.yaml").read_text(encoding="utf-8"))


def recompute_scoring(doc: dict[str, Any], profile_id: str) -> dict[str, Any]:
    """按 YAML 独立复算 9 项；不调用 api.scoring。"""
    profile = load_yaml(profile_id)
    fields = {f["name"]: f for f in doc.get("fields") or []}
    text = doc.get("full_text") or ""
    req = profile.get("requirements") or {}
    items, deductions = [], []
    for item in profile["items"]:
        weight = float(item["weight"])
        score = 0.0
        tier = ""
        evidence = None
        if item["type"] == "price_ratio":
            price = parse_price(fields.get("报价", {}).get("value", ""))
            cap = float(req.get("max_price") or 0)
            if price is None:
                tier = "no_price"
            elif cap <= 0:
                score, tier = weight, "no_cap"
            else:
                ratio = price / cap
                for idx, t in enumerate(item.get("tiers") or []):
                    if ratio <= float(t.get("max_ratio", 99)) + 1e-9:
                        score, tier = min(float(t["score"]), weight), f"{idx+1}:ratio<={t['max_ratio']}"
                        break
                evidence = {"price": price, "cap": cap, "ratio": round(ratio, 6)}
        elif item["type"] == "duration":
            days = parse_days(fields.get("工期", {}).get("value", ""))
            if days is None:
                tier = "no_duration"
            else:
                for idx, t in enumerate(item.get("tiers") or []):
                    if days <= int(t.get("max_days", 9999)):
                        score, tier = min(float(t["score"]), weight), f"{idx+1}:days<={t['max_days']}"
                        break
                evidence = {"days": days}
        elif item["type"] == "presence":
            hit = next((p for p in item.get("patterns") or [] if p in text), None)
            if hit:
                tiers = {t.get("state"): t for t in item.get("tiers") or []}
                score = min(float((tiers.get("provided") or {}).get("score", weight)), weight)
                tier = "provided"
                evidence = {"pattern": hit}
            else:
                tiers = {t.get("state"): t for t in item.get("tiers") or []}
                score = min(float((tiers.get("missing") or {}).get("score", 0)), weight)
                tier = "missing"
        else:
            tier = "unsupported"
        items.append(
            {
                "item_id": item["id"],
                "category": item["category"],
                "name": item["name"],
                "weight": weight,
                "score": round(score, 2),
                "full_score": weight,
                "tier": tier,
                "evidence": evidence,
            }
        )
        if score < weight:
            deductions.append({"item_id": item["id"], "lost": round(weight - score, 2)})
    return {
        "profile_id": profile_id,
        "items": items,
        "total": round(sum(i["score"] for i in items), 2),
        "total_full": round(sum(i["full_score"] for i in items), 2),
        "deductions": deductions,
    }


def compare_scoring(api_review: dict[str, Any], recomputed: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    api_items = {i["item_id"]: i for i in (api_review.get("scoring") or {}).get("items") or []}
    for exp in recomputed["items"]:
        got = api_items.get(exp["item_id"])
        if got is None:
            problems.append(f"{exp['item_id']} 缺失")
            continue
        if abs(float(got.get("weight", -1)) - exp["weight"]) > 1e-9:
            problems.append(f"{exp['item_id']} 权重 {got.get('weight')} != {exp['weight']}")
        if abs(float(got.get("score", -1)) - exp["score"]) > 1e-9:
            problems.append(f"{exp['item_id']} 得分 {got.get('score')} != {exp['score']}")
        if abs(float(got.get("full_score", -1)) - exp["full_score"]) > 1e-9:
            problems.append(f"{exp['item_id']} 满分 {got.get('full_score')} != {exp['full_score']}")
    got_total = float((api_review.get("scoring") or {}).get("total", -1))
    if abs(got_total - recomputed["total"]) > 1e-9:
        problems.append(f"总分 {got_total} != {recomputed['total']}")
    return problems


# ---------------------------------------------------------------- 独立解析核对
def norm(text: str | None) -> str:
    if text is None:
        return ""
    text = str(text).strip()
    text = re.sub(r"（大写[:：].*?）?$", "", text)
    text = text.replace("人民币", "").replace("RMB", "")
    text = re.sub(r"[\s\u3000,，]", "", text)
    return text.lower()


def check_fields(doc: dict[str, Any], expect: dict[str, str]) -> dict[str, Any]:
    """逐字段核对：命中/缺失/多抽 + quote 切片 + 页码。"""
    text = doc.get("full_text") or ""
    pages = doc.get("pages") or []
    got = {f["name"]: f for f in doc.get("fields") or []}

    def page_of(offset: int) -> int | None:
        for span in pages:
            if span["start"] <= offset < span["end"]:
                return span["page"]
        return pages[-1]["page"] if pages and offset == len(text) else None

    rows = []
    for name, want in expect.items():
        field = got.get(name)
        row = {"name": name, "expected": want, "actual": None, "hit": False, "slice_ok": False, "page_ok": False,
               "quote_has_value": False, "note": ""}
        if field is None:
            row["note"] = "缺失"
        else:
            row["actual"] = field.get("value")
            row["hit"] = norm(field.get("value")) == norm(want)
            start, end = field.get("char_start"), field.get("char_end")
            sliced = text[start:end] if isinstance(start, int) and isinstance(end, int) else ""
            row["slice_ok"] = sliced == field.get("quote")
            row["page_ok"] = page_of(start) == field.get("page") if isinstance(start, int) else False
            row["quote_has_value"] = norm(want) in norm(field.get("quote"))
            if not row["hit"]:
                row["note"] = "值不一致"
            if not row["slice_ok"]:
                row["note"] += "；切片≠quote"
            if not row["page_ok"]:
                row["note"] += "；页码不符"
        rows.append(row)
    extras = [name for name in got if name not in expect]
    return {"rows": rows, "extras": extras, "hit": sum(r["hit"] for r in rows), "expect": len(expect)}


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hits = sum(1 for r in rows if r.get("hit"))
    return {"n": len(rows), "hit": hits, "rate": round(hits / len(rows), 4) if rows else 0.0}


# ---------------------------------------------------------------- 管理员清理
def admin_login() -> requests.Session:
    creds = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            creds[k.strip()] = v.strip()
    s = requests.Session()
    s.trust_env = False
    r = s.post(
        BASE + "/api/admin/login",
        json={"username": creds.get("ADMIN_USER", ""), "password": creds.get("ADMIN_PASSWORD", "")},
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"管理员登录失败：HTTP {r.status_code}")
    return s


def cleanup_qa_docs(s: requests.Session) -> dict[str, Any]:
    """删除本次测评创建的 QA20261116- 文档（级联评审/报告）；不碰其他数据。"""
    docs = s.get(BASE + "/api/documents?limit=1000", timeout=60).json().get("items") or []
    targets = [d for d in docs if str(d.get("file_name", "")).startswith(PREFIX)]
    deleted, failed = [], []
    for d in targets:
        r = s.delete(BASE + f"/api/admin/doc/{d['doc_id']}", timeout=60)
        (deleted if r.status_code == 200 else failed).append({"doc_id": d["doc_id"], "file_name": d["file_name"],
                                                             "status": r.status_code, "body": r.text[:200]})
    return {"targets": len(targets), "deleted": deleted, "failed": failed}
