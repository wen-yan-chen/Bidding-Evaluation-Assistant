"""补测：首屏 3 次；评审完成到结果渲染 3 次。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as q
from playwright.sync_api import sync_playwright

TEXT = """项目名称：测评UI性能项目
项目编号：QA-2026-UIPERF
采购人：测评采购人
投标人：测评投标人
投标报价：人民币 1,286,000.00 元
工期：90 日历天
技术方案：技术路线。
实施方案：实施计划。
质量保证措施：质量控制。
应急预案：应急保障。
类似项目业绩：合同业绩。
项目负责人：项目经理。
售后服务：售后服务。
"""


def main() -> int:
    q.ensure_dirs()
    path = q.RAW / "tmp_inputs" / "QA20261116-uiperf.txt"
    path.write_text(TEXT, encoding="utf-8")
    up = q.upload(path, name=path.name)
    doc_id = up["body"]["doc_id"]
    out = {"doc_id": doc_id, "loads": [], "renders": [], "console": []}
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
            for i in range(3):
                ctx = b.new_context(viewport={"width": 1440, "height": 960}, locale="zh-CN")
                page = ctx.new_page()
                page.set_default_timeout(45000)
                page.on("console", lambda msg: out["console"].append({"type": msg.type, "text": msg.text[:200]}))
                t0 = time.perf_counter()
                page.goto(q.BASE + "/#review", wait_until="domcontentloaded")
                page.wait_for_function("document.querySelectorAll('#doc-select option').length > 1")
                page.wait_for_selector("#profile-list .profile-card")
                app_ready = (time.perf_counter() - t0) * 1000
                perf = page.evaluate("""() => {
                    const n = performance.getEntriesByType('navigation')[0] || {};
                    const paints = Object.fromEntries(performance.getEntriesByType('paint').map(x => [x.name, x.startTime]));
                    return {fcp: paints['first-contentful-paint'], fp: paints['first-paint'],
                            dcl: n.domContentLoadedEventEnd, load: n.loadEventEnd};
                }""")
                out["loads"].append({"run": i + 1, "app_ready_ms": round(app_ready, 1), **perf})
                ctx.close()
            # 结果渲染 3 次
            ctx = b.new_context(viewport={"width": 1440, "height": 960}, locale="zh-CN")
            page = ctx.new_page()
            page.set_default_timeout(45000)
            page.goto(q.BASE + "/#review", wait_until="domcontentloaded")
            page.wait_for_function("document.querySelectorAll('#doc-select option').length > 1")
            page.select_option("#doc-select", value=doc_id)
            page.wait_for_function("(id) => document.querySelector('#sel-doc').textContent.includes(id)", arg=doc_id)
            for i in range(3):
                t0 = time.perf_counter()
                page.click("#btn-review")
                page.wait_for_selector("#review-result:not([hidden])")
                page.wait_for_function("document.getElementById('score-total').textContent.trim() !== '—'")
                ms = (time.perf_counter() - t0) * 1000
                out["renders"].append({"run": i + 1, "ms": round(ms, 1),
                                       "score": page.locator("#score-total").inner_text().strip()})
            b.close()
    finally:
        s = q.admin_login()
        s.delete(q.BASE + f"/api/admin/doc/{doc_id}", timeout=120)
    q.jdump(q.PERF / "ui-perf-extra.json", out)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
