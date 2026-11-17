from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("docs/screenshots")
OUT.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:18081"

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(BASE + "/#review", wait_until="networkidle")

    # 报告中心
    page.locator("button.navbtn[data-view='reports']").click()
    page.wait_for_timeout(1500)
    page.locator("#view-reports").screenshot(path=str(OUT / "20261117-05-报告中心.png"))

    previews = page.get_by_role("button", name="预览")
    if previews.count():
        previews.first.click()
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / "20261117-06-报告预览.png"), full_page=False)
        close = page.get_by_role("button", name="关闭")
        if close.count():
            close.first.click()

    # 系统状态 + 管理员登录
    page.locator("button.navbtn[data-view='status']").click()
    page.wait_for_timeout(800)
    page.fill("#admin-user", "admin")
    page.fill("#admin-pass", "BidReview@2026")
    page.click("#btn-admin-login")
    page.wait_for_timeout(1500)
    page.locator("#view-status").screenshot(path=str(OUT / "20261117-07-系统状态.png"))

    # 数据管理在同一页；滚到数据管理区域
    dm = page.locator("#admin-panel")
    if dm.count():
        dm.screenshot(path=str(OUT / "20261117-08-数据管理.png"))
    browser.close()
print("done")
