"""Playwright UI 走查：首屏、评审渲染、双栏定位、源文件、报告中心、预览+原件、无原件提示、管理员状态。

输出：docs/评审功能测评数据/raw/ui-raw.json + docs/screenshots/20261116-*.png
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as q
from playwright.sync_api import sync_playwright

SHOTS = q.SHOTS
ACC = q.jload(q.RAW / "accuracy-raw.json")
PERF = q.jload(q.PERF / "perf-raw.json")
FIX = q.jload(q.RAW / "ui-fixtures.json")


def creds() -> tuple[str, str]:
    data = {}
    for line in (q.ROOT / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data.get("ADMIN_USER", ""), data.get("ADMIN_PASSWORD", "")


def main() -> int:
    q.ensure_dirs()
    risk_rec = next(r for r in ACC["risk"] if r["file"].endswith("risk-001.docx"))
    risk_doc = risk_rec["doc_id"]
    pdf_rec = next(r for r in ACC["samples"] if r["file"] == "bid-004.pdf")
    pdf_doc = pdf_rec["doc"]["doc_id"]
    report_review = None
    out: dict = {"started_at": q.now(), "shots": [], "timings": {}, "checks": {}, "console": [],
                 "page_errors": [], "request_failed": []}

    def shot(page, name: str, full: bool = False) -> None:
        path = SHOTS / f"20261116-{name}.png"
        page.screenshot(path=str(path), full_page=full)
        out["shots"].append(str(path.relative_to(q.ROOT)))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 960}, locale="zh-CN")
        page = ctx.new_page()
        page.set_default_timeout(45000)
        page.on("console", lambda msg: out["console"].append({"type": msg.type, "text": msg.text[:500]}))
        page.on("pageerror", lambda exc: out["page_errors"].append(str(exc)[:800]))
        page.on("requestfailed", lambda req: out["request_failed"].append({"url": req.url, "error": req.failure}))

        # 1. 首屏
        t0 = time.perf_counter()
        page.goto(q.BASE + "/#review", wait_until="domcontentloaded")
        out["timings"]["goto_domcontentloaded_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        page.wait_for_function("document.querySelectorAll('#doc-select option').length > 1", timeout=45000)
        page.wait_for_selector("#profile-list .profile-card", timeout=45000)
        out["timings"]["app_ready_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        perf = page.evaluate("""() => {
            const n = performance.getEntriesByType('navigation')[0] || {};
            const paints = Object.fromEntries(performance.getEntriesByType('paint').map(p => [p.name, p.startTime]));
            return {domContentLoaded: n.domContentLoadedEventEnd, load: n.loadEventEnd,
                    responseStart: n.responseStart, firstPaint: paints['first-paint'],
                    firstContentfulPaint: paints['first-contentful-paint']};
        }""")
        out["timings"]["navigation"] = perf
        out["checks"]["disclaimer"] = page.locator("#disclaimer-text").inner_text().strip()
        out["checks"]["doc_options"] = page.locator("#doc-select option").count()
        out["checks"]["profile_cards"] = page.locator("#profile-list .profile-card").count()
        shot(page, "01-评审看板")

        # 2. 评审 risk-001 并计时
        page.select_option("#doc-select", value=risk_doc)
        page.wait_for_function("(id) => document.querySelector('#sel-doc').textContent.includes(id)", arg=risk_doc)
        page.wait_for_selector("#pages .page", state="attached")
        t0 = time.perf_counter()
        page.click("#btn-review")
        page.wait_for_selector("#review-result:not([hidden])")
        page.wait_for_function("document.getElementById('score-total').textContent.trim() !== '—'")
        out["timings"]["review_click_to_render_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        out["checks"]["risk_review"] = {
            "score": page.locator("#score-total").inner_text().strip(),
            "full": page.locator("#score-full").inner_text().strip(),
            "qual_rows": page.locator("#qual-body tr").count(),
            "score_rows": page.locator("#score-body tr").count(),
            "risk_rows": page.locator("#risk-body tr").count(),
            "review_id": page.locator("#score-review-id").inner_text().strip(),
            "metric_qual": page.locator("#metric-qual").inner_text().strip(),
            "metric_risk": page.locator("#metric-risk").inner_text().strip(),
        }
        shot(page, "02-评审结果-风险", full=True)

        # 3. 双栏定位
        first = page.locator("#evidence-list .ev-item").first
        if first.count():
            first.click()
            page.wait_for_timeout(400)
            out["checks"]["locate"] = {
                "marks": page.locator("#pages mark.hit").count(),
                "active": page.locator("#dual-active").inner_text().strip(),
            }
            shot(page, "03-双栏定位")

        # 4. 源文件（docx HTML）
        page.click(".dual-tab[data-source-tab='file']")
        page.wait_for_selector("#source-preview-body iframe")
        out["checks"]["docx_source"] = {
            "src": page.locator("#source-preview-body iframe").get_attribute("src"),
            "visible": page.locator("#source-preview").is_visible(),
        }
        shot(page, "04-源文件-docx-WordHTML")

        # 5. PDF 源文件
        page.select_option("#doc-select", value=pdf_doc)
        page.wait_for_function("(id) => document.querySelector('#sel-doc').textContent.includes(id)", arg=pdf_doc)
        page.wait_for_selector("#pages .page", state="attached")
        page.click("#btn-review")
        page.wait_for_selector("#review-result:not([hidden])")
        page.wait_for_function("document.getElementById('score-total').textContent.trim() !== '—'")
        pdf_review = page.locator("#score-review-id").inner_text().strip()
        report_review = pdf_review
        page.click(".dual-tab[data-source-tab='file']")
        page.wait_for_selector("#source-preview-body iframe")
        out["checks"]["pdf_source"] = {
            "src": page.locator("#source-preview-body iframe").get_attribute("src"),
            "visible": page.locator("#source-preview").is_visible(),
        }
        shot(page, "05-源文件-PDF")

        # 6. 多选上传
        page.set_input_files("#file-input", [str(q.ROOT / "data" / "samples" / "bid-001.docx"),
                                             str(q.ROOT / "data" / "samples" / "bid-006.txt")])
        page.wait_for_function("document.getElementById('btn-upload').textContent.includes('(2)')")
        out["checks"]["multi_select"] = {
            "filename": page.locator("#file-name").inner_text().strip(),
            "button": page.locator("#btn-upload").inner_text().strip(),
        }
        shot(page, "06-多选已选")
        t0 = time.perf_counter()
        page.click("#btn-upload")
        page.wait_for_function("document.getElementById('upload-status').textContent.includes('批量解析完成')", timeout=120000)
        out["timings"]["multi_upload_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        out["checks"]["multi_upload_status"] = page.locator("#upload-status").inner_text().strip()
        shot(page, "07-多选上传完成")

        # 7. 拖拽选择
        page.evaluate("""() => {
            const dt = new DataTransfer();
            const file = new File(['项目名称：拖拽测试项目\\n项目编号：QA-DRAG-001\\n采购人：拖拽采购人\\n投标人：拖拽投标人\\n投标报价：人民币 1,286,000.00 元\\n工期：90 日历天\\n'], 'QA20261116-drag.txt', {type: 'text/plain'});
            dt.items.add(file);
            const box = document.getElementById('upload-box');
            box.dispatchEvent(new DragEvent('dragover', {bubbles: true, cancelable: true, dataTransfer: dt}));
            box.dispatchEvent(new DragEvent('drop', {bubbles: true, cancelable: true, dataTransfer: dt}));
        }""")
        page.wait_for_function("document.getElementById('btn-upload').textContent.includes('(1)')")
        out["checks"]["drag_select"] = page.locator("#file-name").inner_text().strip()
        page.click("#btn-upload")
        page.wait_for_function("document.getElementById('upload-status').textContent.includes('批量解析完成')", timeout=60000)
        out["checks"]["drag_upload_status"] = page.locator("#upload-status").inner_text().strip()

        # 8. 报告中心
        t0 = time.perf_counter()
        page.click("button[data-view='reports']")
        page.wait_for_selector("#reports-body tr")
        page.wait_for_function("document.querySelectorAll('#reports-body tr').length > 2")
        out["timings"]["reports_list_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        out["checks"]["reports_rows"] = page.locator("#reports-body tr").count()
        out["checks"]["reports_hint"] = page.locator("#reports-hint").inner_text().strip()
        shot(page, "08-报告中心")

        # 9. 报告预览 + 查看原件并排
        row = page.locator(f"tr[data-review-id='{report_review}']")
        if row.count() == 0:
            # 如果不在前 20，取第一行
            row = page.locator("#reports-body tr").first
        row.locator("button.locator", has_text="预览").click()
        page.wait_for_selector("#doc-preview:not([hidden])")
        page.wait_for_selector("#preview-report-pane iframe")
        page.wait_for_timeout(800)
        summary = page.locator("#doc-preview .preview-summary").inner_text().strip()
        out["checks"]["report_preview"] = {"summary": summary[:500],
                                           "iframe": page.locator("#preview-report-pane iframe").get_attribute("src")}
        shot(page, "09-报告预览")
        page.click("#btn-preview-original")
        page.wait_for_selector(".preview-panel.is-compare")
        page.wait_for_timeout(1200)
        page.wait_for_selector("#preview-original-pane iframe")
        out["checks"]["report_compare"] = {
            "btn": page.locator("#btn-preview-original").inner_text().strip(),
            "original_iframe": page.locator("#preview-original-pane iframe").get_attribute("src"),
            "compare_class": page.locator(".preview-panel").get_attribute("class"),
        }
        shot(page, "10-报告预览-原件并排")
        page.click("#btn-preview-close")

        # 10. 无原件报告预览（临时夹具）
        noraw = FIX["noraw_review_id"]
        row = page.locator(f"tr[data-review-id='{noraw}']")
        if row.count():
            row.locator("button.locator", has_text="预览").click()
            page.wait_for_selector("#doc-preview:not([hidden])")
            page.click("#btn-preview-original")
            page.wait_for_selector("#preview-original-pane")
            page.wait_for_timeout(500)
            body_text = page.locator("#preview-original-pane").inner_text().strip()
            out["checks"]["no_raw_report"] = {"text": body_text[:300],
                                              "has_404": "404" in body_text,
                                              "has_json": '"detail"' in body_text}
            shot(page, "11-无原件报告-友好提示")
            page.click("#btn-preview-close")

        # 11. 管理员状态
        page.click("button[data-view='status']")
        page.wait_for_selector("#status-lock")
        shot(page, "12-系统状态-未登录")
        user, password = creds()
        page.fill("#admin-user", user)
        page.fill("#admin-pass", password)
        page.click("#btn-admin-login")
        page.wait_for_selector("#status-content:not([hidden])", timeout=30000)
        page.wait_for_function("document.querySelectorAll('#check-list .check-row').length >= 6")
        out["checks"]["admin"] = {
            "selfcheck_rows": page.locator("#check-list .check-row").count(),
            "mcp": page.locator("#k-mcp-tools").inner_text().strip(),
            "mcp_label": page.locator("#mcp-value-label").inner_text().strip(),
            "skill": page.locator("#k-skill").inner_text().strip(),
            "skill_label": page.locator("#skill-value-label").inner_text().strip(),
            "badge_mcp": page.locator("#badge-mcp").inner_text().strip(),
            "badge_skill": page.locator("#badge-skill").inner_text().strip(),
        }
        shot(page, "13-系统状态-管理员", full=True)

        # 12. 数据管理 + 无原件文档预览（eval 或临时无原件文档）
        page.click("button[data-view='reports']")
        page.wait_for_selector("#admin-data-card:not([hidden])")
        out["checks"]["admin_data"] = {
            "doc_rows": page.locator("#admin-doc-body tr").count(),
            "review_rows": page.locator("#admin-review-body tr").count(),
        }
        # 找 eval 行（无效 doc_id 的现存记录），点预览，应显示友好提示而非 404 JSON
        eval_row = page.locator("#admin-doc-body tr", has_text="eval")
        if eval_row.count():
            eval_row.first.locator("button.locator", has_text="预览").click()
            page.wait_for_selector("#doc-preview:not([hidden])")
            page.wait_for_timeout(500)
            text = page.locator("#doc-preview-body").inner_text().strip()
            out["checks"]["eval_preview"] = {"text": text[:300], "has_404": "404" in text,
                                             "has_json": '"detail"' in text}
            shot(page, "14-数据管理-无原件文档提示")
            page.click("#btn-preview-close")
        out["checks"]["console_error_count"] = sum(1 for c in out["console"] if c["type"] == "error")
        browser.close()

    q.jdump(q.RAW / "ui-raw.json", out)
    print(json.dumps(out, ensure_ascii=False, indent=2)[:8000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
