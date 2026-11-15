"""健康检查：容器 HEALTHCHECK 与前端自检都打这里。

两个路径都保留：
- `/health`     给 docker HEALTHCHECK / 负载均衡用，返回体最小；
- `/api/health` 给前端与脚本用，多带运行时长与能力开关。
"""

from __future__ import annotations

import platform
from typing import Any

from fastapi import APIRouter

from api import config

router = APIRouter(tags=["health"])


def _uptime_seconds() -> int:
    return int((config.now() - config.STARTED_AT).total_seconds())


@router.get("/health", summary="健康检查（容器探针）")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": config.settings.service,
        "version": config.settings.version,
    }


@router.get("/api/health", summary="健康检查（含运行时详情）")
def health_detail() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": config.settings.service,
        "app": config.settings.app_name,
        "version": config.settings.version,
        "env": config.settings.env,
        "started_at": config.iso(config.STARTED_AT),
        "checked_at": config.iso(config.now()),
        "uptime_seconds": _uptime_seconds(),
        "python": platform.python_version(),
        "in_container": config.settings.is_container,
        # 能力开关：随里程碑推进逐项置 true，页面据此显示"待接入"
        "capabilities": {
            "parse": True,         # D2 文档解析 + 页码映射 + 字段抽取（已上线）
            "clause_split": True,  # D2 条款切分（已上线）
            "qualification": False,  # D5 资格性核验
            "scoring": False,      # D5 分项评分
            "risk_scan": False,    # D6 风险扫描
            "report_export": False,  # D7 docx/pdf 导出
            "mcp": False,          # D4 MCP 工具服务
            "knowledge_base": False,  # D4 知识库
            "skills": False,       # D5 Skill 挂载
        },
        "disclaimer": config.DISCLAIMER,
    }
