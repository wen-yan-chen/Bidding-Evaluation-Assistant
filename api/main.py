"""FastAPI 入口：D1 只保证"能起来、能自证"。

启动：
  容器内   docker compose up -d            → http://localhost:8080
  本地     python -m api.main              → http://127.0.0.1:8000
  热重载   uvicorn api.main:app --reload

静态前端由本服务托管（web/ 挂在根路径）。D1 不起第二个容器：
单容器 = 单次构建、单次健康检查，先保证"干净目录一次起服务成功"这条验收。
D4 引入 MCP 服务时会变成两容器（api + mcp），届时再拆。
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api import config
from api.routes import health, meta

class CstFormatter(logging.Formatter):
    """日志时间固定东八区：slim 镜像没有 tzdata，系统时区不可靠。"""

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        from datetime import datetime

        return datetime.fromtimestamp(record.created, config.CST).strftime(
            datefmt or "%Y-%m-%d %H:%M:%S"
        )


_handler = logging.StreamHandler()
_handler.setFormatter(CstFormatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
logging.basicConfig(level=config.settings.log_level.upper(), handlers=[_handler])
log = logging.getLogger("bid-review")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # 上传目录必须存在：D2 起直接往里写，且它是 compose 的挂载点
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    log.info(
        "start service=%s version=%s env=%s container=%s",
        config.settings.service,
        config.settings.version,
        config.settings.env,
        config.settings.is_container,
    )
    yield
    log.info("stop service=%s", config.settings.service)


app = FastAPI(
    title=f"{config.settings.app_name} · 服务层",
    version=config.settings.version,
    description="招投标文件解析、资格性核验、分项评分、风险扫描与报告导出（D1：骨架）。",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# 本地演示与内网部署，放开跨域；前端与 API 同源时这条不生效，留作扩展位
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):  # type: ignore[no-untyped-def]
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response


app.include_router(health.router)
app.include_router(meta.router)

# 静态资源必须最后挂载，否则 "/" 会吃掉上面的 API 路由
app.mount("/", StaticFiles(directory=str(config.WEB_DIR), html=True), name="web")


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=config.settings.host,
        port=config.settings.port,
        log_level=config.settings.log_level,
    )
