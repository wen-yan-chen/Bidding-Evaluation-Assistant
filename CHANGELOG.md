# CHANGELOG

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与语义化版本。

## [0.2.0] — 2026-11-15（D2 解析层）

### Added

- 文档模型 `api/docmodel.py`：`Doc` / `PageSpan` / `Clause` / `SourceField`，页码映射走二分查，
  并提供 `slice_text` 越界保护与 `add_degraded` 降级记录。
- 解析器 `api/parsers/`：
  - `docx_parser`：段落与表格按正文顺序取出；优先按分页符切页，无分页符时按 1100 字/页估算并标 `degraded`；
  - `pdf_parser`：逐页取文本层，页码精确；空页（扫描页）如实标记页码；
  - `txt_parser`：编码嗅探（utf-8 / utf-8-sig / gb18030 / utf-16），按换页符或字数分页；
  - `clauses`：条款切分支持 第X章 / 第X条 / 一、 / 1.1 / （一） 五类编号，保留精确偏移；
  - `dispatch`：按扩展名分发，解析失败一律降级为 `parse_status=failed` + 原因，不抛 500。
- 字段抽取 `api/extract/fields.py`：项目名称 / 项目编号 / 采购人 / 投标人 / 报价 / 工期；
  报价支持"人民币 / ￥ / 万元 / 元"、工期支持"日历天 / 天 / 个月"；每个字段带 `page/char_start/char_end/quote`，
  切片不等于 quote 时直接丢弃（宁缺勿错）。
- 服务层接口：`POST /api/upload`、`GET /api/documents`、`GET /api/doc/{doc_id}`、`GET /api/doc/{doc_id}/raw`；
  结果落盘 `data/parsed/{doc_id}.json`，重启后可查；`doc_id` 正则校验，挡路径穿越。
- 前端「文档解析（D2 已上线）」面板：选择文件 → 上传解析 → 展示字段/页码/原文片段/降级说明；
  打开页面自动恢复最近一次解析结果（无占位按钮）。
- 模拟数据：`tools/make_samples.py` 生成 10 份样本（docx×5、pdf×2、txt×3，含 GB18030 与两份边界样本）
  与 `data/samples/manifest.json` 标准答案；主体名称、编号、金额全部虚构。
- 评测与校验：`tools/eval_parse.py`（解析成功率 / 字段准确率 / 多抽检测）、`tools/validate_quotes.py`
  （quote = 原文切片、页码与偏移一致、页码表连续覆盖全文）。
- 测试：`tests/test_parse.py` 9 条（docx/pdf/gb18030/边界/条款/拒收非白名单/上传→查询→取原文）。

### Changed

- `/api/health` 能力开关新增 `clause_split`，`parse` 与 `clause_split` 置 `true`。
- 页面「里程碑」按 `milestones.json` 的 `stage` 字段展示当前阶段交付物（不再写死 D1 清单），当前进度切到 D2。
- 版本号 `VERSION` 与 README/CHANGELOG 同步到 `0.2.0`。

### Verified

- `docker compose up -d --build` → 容器 `healthy`，`/health` 200；
- 10 份样本：解析成功率 **100%**、字段准确率 **58/58 = 100%**、边界样本 **0 处编造**；
- 10 份样本解析后：字段 58 个、条款 182 条，`validate_quotes.py` **0 处不一致**；
- `smoke_test.py` **9/9**；`pytest` **15 passed**；`agent_config.py check` 0 ERROR / 1 WARN（索引名占位）。

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
