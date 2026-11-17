"""验证评审看板选择 eval（非法 doc_id）时的界面提示。"""
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
    page.set_default_timeout(30000)
    page.goto(q.BASE + "/#review", wait_until="domcontentloaded")
    page.wait_for_function("document.querySelectorAll('#doc-select option').length > 1")
    page.select_option("#doc-select", value="eval")
    page.wait_for_timeout(1500)
    out = {
        "notice": page.locator("#doc-degraded").inner_text().strip(),
        "visible": page.locator("#doc-degraded").is_visible(),
        "sel_doc": page.locator("#sel-doc").inner_text().strip(),
        "review_disabled": page.locator("#btn-review").is_disabled(),
    }
    print(json.dumps(out, ensure_ascii=False))
    q.jdump(q.RAW / "ui-eval.json", out)
    b.close()
