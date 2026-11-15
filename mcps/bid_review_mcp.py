"""招投标评审 MCP 工具服务（D4）。

对外暴露三个**确定性**工具，供 Nexent 智能体调用：
- `parse_tender(doc_id)`  取解析结果：字段 + 页码 + 原文片段 + 条款摘要
- `scan_risks(doc_id)`    按规则库扫描风险：rule_id / level / page / quote / basis
- `locate_span(doc_id, quote)` 用原文片段反查页码与偏移（溯源兜底）

工程约束（手册 §5.6）：
- 一个工具只做一件事；入参出参只用 JSON 可序列化类型；
- 失败返回 `{"error": ...}`，不抛异常给模型；
- 幂等：同一 doc_id 反复调用结果完全一致；
- 不访问外网（不做遥测/回调）；
- 传输用 SSE（平台侧要求），本地也可 `python -c` 直接调函数自测。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from api import rules as rules_api  # noqa: E402
from api import store  # noqa: E402

mcp = FastMCP("bid-review")


def _error(message: str, **extra: Any) -> dict[str, Any]:
    return {"error": message, **extra}


def _load(doc_id: str):
    if not store.valid_doc_id(doc_id):
        return None, _error(f"doc_id 格式不合法：{doc_id}（应为 YYYYMMDD-8位hex）")
    doc = store.load_doc(doc_id)
    if doc is None:
        return None, _error(
            f"未找到文档：{doc_id}",
            hint="先用 POST /api/upload 上传并解析，再把这个 doc_id 传给工具",
        )
    return doc, None


@mcp.tool()
def parse_tender(doc_id: str) -> dict[str, Any]:
    """取招标/投标文件的解析结果。

    返回：文件信息、页数、解析状态与降级说明、6 个关键字段（每个带 page/char_start/char_end/quote）、
    条款清单（clause_id/label/title/page 与文本前 80 字）。不返回全文，避免把大段文本塞给模型。
    """
    doc, err = _load(doc_id)
    if err:
        return err

    return {
        "doc_id": doc.doc_id,
        "file_name": doc.file_name,
        "ext": doc.ext,
        "page_count": len(doc.pages),
        "page_source": doc.page_source,
        "parse_status": doc.parse_status,
        "degraded": doc.degraded,
        "ocr_pages": doc.meta.get("ocr_pages") or [],
        "fields": [
            {
                "name": f.name,
                "value": f.value,
                "page": f.page,
                "char_start": f.char_start,
                "char_end": f.char_end,
                "quote": f.quote,
            }
            for f in doc.fields
        ],
        "clauses": [
            {
                "clause_id": c.clause_id,
                "label": c.label,
                "title": c.title,
                "page": c.page,
                "char_start": c.char_start,
                "char_end": c.char_end,
                "preview": c.text[:80],
            }
            for c in doc.clauses
        ],
        "note": "字段与条款均带页码与字符偏移，可直接用于溯源展示。",
    }


@mcp.tool()
def scan_risks(doc_id: str, rule_ids: list[str] | None = None) -> dict[str, Any]:
    """按规则库扫描合规风险。

    `rule_ids` 为空时扫描全部可自动检测的规则；每条命中返回
    `rule_id / level / page / char_start / char_end / quote / legal_basis / basis_status`。
    只做字面量匹配，不做语义推理；`basis_status=pending` 时 legal_basis 为「未检索到权威依据」。
    """
    doc, err = _load(doc_id)
    if err:
        return err

    all_rules = rules_api.load_rules()
    if rule_ids:
        wanted = {r.strip().upper() for r in rule_ids}
        selected = tuple(r for r in all_rules if r.id in wanted)
        missing = sorted(wanted - {r.id for r in selected})
    else:
        selected = all_rules
        missing = []

    hits = rules_api.scan_doc(doc, selected)
    hits.sort(key=lambda h: ({"高": 0, "中": 1, "低": 2}.get(h["level"], 3), h["page"], h["char_start"]))
    return {
        "doc_id": doc.doc_id,
        "rule_digest": rules_api.rules_digest(),
        "rule_total": len(all_rules),
        "scanned_rules": len([r for r in selected if r.detect == "pattern"]),
        "hit_count": len(hits),
        "hits": hits,
        "missing_rule_ids": missing,
        "note": "命中即「疑似」，需人工复核；pending 依据不编造条号。",
    }


@mcp.tool()
def locate_span(doc_id: str, quote: str) -> dict[str, Any]:
    """用原文片段反查页码与字符偏移（溯源兜底）。

    用于"模型引用了某句话但没给页码"的场景：把 quote 传进来，返回它在文档中的位置与所在条款。
    """
    doc, err = _load(doc_id)
    if err:
        return err

    quote = (quote or "").strip()
    if not quote:
        return _error("quote 不能为空")

    start = doc.full_text.find(quote)
    if start < 0:
        return {
            "doc_id": doc.doc_id,
            "found": False,
            "message": "原文中未找到该片段（可能是 OCR 误识别或模型改写，请核对后重试）",
        }

    end = start + len(quote)
    page = doc.page_of(start)
    clause = None
    for item in doc.clauses:
        if item.char_start <= start < item.char_end:
            clause = {"clause_id": item.clause_id, "label": item.label, "title": item.title}
            break
    return {
        "doc_id": doc.doc_id,
        "found": True,
        "page": page,
        "char_start": start,
        "char_end": end,
        "quote": doc.slice_text(start, end),
        "clause": clause,
    }


def _relax_transport_security() -> None:
    """容器内以服务名互访时 Host 头是 mcp:8765；新版 MCP 的 DNS rebinding 防护会返回 421。

    内网部署、不暴露公网，因此关闭该校验；若将来暴露公网，应改为 allowed_hosts 白名单。
    """
    try:
        from mcp.server.transport_security import TransportSecuritySettings

        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        )
    except Exception:  # 旧版本没有该配置项，忽略即可
        pass


def main() -> None:
    _relax_transport_security()
    port = int(os.getenv("MCP_PORT", "8765"))
    host = os.getenv("MCP_HOST", "0.0.0.0")
    mcp.settings.host = host
    mcp.settings.port = port
    print(f"bid-review MCP server: sse://{host}:{port}/sse ｜ rules={rules_api.rules_digest()}", flush=True)
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
