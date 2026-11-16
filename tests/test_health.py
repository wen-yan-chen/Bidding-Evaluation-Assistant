"""D1 接口单测：不依赖 Docker，直接打 FastAPI 应用。

跑法（项目根目录）：
  pip install -r requirements-dev.txt
  pytest -q
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api import config
from api.main import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parent.parent


def test_health_returns_200_and_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "bid-review-api"


def test_api_health_has_capability_switches():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    caps = resp.json()["capabilities"]
    assert set(caps) >= {"parse", "qualification", "scoring", "risk_scan", "report_export"}
    # D2–D7 已上线的能力为 true，没做的能力不能提前标 true
    assert caps["parse"] is True
    assert caps["clause_split"] is True
    assert caps["ocr"] is True
    assert caps["qualification"] is True
    assert caps["scoring"] is True
    assert caps["risk_scan"] is True
    assert caps["report_export"] is True


def test_version_comes_from_version_file():
    expected = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert client.get("/health").json()["version"] == expected
    assert client.get("/api/health").json()["version"] == expected


def test_info_exposes_milestones_and_agent_config():
    resp = client.get("/api/info")
    assert resp.status_code == 200
    body = resp.json()
    assert body["errors"] == []
    assert len(body["milestones"]["items"]) >= 7
    assert body["agent"]["configured"] is True
    assert body["agent"]["temperature"] == 0


def test_index_page_carries_disclaimer():
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert config.DISCLAIMER in html
    assert "招投标评审助手" in html


def test_static_assets_served():
    assert client.get("/style.css").status_code == 200
    assert client.get("/app.js").status_code == 200


def test_security_headers_present():
    resp = client.get("/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "SAMEORIGIN"
