# 部署文档

> 适用版本：v0.1.0（D1）。目标：**干净环境一次起服务成功**。

## 1. 环境要求

| 项 | 要求 | 检查命令 |
| --- | --- | --- |
| Docker | ≥ 24，且 daemon 已启动 | `docker version` |
| Docker Compose | v2 插件（`docker compose`，非 `docker-compose`） | `docker compose version` |
| 端口 | 宿主 8080 可占用（可用 `HOST_PORT` 覆盖） | `netstat -ano \| findstr 8080` |
| 资源 | ≥ 2 GB 内存、≥ 1 GB 磁盘（镜像约 300 MB） | — |

Python 3.11+ 仅本地直跑时需要，容器内已自带。

## 2. 一键部署

```bash
# 进入项目目录（含 docker-compose.yml）
docker compose up -d --build
```

期望输出：

```text
[+] Running 2/2
 ✔ Network bid-review_default  Created
 ✔ Container bid-review        Started
```

验证：

```bash
docker compose ps                              # STATUS 应为 Up ... (healthy)
curl -i http://127.0.0.1:8080/health           # HTTP/1.1 200 OK
curl -s http://127.0.0.1:8080/api/info | head  # 含 version / milestones
python tools/smoke_test.py                     # 7/7 通过
```

浏览器打开 <http://127.0.0.1:8080>，「服务自检」6 项应全部为绿。

## 3. 配置项

复制 `.env.example` 为 `.env` 后修改（不改也能起，全部有默认值）：

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `HOST_PORT` | `8080` | 宿主机端口，冲突时改这里 |
| `PIP_INDEX_URL` | 清华源 | 构建期 pip 源；海外或清华源异常时改 `https://pypi.org/simple` |
| `BASE_IMAGE` | `python:3.11-slim` | 基础镜像；docker.io 拉不动时改 `docker.m.daocloud.io/library/python:3.11-slim` |
| `APP_TAG` | `0.1.0` | 镜像 tag |
| `APP_ENV` | `docker` | 环境标识，显示在页面与日志 |
| `LOG_LEVEL` | `info` | `debug` / `info` / `warning` |
| `MAX_UPLOAD_MB` | `50` | 单文件上限（D2 起生效） |
| `MCP_URL` | `http://127.0.0.1:8765/sse` | D4 起改为 `http://mcp:8765/sse` |
| `NEXENT_BASE` | 空 | D7 端到端联调时填平台地址 |

## 4. 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `project name must not be empty` | 目录名是中文，Compose 推导项目名失败 | 已用 `name: bid-review` 固定；若自行改名 compose 文件需保留该字段 |
| 构建卡在 `pip install` | 默认源不可达 | `docker compose build --build-arg PIP_INDEX_URL=https://pypi.org/simple` |
| 构建卡在拉基础镜像（几十 KB/s） | docker.io 直连慢 | `BASE_IMAGE=docker.m.daocloud.io/library/python:3.11-slim docker compose up -d --build`，或复用本机已有镜像的 digest：`BASE_IMAGE=python@sha256:<digest>` |
| 端口占用 | 8080 被其他服务占用 | `HOST_PORT=18080 docker compose up -d` |
| 容器 `unhealthy` | 应用未起或 15 秒内未就绪 | `docker compose logs app`；`start-period=15s` 已留余量 |
| 页面显示"配置未就绪" | `agent.json` 或 `milestones.json` 缺失/格式错 | `python tools/agent_config.py check`；查看 `/api/info` 的 `errors` |
| Linux 上上传失败（D2 起） | 绑定挂载目录权限 | `sudo chown -R 1000:1000 data/`，或按 Dockerfile 注释改非 root |
| 改了代码但页面没变 | 镜像未重建 | `docker compose up -d --build` |

## 5. 停止与清理

```bash
docker compose down            # 停服务，保留 data/
docker compose down --rmi local  # 同时删本地镜像
docker compose logs -f app     # 看日志
```

`./data` 是绑定挂载，`down` 不会删除；上传件与结果都在里面。

## 6. 干净环境复现清单（提交前逐条勾）

- [ ] 新机器 `git clone` → `docker compose up -d --build` → `docker compose ps` 显示 healthy
- [ ] `curl http://127.0.0.1:<port>/health` 返回 200
- [ ] 浏览器打开首页，「服务自检」6 项全绿
- [ ] `python tools/smoke_test.py` 7/7 通过
- [ ] `python tools/agent_config.py check` 无 ERROR
