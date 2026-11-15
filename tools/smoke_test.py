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
import uuid
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


def upload_file(base: str, path: Path, field: str = "file", timeout: float = 60.0) -> dict[str, Any]:
    """构造 multipart 请求上传一个文件（只用标准库，不依赖 requests）。"""
    boundary = "----bidreview" + uuid.uuid4().hex
    body = bytearray()
    body += f"--{boundary}\r\n".encode("utf-8")
    body += (
        f'Content-Disposition: form-data; name="{field}"; filename="{path.name}"\r\n'
    ).encode("utf-8")
    body += b"Content-Type: application/octet-stream\r\n\r\n"
    body += path.read_bytes()
    body += f"\r\n--{boundary}--\r\n".encode("utf-8")

    url = base.rstrip("/") + "/api/upload"
    request = urllib.request.Request(
        url,
        data=bytes(body),
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return {
                "ok": True,
                "status": resp.status,
                "headers": {},
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
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status": 0,
            "headers": {},
            "body": "",
            "ms": (time.perf_counter() - t0) * 1000,
            "url": url,
            "error": f"{type(exc).__name__}: {exc}",
        }


def verify_doc_payload(data: dict[str, Any]) -> list[str]:
    """在前端/脚本侧独立复核：字段切片必须等于 quote，页码必须与偏移一致。"""
    text = data.get("full_text") or ""
    pages = data.get("pages") or []
    problems: list[str] = []

    def page_of(offset: int) -> int | None:
        for span in pages:
            if span["start"] <= offset < span["end"]:
                return span["page"]
        return pages[-1]["page"] if pages and offset == len(text) else None

    for field in data.get("fields") or []:
        sliced = text[field["char_start"] : field["char_end"]]
        if sliced != field["quote"]:
            problems.append(f"{field['name']}: 切片≠quote")
            continue
        actual_page = page_of(field["char_start"])
        if actual_page is not None and actual_page != field["page"]:
            problems.append(f"{field['name']}: 声明第 {field['page']} 页，实际第 {actual_page} 页")
    return problems


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
    stage_items = (ms.get("stage") or {}).get("items") or ms.get("d1_deliverables") or []
    add(
        "5. /api/info 配置齐全（里程碑 + 阶段交付清单 + 无错误）",
        info["status"] == 200
        and len(ms_items) >= 7
        and len(stage_items) >= 7
        and not (inf.get("errors") or []),
        f"HTTP {info['status']} · 里程碑 {len(ms_items)} · 阶段交付 {len(stage_items)}"
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

    # ---- D2：上传 → 解析 → 溯源自洽（端到端，走真实 HTTP）
    sample = ROOT / "data" / "samples" / "bid-001.docx"
    if sample.exists():
        uploaded = upload_file(base, sample)
        payload = as_json(uploaded)
        fields = payload.get("fields") or []
        add(
            "8. 上传样本 → 解析成功且抽到 6 个字段",
            uploaded["status"] == 200
            and payload.get("parse_status") in ("ok", "degraded")
            and len(fields) >= 6,
            f"HTTP {uploaded['status']} · status={payload.get('parse_status')} · "
            f"字段={len(fields)} · 页={payload.get('page_count')} · 条款={payload.get('clause_count')}",
        )

        doc_id = payload.get("doc_id")
        detail = fetch(base, f"/api/doc/{doc_id}") if doc_id else {"status": 0, "body": "{}"}
        problems = verify_doc_payload(as_json(detail))
        add(
            "9. 字段溯源自洽（quote = 原文切片，页码与偏移一致）",
            detail["status"] == 200 and not problems,
            "全部自洽" if not problems else "；".join(problems[:3]),
        )
    else:
        add("8. 上传样本 → 解析成功且抽到 6 个字段", False, "缺少 data/samples/bid-001.docx")
        add("9. 字段溯源自洽（quote = 原文切片，页码与偏移一致）", False, "无样本，跳过")

    # ---- D3：扫描件走 OCR（无文本层 PDF）
    scan = ROOT / "data" / "samples" / "scan-001.pdf"
    if scan.exists():
        scanned = upload_file(base, scan, timeout=180.0)
        payload = as_json(scanned)
        ocr_pages = payload.get("ocr_pages") or []
        fields = payload.get("fields") or []
        add(
            "10. 扫描件走 OCR 解析（无文本层 PDF）",
            scanned["status"] == 200
            and payload.get("parse_status") in ("ok", "degraded")
            and len(ocr_pages) >= 1
            and len(fields) >= 4,
            f"HTTP {scanned['status']} · 状态={payload.get('parse_status')} · "
            f"OCR 页={len(ocr_pages)} · 字段={len(fields)} · 耗时={scanned['ms'] / 1000:.1f}s",
        )
    else:
        add("10. 扫描件走 OCR 解析（无文本层 PDF）", False, "缺少 data/samples/scan-001.pdf")

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
