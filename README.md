# 招投标评审助手

> 魔擎开发者激励 1 期 · 课题 8 · 政企采购 · 中级（¥6,000）
> 当前版本 **v0.1.0（D1 立骨完成）**：仓库能一次起服务，页面能自证，评审能力 D2 起接入。

面向政企采购场景的招投标文件辅助评审系统：解析招标/投标文件并**溯源到页码**，按招标文件的评分细则**逐项算分**，按 40 条规则库核验**资格性与合规风险**，输出可**点击跳回原文**的风险清单与可下载的审核报告。

> [!IMPORTANT]
> 本项目输出为**辅助建议**，不给出中标/废标结论。界面顶部、报告页脚与系统提示词三处固定提示：
> **AI 辅助评审结果，最终以评标委员会评审结论为准**

---

## 一、D1 交付状态

| D1 任务 | 交付物 | 状态 | 验证方式 |
| --- | --- | :-: | --- |
| 目录结构 | 本目录 | ✅ | 见下方「目录结构」 |
| `Dockerfile` | `Dockerfile` | ✅ | `docker compose build` |
| `docker-compose.yml` | `docker-compose.yml` | ✅ | `docker compose up -d` |
| `api` 空壳（`/health`） | `api/` | ✅ | `curl /health` → 200 |
| `web` 空壳 | `web/` | ✅ | 浏览器打开首页，自检 6 项全绿 |
| `agent.json` 草案 | `agent.json` `prompt.md` | ✅ | `python tools/agent_config.py check` |
| `README` 骨架 | 本文件 | ✅ | — |

D1 验收（当晚自测）：**干净目录一次起服务成功；`/health` 返回 200；浏览器打开有页面。**
证据见 [`docs/D1-自测记录.md`](docs/D1-自测记录.md)，交接说明见 [`docs/D1-交接文档.md`](docs/D1-交接文档.md)。

---

## 二、快速开始

```bash
# 1) 起服务（首次会构建镜像，约 1–3 分钟）
docker compose up -d --build

# 2) 看状态
docker compose ps                 # app 应为 healthy
curl http://127.0.0.1:8080/health # {"status":"ok", ...}

# 3) 打开页面
#    http://127.0.0.1:8080

# 4) 跑一遍 D1 验收（只用标准库，无需装依赖）
python tools/smoke_test.py
```

端口被占用时换一个：`HOST_PORT=18080 docker compose up -d`。
构建太慢或走不通网络：`docker compose build --build-arg PIP_INDEX_URL=https://pypi.org/simple`；
基础镜像拉不动（docker.io 几十 KB/s）时加 `BASE_IMAGE=docker.m.daocloud.io/library/python:3.11-slim`。
详细部署与排错见 [`DEPLOY.md`](DEPLOY.md)。

本地不起容器也可以跑：

```bash
pip install -r requirements.txt
python -m api.main                 # http://127.0.0.1:8000
python tools/smoke_test.py --base http://127.0.0.1:8000
```

---

## 三、目录结构

```text
行业智能体/政务/招投标评审助手/
├── api/                     # 服务层（FastAPI）：/health、/api/health、/api/info、静态托管
│   ├── main.py              #   应用入口（含安全头中间件、静态挂载）
│   ├── config.py            #   路径 / 环境变量 / 免责声明 / 版本号的唯一出口
│   └── routes/              #   health.py（探针）、meta.py（页面数据）
├── web/                     # 前端工程：状态页（D1），D8 补齐评审看板
│   ├── index.html  style.css  app.js
├── data/                    # 模拟数据与运行时产物
│   └── meta/milestones.json #   里程碑与 D1 清单（页面与文档同源）
├── agent.json               # Nexent 导入配置（草案：MCP 6 工具 + 4 Skill + 知识库检索）
├── prompt.md                # 系统提示词唯一来源，agent.json.prompt 由脚本同步
├── knowledge/               # 知识库资产（D4：40 条规则按节切分）            —— 待填充
├── mcps/                    # MCP 工具服务（D4：server.py + tools schema）    —— 待填充
├── skills/                  # 4 个自定义 Skill（D5）                          —— 待填充
├── docs/                    # 交接文档、测试报告、截图、演示视频
├── tools/                   # agent_config.py（配置校验）、smoke_test.py（冒烟）
├── tests/                   # pytest 接口单测
├── Dockerfile  docker-compose.yml  .env.example
├── requirements.txt  requirements-dev.txt
├── CHANGELOG.md  LICENSE  README.md  DEPLOY.md  VERSION
```

> 归类说明：赛题领域写「政企采购」，仓库现有行业分类只有医疗/政务/金融，暂按**政务**归档，已在 Issue 中确认。

---

## 四、八项交付物索引（随进度打勾）

| # | 交付物 | 路径 | 状态 |
| :-: | --- | --- | :-: |
| 1 | 前端工程 | `web/` | 🟡 D1 骨架（状态页） |
| 2 | 后端智能体工程 | `agent.json` `prompt.md` `mcps/` `skills/` `api/` | 🟡 D1 草案（配置校验通过） |
| 3 | 知识库资产 | `knowledge/` | ⬜ D4 |
| 4 | 模拟数据 | `data/` | ⬜ D2 起 |
| 5 | 部署文档 | `DEPLOY.md` `docker-compose.yml` | 🟡 D1 已可部署 |
| 6 | 使用文档 | `USAGE.md` | ⬜ D8 |
| 7 | 演示视频 | `docs/video/` | ⬜ D10 |
| 8 | 测试报告 | `docs/TEST_REPORT.md` | ⬜ D9 |

---

## 五、平台能力对照（Nexent 三件套）

| 能力 | 落地方式 | 当前状态 | 证据位 |
| --- | --- | --- | --- |
| 智能体编排 | `max_steps=15`；4 个 Skill 分阶段；步骤/终局校验开启 | 草案 | `agent.json` |
| 工具调用 | MCP 6 工具：`parse_tender` / `check_qualification` / `score_item` / `scan_risks` / `locate_span` / `export_report` | 已登记未挂载（D4） | `agent.json` → `mcp_info` |
| 知识库挂载 | 40 条规则按节切分，`hybrid` + `top_k=3` | 待建（D4） | `agent.json` → `index_names` |
| 自定义 Skill | `bid-rule-cards` / `missing-qualification` / `risk-selfcheck` / `summary-compiler` | 已登记未上传（D5） | `skills/` |

> 页面「平台能力接入」卡片直接读 `agent.json` 判断状态：**登记 ≠ 可用**，未落地一律显示"待接入"。
> ⚠️ 导入到其他环境前必须替换 `index_names`（格式 `<序号>-<hash>`），否则检索被权限过滤，依据会退化成"未检索到权威依据"。

---

## 六、接口一览

| 方法 | 路径 | 说明 | 状态 |
| --- | --- | :-: | --- |
| GET | `/health` | 容器探针，最小返回体 | ✅ D1 |
| GET | `/api/health` | 运行时长、能力开关（D1 全 false） | ✅ D1 |
| GET | `/api/info` | 智能体配置摘要 + 里程碑 + 免责声明 | ✅ D1 |
| GET | `/api/docs` | OpenAPI 交互文档 | ✅ D1 |
| POST | `/api/upload` | 上传招标/投标文件并解析 | ⬜ D2 |
| POST | `/api/review` | 触发一次完整评审 | ⬜ D5 |
| GET | `/api/review/{id}` | 取评审结果（含风险溯源） | ⬜ D5 |
| POST | `/api/report` | 导出 docx/pdf | ⬜ D7 |

---

## 七、开发与自测命令

```bash
python tools/agent_config.py sync     # prompt.md → agent.json.prompt（唯一写入方向）
python tools/agent_config.py check    # 配置校验：temperature、Skill/MCP 数量、占位符、免责声明
python tools/smoke_test.py            # 服务起来后的 7 项验收
pytest -q                             # 接口单测（需 requirements-dev.txt）
```

---

## 八、提交到 AgentsHub（fork 工作流）

提交目录必须是 fork 里的 `行业智能体/政务/招投标评审助手/`，开发在独立仓库进行，两者用脚本同步，避免漏文件。

```bash
# 一次性准备（已完成）
git clone --depth 1 --filter=blob:none --no-checkout https://gitcode.com/gcw_N79tXvDq/AgentsHub_3978.git D:\contest-8\AgentsHub
git -C D:\contest-8\AgentsHub sparse-checkout set 行业智能体/政务
git -C D:\contest-8\AgentsHub checkout -b feat/kw8-bid-reviewer

# 每天收工（同步 → 提交 → 推送）
powershell -File tools/sync_to_agentshub.ps1 -Commit -Push

# 只看差异不提交
powershell -File tools/sync_to_agentshub.ps1
```

- 脚本用 `robocopy /MIR` 镜像，排除 `.git` `__pycache__` `.pytest_cache` `data/uploads`（运行时产物）；
- 提交消息默认取开发仓库最新 commit 标题并加 `kw8:` 前缀，可用 `-Message` 覆盖；
- 演示视频默认不同步（`-IncludeVideo` 才带上），避免日常提交塞入大文件；
- fork 仓库：<https://gitcode.com/gcw_N79tXvDq/AgentsHub_3978>，长期分支 `feat/kw8-bid-reviewer`；
- PR 在 D10 提，标题按仓库规范：`[new agent] 招投标评审助手`。

> 注意：该脚本含中文路径，必须保存为 **UTF-8 with BOM**，否则 Windows PowerShell 5.1 会按 GBK 解析报错。

## 九、合规声明

- **无真实数据**：全部自造，主体名称为虚构（"示例市公共资源交易中心""某某建设工程有限公司"）。
- **不编造依据**：`basis_status=pending` 一律输出「未检索到权威依据」；`na` 输出「经验判据，无法条依据」。
- **不出最终结论**：只输出「疑似 / 建议复核」，最终以评标委员会评审结论为准。
- **个人信息脱敏**：界面与报告不展示真实姓名、身份证号、联系方式。
- **开源协议**：MIT（见 [`LICENSE`](LICENSE)）。

## 十、已知限制

- 仅覆盖货物/服务类招标，工程类（清单计价、施工组织）未覆盖；
- 围标串标特征为经验判据，无法条依据；
- 规则库法规依据需法务复核，`pending` 状态如实标注；
- OCR 对低分辨率扫描件会退化，届时显式提示"解析降级"而不是硬凑；
- D1 版本无任何评审能力，页面上未实现的功能一律标注"待接入"。
