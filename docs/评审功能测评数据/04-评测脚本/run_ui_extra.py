"""补拍数据管理区与未登录状态截图。"""
from __future__ import annotations

import sys
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
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
        ctx = b.new_context(viewport={"width": 1440, "height": 960}, locale="zh-CN")
        page = ctx.new_page()
        page.set_default_timeout(45000)

        page.goto(q.BASE + "/#status", wait_until="domcontentloaded")
        page.wait_for_selector("#status-lock")
        page.wait_for_timeout(800)
        page.screenshot(path=str(q.SHOTS / "20261116-12-系统状态-未登录.png"))

        user, password = creds()
        page.fill("#admin-user", user)
        page.fill("#admin-pass", password)
        page.click("#btn-admin-login")
        page.wait_for_selector("#status-content:not([hidden])")
        page.click("button[data-view='reports']")
        page.wait_for_selector("#admin-data-card:not([hidden])")
        page.wait_for_function("document.querySelectorAll('#admin-doc-body tr').length > 20", timeout=60000)
        page.locator("#admin-data-card").scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        page.screenshot(path=str(q.SHOTS / "20261116-15-数据管理.png"))

        # 把 eval 行滚动到可见位置再拍一张（不打开弹窗）
        eval_row = page.locator("#admin-doc-body tr", has_text="eval")
        if eval_row.count():
            eval_row.first.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            page.screenshot(path=str(q.SHOTS / "20261116-16-数据管理-eval行.png"))
        print("ok")
        b.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
