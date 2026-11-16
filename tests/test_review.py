"""D5 评审逻辑单测：评分细则、确定性算分、资格性三态、编排与接口。"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api import scoring, store
from api.extract import extract_fields
from api.main import app
from api.parsers.dispatch import parse_file
from api.review import qualification, service

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"
client = TestClient(app)


def parse_sample(name: str, doc_id: str = "eval"):
    path = SAMPLES / name
    doc = parse_file(path.read_bytes(), path.name, doc_id, "eval")
    doc.fields = extract_fields(doc)
    return doc


def test_profiles_loaded_and_digest_differs():
    profiles = scoring.list_profiles()
    assert [p.id for p in profiles] == ["profile-a", "profile-b"]
    assert all(p.total == 100 for p in profiles)
    assert scoring.profile_digest(profiles[0]) != scoring.profile_digest(profiles[1])
    assert scoring.load_profile("not-exist") is None


def test_price_and_duration_parsing():
    assert scoring.parse_price("人民币 1,286,000.00 元") == 1_286_000.0
    assert scoring.parse_price("96.8 万元") == 968_000.0
    assert scoring.parse_price("￥968,000.00") == 968_000.0
    assert scoring.parse_days("90 日历天") == 90
    assert scoring.parse_days("12 个月") == 360
    assert scoring.parse_days("无") is None


def test_price_ratio_tier():
    doc = parse_sample("bid-001.docx")
    result = scoring.score_doc(doc, "profile-a")
    price_item = next(i for i in result["items"] if i["item_id"] == "P1")
    # 1,286,000 / 2,000,000 = 0.643 → 第一档（≤0.90）满分 40
    assert price_item["score"] == 40
    assert price_item["tier"].startswith("1:")
    assert price_item["evidence"]["ratio"] <= 0.90


def test_over_cap_scores_zero():
    doc = parse_sample("bid-003.docx")  # 18,960,000 元，远超 200 万限价
    result = scoring.score_doc(doc, "profile-a")
    price_item = next(i for i in result["items"] if i["item_id"] == "P1")
    assert price_item["score"] == 0
    assert any(d["item_id"] == "P1" for d in result["deductions"])


def test_duration_tier_penalises_long_schedule():
    doc = parse_sample("bid-006.txt")  # 365 日历天，超过 90 天要求
    result = scoring.score_doc(doc, "profile-a")
    duration_item = next(i for i in result["items"] if i["item_id"] == "T5")
    assert duration_item["score"] == 0
    assert duration_item["evidence"]["days"] == 365


def test_qualification_three_states():
    doc = parse_sample("bid-001.docx")
    result = qualification.check(doc)
    states = {i["rule_id"]: i["state"] for i in result["items"]}
    assert states["R01"] == "provided"          # 营业执照
    assert states["R04"] == "provided"          # 授权委托书
    assert states["R09"] == "missing"           # 联合体协议（样本没有）
    assert result["counts"]["provided"] + result["counts"]["missing"] + result["counts"]["insufficient"] == 10


def test_review_is_deterministic_and_profile_switch_changes_score():
    doc = parse_sample("bid-001.docx", doc_id="20261115-abcdef02")
    first = service.run(doc, "profile-a")
    second = service.run(doc, "profile-a")
    assert first["summary"]["total_score"] == second["summary"]["total_score"]
    assert [r["rule_id"] for r in first["risks"]] == [r["rule_id"] for r in second["risks"]]
    assert first["rule_digest"] == second["rule_digest"]

    third = service.run(doc, "profile-b")
    items_a = {i["item_id"]: i["score"] for i in first["scoring"]["items"]}
    items_b = {i["item_id"]: i["score"] for i in third["scoring"]["items"]}
    assert items_a != items_b, "换细则后分项得分必须变化"
    assert first["profile"]["digest"] != third["profile"]["digest"]

    # 清理测试写入的评审文件，避免 pytest 污染 check_report 的最近 50 份
    for item in (first, second, third):
        service.delete(item["review_id"])


def test_review_api_roundtrip():
    blob = (SAMPLES / "bid-001.docx").read_bytes()
    upload = client.post(
        "/api/upload",
        files={"file": ("bid-001.docx", blob, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert upload.status_code == 200
    doc_id = upload.json()["doc_id"]

    created = client.post("/api/review", json={"doc_id": doc_id, "profile_id": "profile-a"})
    assert created.status_code == 200
    review = created.json()
    assert review["summary"]["total_score"] > 0
    assert review["qualification"]["total"] == 10
    assert review["disclaimer"].startswith("AI 辅助评审结果")

    fetched = client.get(f"/api/review/{review['review_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["summary"]["total_score"] == review["summary"]["total_score"]

    listed = client.get("/api/review")
    assert listed.status_code == 200
    assert listed.json()["count"] >= 1

    profiles = client.get("/api/scoring/profiles")
    assert profiles.status_code == 200
    assert profiles.json()["count"] == 2

    missing = client.get("/api/review/rv-not-exist")
    assert missing.status_code == 404

    # 清理本次上传与评审，避免污染运行时数据
    service.delete(review["review_id"])
    store.delete_doc(doc_id)
