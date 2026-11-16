"""D7 报告导出单测：docx / pdf 生成、数值一致、错误处理。"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfReader
import pytest

from api import store
from api.main import app
from api.report import service as report_service
from api.review import service as review_service

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"
client = TestClient(app)
CREATED: list[tuple[str, str]] = []


@pytest.fixture(autouse=True)
def _cleanup_created():
    CREATED.clear()
    yield
    for review_id, doc_id in CREATED:
        report_service.delete_reports(review_id)
        review_service.delete(review_id)
        store.delete_doc(doc_id)


def _make_review() -> dict:
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
    CREATED.append((review["review_id"], doc_id))
    return review


def _docx_text(path: Path) -> str:
    document = Document(str(path))
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


def test_generate_docx_and_pdf_with_consistent_numbers():
    review = _make_review()
    review_id = review["review_id"]
    total = str(review["summary"]["total_score"])

    docx_path, data = report_service.generate(review_id, "docx")
    assert docx_path.exists() and docx_path.stat().st_size > 5000
    assert docx_path.read_bytes()[:2] == b"PK"
    text = _docx_text(docx_path)
    assert total in text
    assert data["basis"]["profile_digest"] in text
    assert data["basis"]["rule_digest"] in text

    pdf_path, _ = report_service.generate(review_id, "pdf")
    assert pdf_path.exists() and pdf_path.stat().st_size > 2000
    assert pdf_path.read_bytes()[:4] == b"%PDF"
    pdf_text = "\n".join((p.extract_text() or "") for p in PdfReader(str(pdf_path)).pages)
    assert total in pdf_text.replace(" ", "")
    assert "免责" in pdf_text or "辅助评审结果" in pdf_text


def test_generate_is_idempotent():
    review = _make_review()
    first, _ = report_service.generate(review["review_id"], "docx")
    size = first.stat().st_size
    second, _ = report_service.generate(review["review_id"], "docx")
    assert first == second
    assert second.stat().st_size == size


def test_report_meta_endpoint():
    review = _make_review()
    resp = client.get(f"/api/report/{review['review_id']}/meta")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["numbers"]["total"] == review["summary"]["total_score"]
    assert payload["numbers"]["risk_count"] == review["summary"]["risk_total"]


def test_report_download_endpoint():
    review = _make_review()
    docx = client.get(f"/api/report/{review['review_id']}?format=docx")
    assert docx.status_code == 200
    assert docx.headers["content-type"].startswith("application/vnd.openxmlformats")
    pdf = client.get(f"/api/report/{review['review_id']}?format=pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"


def test_report_errors():
    assert client.get("/api/report/rv-not-exist?format=docx").status_code == 404
    review = _make_review()
    bad = client.get(f"/api/report/{review['review_id']}?format=xlsx")
    assert bad.status_code == 400
