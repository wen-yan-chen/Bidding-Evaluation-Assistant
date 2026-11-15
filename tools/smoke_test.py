"""D1 冒烟测试：服务起来之后跑一遍验收项，只用标准库（不装依赖也能验）。

验的就是 D1 的三条验收标准：
  1. 干净目录一次起服务成功     → 容器 healthy
  2. /health 返回 200           → 第 1 项
  3. 浏览器打开有页面           → 第 3、4 项（首页 + 静态资源 + 免责声明）

用法：
  python tools/smoke_test.py                              # 默认 http://127.0.0.1:8080
  python tools/smoke_test.py --base http://127.0.0.1:8000  # 本地直跑
  python tools/smoke_test.py --json                        # 机器可读结果（CI 用）
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DISCLAIMER = "AI 辅助评审结果，最终以评标委员会评审结论为准"


def fetch(base: str, path: str, timeout: float = 6.0) -> dict[str, Any]:
    url = base.rstrip("/") + path
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return {
                "ok": True,
                "status": resp.status,
                "headers": {k.lower(): v for k, v in resp.headers.items()},
                "body": raw,
                "ms": (time.perf_counter() - t0) * 1000,
                "url": url,
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "status": exc.code,
            "headers": {},
            "body": exc.read().decode("utf-8", "replace"),
            "ms": (time.perf_counter() - t0) * 1000,
            "url": url,
            "error": f"HTTP {exc.code}",
        }
    except Exception as exc:  # noqa: BLE001 - 探活脚本要把所有异常都变成可读结果
        return {
            "ok": False,
            "status": 0,
            "headers": {},
            "body": "",
            "ms": (time.perf_counter() - t0) * 1000,
            "url": url,
            "error": f"{type(exc).__name__}: {exc}",
        }


def as_json(result: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(result["body"])
    except (ValueError, KeyError):
        return {}


def run(base: str) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})

    health = fetch(base, "/health")
    body = as_json(health)
    add(
        "1. GET /health 返回 200 且 status=ok",
        health["status"] == 200 and body.get("status") == "ok",
        f"HTTP {health['status']} · {health['ms']:.0f} ms · {body or health.get('error', '')}",
    )

    api_health = fetch(base, "/api/health")
    ah = as_json(api_health)
    caps = ah.get("capabilities") or {}
    add(
        "2. GET /api/health 返回 200 且带能力开关",
        api_health["status"] == 200 and isinstance(caps, dict) and len(caps) >= 6,
        f"HTTP {api_health['status']} · capabilities {len(caps)} 项",
    )

    index = fetch(base, "/")
    html = index["body"]
    add(
        "3. 首页 200 且包含标题与免责声明",
        index["status"] == 200 and "招投标评审助手" in html and DISCLAIMER in html,
        f"HTTP {index['status']} · {len(html)} 字符 · 免责声明 {'有' if DISCLAIMER in html else '缺'}",
    )

    css = fetch(base, "/style.css")
    js = fetch(base, "/app.js")
    add(
        "4. 静态资源可访问（style.css / app.js）",
        css["status"] == 200 and js["status"] == 200,
        f"css {css['status']} / js {js['status']}",
    )

    info = fetch(base, "/api/info")
    inf = as_json(info)
    ms = inf.get("milestones") or {}
    ms_items = ms.get("items") or []
    d1_items = ms.get("d1_deliverables") or []
    add(
        "5. /api/info 配置齐全（里程碑 + D1 交付清单 + 无错误）",
        info["status"] == 200
        and len(ms_items) >= 7
        and len(d1_items) >= 7
        and not (inf.get("errors") or []),
        f"HTTP {info['status']} · 里程碑 {len(ms_items)} · D1 交付 {len(d1_items)}"
        f" · errors {len(inf.get('errors') or [])}",
    )

    version_file = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    versions = {
        "VERSION": version_file,
        "/health": body.get("version"),
        "/api/health": ah.get("version"),
        "/api/info": (inf.get("app") or {}).get("version"),
    }
    add(
        "6. 版本号四处一致（VERSION 单一来源）",
        len(set(v for v in versions.values() if v)) == 1 and version_file in versions.values(),
        " / ".join(f"{k}={v}" for k, v in versions.items()),
    )

    headers = health["headers"]
    add(
        "7. 响应带安全头（nosniff / frame-options）",
        headers.get("x-content-type-options") == "nosniff"
        and "x-frame-options" in headers,
        f"nosniff={headers.get('x-content-type-options')} "
        f"frame={headers.get('x-frame-options')}",
    )

    return checks


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="招投标评审助手 D1 冒烟测试")
    ap.add_argument("--base", default="http://127.0.0.1:8080", help="服务地址")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv)

    checks = run(args.base)
    passed = sum(1 for c in checks if c["pass"])

    if args.json:
        print(json.dumps(
            {"base": args.base, "passed": passed, "total": len(checks), "checks": checks},
            ensure_ascii=False, indent=2,
        ))
    else:
        print(f"冒烟测试 → {args.base}")
        print("-" * 78)
        for c in checks:
            print(f"{'PASS' if c['pass'] else 'FAIL'}  {c['name']}")
            print(f"      {c['detail']}")
        print("-" * 78)
        print(f"结果：{passed}/{len(checks)} 通过")

    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
