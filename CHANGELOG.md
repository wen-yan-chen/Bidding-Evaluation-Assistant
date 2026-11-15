# CHANGELOG

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与语义化版本。

## [0.1.0] — 2026-11-15（D1 立骨）

### Added

- 项目骨架：`api/`（FastAPI）、`web/`（状态页）、`data/meta/`、`docs/`、`tools/`、`tests/`。
- 服务层：`GET /health`（容器探针）、`GET /api/health`（含运行时长与 8 项能力开关）、
  `GET /api/info`（智能体配置摘要 + 里程碑 + 免责声明）、`/api/docs`（OpenAPI）。
- 前端状态页：服务自检 6 项、运行信息、平台能力接入状态、里程碑进度、D1 交付清单、
  顶部常驻免责声明；每 15 秒自动复检，无占位按钮。
- 部署：`Dockerfile`（多段复制、非缓存依赖层、标准库 HEALTHCHECK、`BASE_IMAGE` 可覆盖）、
  `docker-compose.yml`（显式项目名、端口可覆盖、`./data` 持久化、`host.docker.internal` 映射）、`.env.example`。
- 配置：`agent.json` 草案（MCP 6 工具 + 4 Skill + 知识库检索；`temperature=0`）、
  `prompt.md` 系统提示词 v0.1（角色/边界/七步流程/输出结构/免责）。
- 工具：`tools/agent_config.py`（prompt 同步 + 配置校验）、`tools/smoke_test.py`（7 项验收，仅标准库）。
- 测试：`tests/test_health.py` 7 条接口单测。
- 工具：`tools/sync_to_agentshub.ps1`（开发仓库 → fork 提交目录的镜像同步 + 可选提交/推送）。
- 文档：`README.md`（交付物索引 + 平台能力对照 + 接口一览 + fork 提交工作流）、`DEPLOY.md`（干净环境复现清单）、
  `docs/D1-交接文档.md`、`docs/D1-自测记录.md`。
- 仓库：fork <https://gitcode.com/gcw_N79tXvDq/AgentsHub_3978>，长期分支 `feat/kw8-bid-reviewer`；
  `agent.json` 的 `author` 填为 AtomGit 用户名 `gcw_N79tXvDq`。

### Notes

- D1 范围只做"能起服务 + 能自证"：解析、核验、评分、风险扫描、报告导出均未实现，
  页面与 `/api/health` 的 `capabilities` 全部显式为 `false`。
- `agent.json` 中的 `author`、`index_names` 为占位符，导入 Nexent 前必须替换（见 README §5）。
