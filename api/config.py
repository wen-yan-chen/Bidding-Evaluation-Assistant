"""配置与路径：整个服务层唯一的路径/环境变量出口。

约定：
- 所有路径都相对项目根目录推导，容器内外一致（Dockerfile 把项目根放 /app）。
- 版本号只认根目录 VERSION 文件，避免 README / 镜像 tag / 接口三处各写一份。
- 免责声明只在这里写一次，页面、报告页脚、提示词都引用同一句。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 容器内不用 zoneinfo（slim 镜像未必带 tzdata），固定东八区，避免时区缺失报错
CST = timezone(timedelta(hours=8))

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
DATA_DIR = ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
META_DIR = DATA_DIR / "meta"
AGENT_FILE = ROOT / "agent.json"
PROMPT_FILE = ROOT / "prompt.md"
MILESTONES_FILE = META_DIR / "milestones.json"
VERSION_FILE = ROOT / "VERSION"

# 赛题硬要求：三处提示（界面顶部 / 报告页脚 / 系统提示词），文案必须一字不差
DISCLAIMER = "AI 辅助评审结果，最终以评标委员会评审结论为准"

STARTED_AT = datetime.now(CST)


def read_version() -> str:
    """读 VERSION 文件；读不到时退化为环境变量或 0.0.0，不让服务起不来。"""
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return os.getenv("APP_VERSION", "0.0.0")


def now() -> datetime:
    return datetime.now(CST)


def iso(ts: datetime) -> str:
    return ts.isoformat(timespec="seconds")


@dataclass(frozen=True)
class Settings:
    """运行时配置。D1 只用得到 env / host / port / 日志级别。"""

    app_name: str = "招投标评审助手"
    service: str = "bid-review-api"
    version: str = field(default_factory=read_version)
    env: str = field(default_factory=lambda: os.getenv("APP_ENV", "dev"))
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "info"))
    max_upload_mb: int = field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_MB", "50")))
    mcp_url: str = field(default_factory=lambda: os.getenv("MCP_URL", "http://127.0.0.1:8765/sse"))
    nexent_base: str = field(default_factory=lambda: os.getenv("NEXENT_BASE", ""))

    @property
    def is_container(self) -> bool:
        return Path("/.dockerenv").exists()


settings = Settings()
