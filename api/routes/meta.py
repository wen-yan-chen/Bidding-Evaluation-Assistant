"""元信息：页面渲染所需的一切都从文件读，不在前端硬编码。

- agent.json      → 智能体名称、Skill/MCP 登记情况、temperature 等关键参数
- data/meta/milestones.json → 里程碑与 D1 交付清单（唯一来源，文档与页面同源）
- VERSION         → 版本号

读文件失败不抛 500：返回 errors 列表，页面显式提示"配置未就绪"，
这样评审能一眼看出是配置问题而不是服务挂了。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from api import config

router = APIRouter(prefix="/api", tags=["meta"])

PLACEHOLDER_TOKENS = ("REPLACE_ME", "TODO", "<", "your-")


def _load_json(path: Path) -> tuple[Any, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except FileNotFoundError:
        return None, [f"缺少配置文件：{path.name}"]
    except json.JSONDecodeError as exc:
        return None, [f"{path.name} 不是合法 JSON：{exc}"]


def _agent_summary(agent: dict[str, Any] | None) -> dict[str, Any]:
    if not agent:
        return {"configured": False}
    info = (agent.get("agent_info") or {}).get("0") or {}
    mcp = agent.get("mcp_info") or []
    kb_tools = [t for t in info.get("tools") or [] if t.get("class_name") == "KnowledgeBaseSearchTool"]
    index_names = [n for t in kb_tools for n in (t.get("params") or {}).get("index_names") or []]
    # 占位符没换掉时，检索会被权限过滤，输出会退化成"未检索到权威依据"（手册 §5.7）
    kb_ready = bool(index_names) and not any(
        any(tok in str(name) for tok in PLACEHOLDER_TOKENS) for name in index_names
    )
    return {
        "configured": True,
        "name": info.get("name"),
        "display_name": info.get("display_name"),
        "max_steps": info.get("max_steps"),
        "skills": info.get("skill_names") or [],
        "mcp_server": (mcp[0] or {}).get("mcp_server_name") if mcp else None,
        "mcp_tools": [t.get("name") for s in mcp for t in s.get("tools") or []],
        "kb_index_ready": kb_ready,
        "kb_index_count": len(index_names),
        "temperature": (
            ((info.get("model_params_override") or {}).get("0") or {}).get("extra_params") or {}
        ).get("temperature"),
        "verification_enabled": bool((info.get("verification_config") or {}).get("enabled")),
    }


@router.get("/info", summary="智能体配置 + 里程碑 + 免责声明")
def info() -> dict[str, Any]:
    agent, agent_errors = _load_json(config.AGENT_FILE)
    milestones, ms_errors = _load_json(config.MILESTONES_FILE)

    return {
        "app": {
            "name": config.settings.app_name,
            "service": config.settings.service,
            "version": config.settings.version,
            "env": config.settings.env,
            "started_at": config.iso(config.STARTED_AT),
        },
        "agent": _agent_summary(agent),
        "milestones": milestones,
        "disclaimer": config.DISCLAIMER,
        "errors": agent_errors + ms_errors,
    }
