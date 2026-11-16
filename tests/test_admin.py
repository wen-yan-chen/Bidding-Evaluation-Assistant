"""管理员登录与数据管理接口单测（演示级门禁）。"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data" / "samples" / "bid-001.docx"


def _client_with_admin(monkeypatch, password: str = "secret-pass") -> TestClient:
    monkeypatch.setenv("ADMIN_USER", "tester")
    monkeypatch.setenv("ADMIN_PASSWORD", password)
    return TestClient(app)


def test_admin_overview_requires_login(monkeypatch):
    client = _client_with_admin(monkeypatch)
    resp = client.get("/api/admin/overview")
    assert resp.status_code == 401


def test_admin_login_session_logout(monkeypatch):
    client = _client_with_admin(monkeypatch)
    assert client.post("/api/admin/login", json={"username": "tester", "password": "wrong"}).status_code == 401

    resp = client.post("/api/admin/login", json={"username": "tester", "password": "secret-pass"})
    assert resp.status_code == 200
    assert resp.json()["authenticated"] is True

    assert client.get("/api/admin/session").json()["authenticated"] is True
    overview = client.get("/api/admin/overview")
    assert overview.status_code == 200
    assert "docs" in overview.json()

    client.post("/api/admin/logout")
    assert client.get("/api/admin/session").json()["authenticated"] is False


def test_admin_login_reports_missing_password(monkeypatch):
    client = _client_with_admin(monkeypatch, password="")
    resp = client.post("/api/admin/login", json={"username": "tester", "password": "x"})
    assert resp.status_code == 503
    assert "ADMIN_PASSWORD" in resp.json()["detail"]


def test_admin_can_delete_uploaded_doc(monkeypatch):
    client = _client_with_admin(monkeypatch)
    assert client.post("/api/admin/login", json={"username": "tester", "password": "secret-pass"}).status_code == 200

    upload = client.post(
        "/api/upload",
        files={"file": ("admin-delete-test.docx", SAMPLE.read_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert upload.status_code == 200, upload.text
    doc_id = upload.json()["doc_id"]

    resp = client.delete(f"/api/admin/doc/{doc_id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["deleted_files"]
    assert client.get(f"/api/doc/{doc_id}").status_code == 404
