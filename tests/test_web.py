"""D8 前端静态约束：三视图、免责声明、自包含（无 CDN）。

这些断言只检查服务端托管的静态文件，不启动浏览器；用于防止后续改动把
「评审看板 / 报告中心」或免责声明文案弄丢，或误引入外链资源。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api import config
from api.main import app

client = TestClient(app)


def test_d8_views_and_disclaimer_present():
    html = client.get("/").text
    for token in ("评审看板", "报告中心", "系统状态", "双栏对照", "分项评分表", "资格性核验", "风险清单"):
        assert token in html, f"首页缺少 {token}"
    assert config.DISCLAIMER in html
    assert "选择文件" in html and "上传并解析" in html


def test_frontend_is_self_contained_without_cdn():
    html = client.get("/").text
    css = client.get("/style.css").text
    js = client.get("/app.js").text
    for name, text in (("index.html", html), ("style.css", css), ("app.js", js)):
        assert "http://" not in text, f"{name} 含外链 http://"
        assert "https://" not in text, f"{name} 含外链 https://"
    assert "@import" not in css, "style.css 不允许 @import 外链字体/样式"
    assert '<script src="app.js"></script>' in html
    assert client.get("/favicon.svg").status_code == 200
