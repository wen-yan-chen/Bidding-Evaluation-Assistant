# 招投标评审助手

> 魔擎开发者激励 1 期 · 课题 8 · 政企采购 · 中级（¥6,000）
> 当前版本 **v0.4.0（D4 规则库 + 知识库 + MCP）**：40 条规则库（依据三态）、知识库自动导出（指纹锁一致）、
> MCP 三个工具（解析 / 扫描 / 溯源）已通过协议实测。资格性核验与评分 D5 起接入。

面向政企采购场景的招投标文件辅助评审系统：解析招标/投标文件并**溯源到页码**，按招标文件的评分细则**逐项算分**，按 40 条规则库核验**资格性与合规风险**，输出可**点击跳回原文**的风险清单与可下载的审核报告。

> [!IMPORTANT]
> 本项目输出为**辅助建议**，不给出中标/废标结论。界面顶部、报告页脚与系统提示词三处固定提示：
> **AI 辅助评审结果，最终以评标委员会评审结论为准**

---

## 一、当前进度

### D4 规则库 + 知识库 + MCP（v0.4.0）

| D4 任务 | 交付物 | 状态 | 验证方式 |
| --- | --- | :-: | --- |
| 40 条规则（四类各 10 条） | `data/rules/rules.yaml` | ✅ | `python tools/validate_rules.py` |
| 依据三态（verified/pending/na） | `Rule.legal_basis` 唯一出口 | ✅ | 单测逐条断言：pending 必输出「未检索到权威依据」 |
| 知识库导出 + 指纹 | `knowledge/rules-full.md`（40 块）+ `manifest.json` | ✅ | 与 YAML 指纹一致 |
| 知识库导入 | 平台 `bid-review-rules`，索引 `2-c6515aaca42f46c58554031ab149e820` | ✅ | 平台文档状态 COMPLETED |
| 规则库接口 | `GET /api/rules`、`/stats`、`/{rule_id}` | ✅ | 返回 40 条 + 统计 + 指纹 |
| MCP 三工具 | `parse_tender` / `scan_risks` / `locate_span` | ✅ | MCP 协议实测（SSE，3 工具可用） |
| compose 双服务 | `app` + `mcp`（8765，共用 `./data`） | ✅ | `docker compose ps` 两容器 healthy |

**D4 验收**：40 条规则、四类各 10、依据 21 验证 / 15 待核验 / 4 经验判据；知识库 40 块与规则库指纹一致；
MCP 扫描 20 条可自动检测规则、命中 6 条且每条带 `page/quote`。
证据见 [`docs/D4-自测记录.md`](docs/D4-自测记录.md)，交接说明见 [`docs/D4-交接文档.md`](docs/D4-交接文档.md)。

### D3 解析层收尾（v0.3.0）

| D3 任务 | 交付物 | 状态 | 验证方式 |
| --- | --- | :-: | --- |
| 扫描件 OCR（锁版本、离线） | `api/parsers/ocr.py` | ✅ | 5 份扫描件全部识别 |
| 扫描页并入页码表 | `api/parsers/pdf_parser.py` | ✅ | `meta.ocr_pages` 标注，溯源仍 0 不一致 |
| 低质量件降级提示 | 置信度 < 0.30 丢行并计数 | ✅ | 低清样本少抽 1 字段、0 编造 |
| 边界样本 | `data/samples/boundary/`（空白/低清/旋转） | ✅ | 3 份全部降级但不崩 |
| docx 页码改按行估算 | `api/parsers/docx_parser.py` | ✅ | 每页 38 行 × 38 字，更贴近 Word 分页 |
| 扫描件指标单列 | `tools/eval_parse.py` | ✅ | 文本层 10/10、扫描件 5/5 |
| 端到端冒烟增扫描件 | `tools/smoke_test.py` | ✅ | 10/10 |

**D3 验收（当晚自测）**：15 份样本（10 文本层 + 5 扫描件）解析成功率 **100%**、字段准确率 **88/88 = 100%**、
溯源 **0 处不一致**；扫描件最慢 16.2 s/份（3 页 / 200 DPI）。
证据见 [`docs/D3-自测记录.md`](docs/D3-自测记录.md)，交接说明见 [`docs/D3-交接文档.md`](docs/D3-交接文档.md)。

### D2 解析层（v0.2.0）

| D2 任务 | 交付物 | 状态 | 验证方式 |
| --- | --- | :-: | --- |
| 文档模型 + 页码/偏移映射 | `api/docmodel.py` | ✅ | `page_of()` 二分查页，页码表连续覆盖全文 |
| docx / pdf / txt 解析 | `api/parsers/` | ✅ | 10 份文本层样本解析成功率 100% |
| 条款切分（章/条/一、/1.1/（一）） | `api/parsers/clauses.py` | ✅ | 10 份样本共切出 182 条条款 |
| 6 字段抽取 + 溯源三元组 | `api/extract/fields.py` | ✅ | 58/58 字段命中，0 处编造 |
| 上传 / 查询 / 取原文接口 | `api/routes/docs.py` | ✅ | `POST /api/upload` → `200` |
| 10 份模拟样本 + 标准答案 | `data/samples/` | ✅ | `python tools/eval_parse.py` |
| 溯源校验脚本 | `tools/validate_quotes.py` | ✅ | 58 字段 / 182 条款，0 处不一致 |
| 前端解析面板（选择文件→解析→看字段与原文） | `web/` | ✅ | 页面「文档解析（D2 已上线）」 |

**D2 验收（当晚自测）**：解析成功率 **10/10 = 100%**（要求 ≥90%）；字段准确率 **58/58 = 100%**（要求 ≥90%）；
`quote` 与原文切片、页码与偏移 **100% 自洽**；边界样本（缺报价/缺工期）**0 处编造**。
证据见 [`docs/D2-自测记录.md`](docs/D2-自测记录.md)，交接说明见 [`docs/D2-交接文档.md`](docs/D2-交接文档.md)。

### D1 立骨（v0.1.0，已完成）

| D1 任务 | 交付物 | 状态 | 验证方式 |
| --- | --- | :-: | --- |
| 目录结构 | 本目录 | ✅ | 见下方「目录结构」 |
| `Dockerfile` | `Dockerfile` | ✅ | `docker compose build` |
| `docker-compose.yml` | `docker-compose.yml` | ✅ | `docker compose up -d` |
| `api` 空壳（`/health`） | `api/` | ✅ | `curl /health` → 200 |
| `web` 空壳 | `web/` | ✅ | 浏览器打开首页，自检 6 项全绿 |
| `agent.json` 草案 | `agent.json` `prompt.md` | ✅ | `python tools/agent_config.py check` |
| `README` 骨架 | 本文件 | ✅ | — |

D1 验收：**干净目录一次起服务成功；`/health` 返回 200；浏览器打开有页面。**
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
├── api/                     # 服务层（FastAPI）
│   ├── main.py              #   应用入口（安全头中间件、路由挂载、静态托管）
│   ├── config.py            #   路径 / 环境变量 / 免责声明 / 版本号的唯一出口
│   ├── docmodel.py          #   Doc / PageSpan / Clause / SourceField + 页码映射（二分）
│   ├── store.py             #   原文与解析结果落盘（data/uploads、data/parsed）
│   ├── parsers/             #   docx / pdf / txt / OCR 解析 + 条款切分 + 分发（失败降级）
│   ├── extract/             #   6 个关键字段抽取（确定性规则 + 溯源三元组）
│   └── routes/              #   health / meta / docs（上传、查询、取原文）
├── web/                     # 前端工程：状态页 + D2 解析面板（D8 补齐评审看板）
│   ├── index.html  style.css  app.js
├── data/                    # 模拟数据与运行时产物
│   ├── samples/             #   15 份样本（含 5 份扫描件）+ boundary + manifest.json
│   ├── rules/rules.yaml     #   40 条规则（四类各 10 条，依据三态）
│   ├── parsed/              #   解析结果 JSON（运行时生成，不进仓库）
│   └── meta/milestones.json #   里程碑与阶段交付清单（页面与文档同源）
├── agent.json               # Nexent 导入配置（草案：MCP 6 工具 + 4 Skill + 知识库检索）
├── prompt.md                # 系统提示词唯一来源，agent.json.prompt 由脚本同步
├── knowledge/               # 知识库资产：rules-full.md（40 块）+ manifest 指纹 ✅
├── mcps/                    # MCP 工具服务：bid_review_mcp.py（3 个工具）✅
├── skills/                  # 4 个自定义 Skill（D5）                          —— 待填充
├── docs/                    # 交接文档、自测记录、测试报告、截图、演示视频
├── tools/                   # 配置校验 / 冒烟 / 样本生成 / 溯源校验 / 指标复算 / fork 同步
├── tests/                   # pytest：接口 + 解析链路单测
├── Dockerfile  docker-compose.yml  .env.example
├── requirements.txt  requirements-dev.txt
├── CHANGELOG.md  LICENSE  README.md  DEPLOY.md  VERSION
```

> 归类说明：赛题领域写「政企采购」，仓库现有行业分类只有医疗/政务/金融，暂按**政务**归档，已在 Issue 中确认。

---

## 四、八项交付物索引（随进度打勾）

| # | 交付物 | 路径 | 状态 |
| :-: | --- | --- | :-: |
| 1 | 前端工程 | `web/` | 🟡 D3 状态页 + 解析面板（含 OCR 徽标，D8 补看板） |
| 2 | 后端智能体工程 | `agent.json` `prompt.md` `mcps/` `skills/` `api/` | 🟡 解析 + MCP 已通，Skill 待 D5 |
| 3 | 知识库资产 | `knowledge/` | 🟡 D4 已导出并导入（40 块，指纹一致） |
| 4 | 模拟数据 | `data/samples/` | 🟡 D3 已有 15 份（含 5 份扫描件）+ 3 份边界 + 标准答案（D9 扩到 20 份） |
| 5 | 部署文档 | `DEPLOY.md` `docker-compose.yml` | 🟡 D1 已可部署 |
| 6 | 使用文档 | `USAGE.md` | ⬜ D8 |
| 7 | 演示视频 | `docs/video/` | ⬜ D10 |
| 8 | 测试报告 | `docs/TEST_REPORT.md` | ⬜ D9 |

---

## 五、平台能力对照（Nexent 三件套）

| 能力 | 落地方式 | 当前状态 | 证据位 |
| --- | --- | --- | --- |
| 智能体编排 | `max_steps=15`；4 个 Skill 分阶段；步骤/终局校验开启 | 草案 | `agent.json` |
| 工具调用 | MCP 已实现 3 个（`parse_tender` / `scan_risks` / `locate_span`），D5–D7 补 `check_qualification` / `score_item` / `export_report` | 服务已上线（8765），平台登记待导入 | `mcps/`、`agent.json` → `mcp_info` |
| 知识库挂载 | 40 条规则一块一条，`bge-m3` 1024 维，`hybrid` + `top_k=3` | 已导入（索引 `2-c6515a…`） | `agent.json` → `index_names` |
| 自定义 Skill | `bid-rule-cards` / `missing-qualification` / `risk-selfcheck` / `summary-compiler` | 已登记未上传（D5） | `skills/` |

> 页面「平台能力接入」卡片直接读 `agent.json` 判断状态：**登记 ≠ 可用**，未落地一律显示"待接入"。
> ⚠️ 导入到其他环境前必须替换 `index_names`（格式 `<序号>-<hash>`），否则检索被权限过滤，依据会退化成"未检索到权威依据"。

---

## 六、接口一览

| 方法 | 路径 | 说明 | 状态 |
| --- | --- | :-: | --- |
| GET | `/health` | 容器探针，最小返回体 | ✅ D1 |
| GET | `/api/health` | 运行时长、9 项能力开关（D2 起 `parse` / `clause_split` 为 true） | ✅ D2 |
| GET | `/api/info` | 智能体配置摘要 + 里程碑 + 免责声明 | ✅ D1 |
| GET | `/api/rules` | 规则库（40 条 + 统计 + 指纹） | ✅ D4 |
| GET | `/api/rules/{rule_id}` | 单条规则（含依据三态解析） | ✅ D4 |
| GET | `/api/docs` | OpenAPI 交互文档 | ✅ D1 |
| POST | `/api/upload` | 上传招标/投标文件 → 解析 → 落盘 → 返回字段与溯源 | ✅ D2 |
| GET | `/api/documents` | 已解析文档列表 | ✅ D2 |
| GET | `/api/doc/{doc_id}` | 解析全文（含 `full_text`、页码表、条款、字段） | ✅ D2 |
| GET | `/api/doc/{doc_id}/raw` | 取原始文件（双栏对照用） | ✅ D2 |
| POST | `/api/review` | 触发一次完整评审 | ⬜ D5 |
| GET | `/api/review/{id}` | 取评审结果（含风险溯源） | ⬜ D5 |
| POST | `/api/report` | 导出 docx/pdf | ⬜ D7 |

---

## 七、开发与自测命令

```bash
python tools/agent_config.py sync     # prompt.md → agent.json.prompt（唯一写入方向）
python tools/agent_config.py check    # 配置校验：temperature、Skill/MCP 数量、占位符、免责声明
python tools/smoke_test.py            # 服务起来后的 10 项验收（含扫描件 OCR）
python tools/validate_rules.py        # 规则库门禁：条数/分类/依据三态/知识库指纹
python tools/export_kb.py --check     # 校验知识库导出是否与 YAML 一致
python tools/make_samples.py          # 重新生成 10 份样本 + 标准答案（--no-pdf 跳过 pdf）
python tools/eval_parse.py --strict   # 复算指标（需 OCR 依赖，建议在容器里跑，见 D3 自测记录 §3）
python tools/validate_quotes.py       # 校验 quote = 原文切片、页码与偏移一致
pytest -q                             # 接口 + 解析链路单测（需 requirements-dev.txt）
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
- **docx 无分页符时页码为估算值**（每页约 1100 字），只承诺"大致位置"；PDF 与带分页符的 docx 页码精确；
- **字段抽取只覆盖 6 个关键字段**，且依赖"标签：值"同行的写法；字段藏在表格单元格里的情况 D3/D9 增强；
- **扫描件走 OCR**：单份 3 页约 13–16 s（200 DPI）；OCR 页面会在 `meta.ocr_pages` 标注并提示人工复核；
- **低质量扫描件**（低分辨率/旋转）允许识别率下降，宁可少抽字段也不编造；
- **docx 内嵌图片不做 OCR**（只接 PDF 空文本页），列为已知限制；
- **扫描件样本与文本层样本同源**（内容一致），不能据此宣称真实业务泛化能力，测试报告会写清；
- 解析链路已完整（含 OCR），但仍无资格核验 / 评分 / 风险扫描 / 报告导出（D4–D7），页面未实现的能力一律标注"待接入"。
