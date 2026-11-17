"""阶段 1 后 UI 冒烟：文档列表、bid-001 评审、控制台错误。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as q
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
    ctx = b.new_context(viewport={"width": 1440, "height": 960}, locale="zh-CN")
    page = ctx.new_page()
    page.set_default_timeout(45000)
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto(q.BASE + "/#review", wait_until="domcontentloaded")
    page.wait_for_function("document.querySelectorAll('#doc-select option').length > 1")
    options = page.locator("#doc-select option")
    values = [options.nth(i).get_attribute("value") for i in range(options.count())]
    out = {"options": len(values), "has_eval": "eval" in values}
    bid = "20261116-3aced1a7"
    if bid in values:
        page.select_option("#doc-select", value=bid)
        page.wait_for_function("(id) => document.querySelector('#sel-doc').textContent.includes(id)", arg=bid)
        page.wait_for_selector("#pages .page", state="attached")
        page.click("#btn-review")
        page.wait_for_selector("#review-result:not([hidden])")
        page.wait_for_function("document.getElementById('score-total').textContent.trim() !== '—'")
        out["score"] = page.locator("#score-total").inner_text().strip()
        out["qual_rows"] = page.locator("#qual-body tr").count()
        out["review_id"] = page.locator("#score-review-id").inner_text().strip()
    out["console_errors"] = errors
    q.jdump(q.RAW / "phase1-ui.json", out)
    print(json.dumps(out, ensure_ascii=False))
    b.close()
    if out.get("review_id"):
        s = q.admin_login()
        s.delete(q.BASE + f"/api/admin/review/{out['review_id']}", timeout=120)
