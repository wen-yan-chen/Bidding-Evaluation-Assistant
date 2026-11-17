"""补拍报告中心/数据管理截图，并验证 iframe 源与下载可用性。"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as q
from playwright.sync_api import sync_playwright


def creds() -> tuple[str, str]:
    data = {}
    for line in (q.ROOT / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data.get("ADMIN_USER", ""), data.get("ADMIN_PASSWORD", "")


def main() -> int:
    q.ensure_dirs()
    out: dict = {"started_at": q.now(), "checks": {}, "shots": [], "console": [], "page_errors": []}
    prev = q.jload(q.RAW / "ui-raw.json")

    # 先验证 iframe 源（HTTP 层，不依赖浏览器 PDF 插件）
    for name, src in (("report_pdf", prev["checks"]["report_preview"]["iframe"]),
                      ("original_pdf", prev["checks"]["report_compare"]["original_iframe"]),
                      ("docx_html", prev["checks"]["docx_source"]["src"])):
        r = q.get(src) if src.startswith("/") else None
        out["checks"][name] = {"src": src, "status": r.status_code if r else None,
                               "content_type": r.headers.get("content-type") if r else None,
                               "magic": r.content[:8].decode("latin1") if r and r.content else "",
                               "size": len(r.content) if r else 0,
                               "has_disclaimer": ("AI 辅助评审结果" in r.text) if r and "html" in (r.headers.get("content-type") or "") else None}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 960}, locale="zh-CN", accept_downloads=True)
        page = ctx.new_page()
        page.set_default_timeout(45000)
        page.on("console", lambda msg: out["console"].append({"type": msg.type, "text": msg.text[:300]}))
        page.on("pageerror", lambda exc: out["page_errors"].append(str(exc)[:500]))
        page.goto(q.BASE + "/#reports", wait_until="domcontentloaded")
        page.wait_for_function("document.querySelectorAll('#reports-body tr').length >= 5")
        page.wait_for_function("!document.querySelector('#reports-body .meta-total').textContent.includes('读取中')", timeout=60000)
        page.wait_for_function("!document.querySelector('#reports-hint').textContent.includes('正在读取')", timeout=60000)
        out["checks"]["reports"] = {
            "rows": page.locator("#reports-body tr").count(),
            "hint": page.locator("#reports-hint").inner_text().strip(),
            "first_total": page.locator("#reports-body .meta-total").first.inner_text().strip(),
            "first_numbers": page.locator("#reports-body .meta-numbers").first.inner_text().strip(),
        }
        page.screenshot(path=str(q.SHOTS / "20261116-08-报告中心.png"))
        out["shots"].append("docs/screenshots/20261116-08-报告中心.png")

        # 下载 docx / pdf（浏览器路径）
        row = page.locator("#reports-body tr").first
        for fmt in ("docx", "pdf"):
            with page.expect_download(timeout=60000) as dl:
                row.locator("button", has_text=f"下载 {fmt}").click()
            d = dl.value
            path = q.PERF / f"ui-download-{d.suggested_filename}"
            d.save_as(str(path))
            out["checks"][f"download_{fmt}"] = {"filename": d.suggested_filename, "size": path.stat().st_size,
                                                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            path.unlink(missing_ok=True)

        # 管理员登录 -> 数据管理
        page.click("button[data-view='status']")
        user, password = creds()
        page.fill("#admin-user", user)
        page.fill("#admin-pass", password)
        page.click("#btn-admin-login")
        page.wait_for_selector("#status-content:not([hidden])")
        page.click("button[data-view='reports']")
        page.wait_for_selector("#admin-data-card:not([hidden])")
        page.wait_for_function("document.querySelectorAll('#admin-doc-body tr').length > 20", timeout=60000)
        out["checks"]["admin_data"] = {
            "doc_rows": page.locator("#admin-doc-body tr").count(),
            "review_rows": page.locator("#admin-review-body tr").count(),
            "summary": page.locator("#admin-summary").inner_text().strip(),
            "doc_count": page.locator("#admin-doc-count").inner_text().strip(),
            "review_count": page.locator("#admin-review-count").inner_text().strip(),
        }
        page.screenshot(path=str(q.SHOTS / "20261116-15-数据管理.png"))
        out["shots"].append("docs/screenshots/20261116-15-数据管理.png")

        # eval 行（非法 doc_id 但存在于解析目录）预览：应友好提示，不应把 404 JSON 塞进 iframe
        eval_row = page.locator("#admin-doc-body tr", has_text="eval")
        out["checks"]["eval_rows"] = eval_row.count()
        if eval_row.count():
            eval_row.first.locator("button", has_text="预览").click()
            page.wait_for_selector("#doc-preview:not([hidden])")
            page.wait_for_timeout(500)
            text = page.locator("#doc-preview-body").inner_text().strip()
            out["checks"]["eval_preview"] = {"text": text[:400], "has_404": "404" in text,
                                             "has_json": '"detail"' in text}
            page.screenshot(path=str(q.SHOTS / "20261116-14-数据管理-无原件文档提示.png"))
            out["shots"].append("docs/screenshots/20261116-14-数据管理-无原件文档提示.png")
            page.click("#btn-preview-close")

        # 无效 doc_id 记录直接走 API 的表现（记录缺陷）
        r = q.get("/api/doc/eval")
        out["checks"]["eval_api"] = {"status": r.status_code, "body": r.text[:200]}
        out["checks"]["console_error_count"] = sum(1 for c in out["console"] if c["type"] == "error")
        browser.close()

    q.jdump(q.RAW / "ui-reports-raw.json", out)
    print(json.dumps(out, ensure_ascii=False, indent=2)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
