[new agent] 招投标评审助手（课题 8）

## 课题 8 · 招投标评审助手（政企采购 / 中级档）

> 提交目录：`行业智能体/政务/招投标评审助手/`　|　作者：AtomGit `@gcw_N79tXvDq`　|　版本：v0.9.0
> 本目录是**完整工程**（前端 / 后端 / 模拟数据 / 评测集 / 部署 / 文档 / Docker），clone 后按 `DEPLOY.md` 可直接复现，不依赖外部仓库。

面向政企采购的招投标文件辅助评审智能体：上传 **docx / pdf / txt / md（含扫描件 OCR）**，
解析 8 类字段、做资格性三态核验、按 9 项细则逐项算分、扫描 40 条规则，输出**带页码与原文片段**的
风险清单和 docx/pdf 报告；所有结论可点击回原文。

> **辅助评审，不替代评标委员会。** 不输出中标/废标结论，不判断证件真伪、不核验业绩真实性；最终以评标委员会结论为准。

界面截图：`docs/screenshots/`（评审看板、总分卡、三表、双栏定位、报告中心，共 5 张）。

---

## 一、交付物清单

| 交付物 | 路径 | 状态 / 要点 |
| --- | --- | --- |
| 前端工程 | `web/` | 评审看板、双栏对照、报告中心、系统状态、数据管理；原生 JS，无构建、无占位按钮 |
| 后端智能体工程 | `api/`、`agent.json`、`prompt.md`、`skills/`、`mcps/` | FastAPI + Nexent 导出配置 + 4 个 Skill（含 zip）+ 8 个 MCP 工具 |
| 知识库资产 | `knowledge/rules-full.md`、`knowledge/rules/`、`manifest.json` | 40 条规则全文，指纹 `a30eba3bfa5b33c0`，含判定条件与依据三态 |
| 模拟数据 | `data/samples/` | 25 份基线（20 文本层 + 5 扫描件）+ 3 份边界 + 15 份植入风险 + 5 份干净对照 + N01–N10 |
| 评测集 | `docs/评审功能测评数据/` | 250 条资格性标注、评分表/意见、原始记录、复算脚本 |
| 部署文档 | `DEPLOY.md`、`Dockerfile`、`docker-compose.yml`、`.env.example` | app 默认 8080（`HOST_PORT` 可覆盖）、MCP 8765；OCR 依赖已写入镜像 |
| 使用文档 | `docs/使用说明.md`、`docs/screenshots/` | 功能地图、5 分钟上手、8 项功能、三张结果表、双栏、报告、FAQ；5 张截图 |
| 测试报告 | `docs/测试报告.md` | 六条课题验收 + 七条通用验收逐项、样本量、TP/FN/FP、复算命令 |
| 设计说明 | `docs/开发说明.md` | 架构分层、模块职责、请求链路、部署拓扑、M0–M6 开发阶段 |
| 许可 / 变更 | `LICENSE`（MIT）、`CHANGELOG.md` | — |
| 演示视频 | `docs/video/` | **待补**（当前为空；脚本 7 分 50 秒与 20 页 deck 已就绪） |

> 结论：8 项必需交付物中 7 项完成，**演示视频仍缺**；不做“已完成视频”的虚假声明。

---

## 二、验收对照

| 验收项 | 要求 / 口径 | 实测 | 判定 |
| --- | --- | --- | :--: |
| 解析成功率 | 25 份样本（含 5 扫描件） | **25/25 = 100%** | 达标 |
| 6 字段基线 | 146 个字段 | **146/146 = 100%** | 达标 |
| 8 字段扩展 | 14 个扩展样本 | **14/14** | 达标 |
| 资格性核验 | 25 份 × R01–R10 | **250/250 = 100%** | 达标 |
| 风险检出 | 15 份植入 + 5 份干净对照 | **TP 15 / FN 0 / FP 0** | 达标 |
| 规则覆盖 | 40 条 | **40 = 27 自动 + 10 人工 + 3 未实现** | 如实披露 |
| 规则依据 | 三态 | **30 verified / 6 pending / 4 na** | 如实披露 |
| 评分一致 | N01–N10，±5 分 | **10/10 = 100%，平均偏差 0.00** | 达成（见说明） |
| 旧口径对照 | 同一批 N01–N10 | 旧 `profile-a` 4/10，平均偏差 11.60 | 对照 |
| 报告一致性 | 14 份 baseline | **14/14** | 达标 |
| 3 次一致性 | 同一输入重复 3 次 | 字段 / 资格性 / 评分 / 风险 **3/3 完全一致** | 达标 |
| 单测 | 本地 / 容器 | 本地 **66 passed / 1 skipped**；容器 **67 passed** | 达标 |
| 部署 | Docker Compose | app + mcp 可启动；本机 18080 / 8765，默认 8080 / 8765 | 基本达标 |

说明：

- 评分的“专家”为**单评审人盲评**（n=10），不是多专家一致性结论；校准在同一批 N01–N10 上完成，**10/10 属拟合内结果**，不能当作泛化准确率；
- N01–N08 的 T1/T3/T4 文本相同，样本对这三项区分力有限；N09/N10 已加入“有/无”对照；
- n=10 的 95% 置信区间约 72%–100%，不能外推；
- 容器 67 passed 为 2026-11-17 记录值；本机 Docker 管道当前不可用，未在本次复跑。

---

## 三、五分钟验收路径

```bash
git clone https://gitcode.com/ModelEngine/AgentsHub.git
cd AgentsHub/行业智能体/政务/招投标评审助手

python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

python tools/validate_rules.py
python tools/eval_qualification.py --strict --require-full
python tools/eval_parse.py --strict
python tools/eval_risks.py --strict
python tools/eval_rule_coverage.py --strict
python tools/eval_calibrated.py --strict
python tools/eval_scoring.py --strict
python tools/validate_quotes.py
python tools/check_repeatable.py
python -m pytest -q
```

期望：

```text
规则：40 = 27 自动 + 10 人工 + 3 未实现（30 verified / 6 pending / 4 na）
资格性：250/250 = 100%
解析：25/25 = 100%；字段 146/146 = 100%
风险：TP 15 / FN 0 / FP 0
评分：旧 4/10、校准 10/10，平均偏差 0.00
一致性：字段 / 资格性 / 评分 / 风险 3/3 完全一致
pytest：本地 66 passed / 1 skipped；容器 67 passed
```

Docker：

```bash
cp .env.example .env
docker compose up -d --build
# 浏览器打开 http://127.0.0.1:8080（若 .env 里 HOST_PORT=18080 则用 18080）
```

---

## 四、平台能力落地

| 能力 | 落地方式 | 证据 |
| --- | --- | --- |
| 智能体编排 | 单主智能体，`max_steps=15`；`verification_config` 开启步骤级 + 终局校验，`pass_score=0.75`，失败 `repair_then_controlled_summary` | `agent.json` |
| 工具调用 | MCP `bid-review` 8 个工具；知识库 `KnowledgeBaseSearchTool`，`top_k=3`、`search_mode=hybrid` | `agent.json`、`mcps/` |
| 知识库挂载 | 40 条规则、`knowledge/rules-full.md`（40 分片）；导入后替换 `index_names` | `knowledge/`、`agent.json` |
| 自定义 Skill | `bid-rule-cards` / `missing-qualification` / `bid-risk-selfcheck` / `summary-compiler`（4 个 zip 已随包提交） | `skills/*.zip` |
| 确定性兜底 | 解析、字段、资格性、评分、风险、报告全部由代码计算；模型只负责组织语言 | `api/` |
| MCP | 8 工具：`parse_tender` / `check_qualification` / `score_item` / `scan_risks` / `locate_span` / `export_report` / `list_documents` / `parse_attachment` | `mcps/bid_review_mcp.py` |

---

## 五、`agent.json` 关键配置

| 项 | 值 | 说明 |
| --- | --- | --- |
| `display_name` | 招投标评审助手 | |
| `max_steps` | 15 | 解析 → 资格性 → 评分 → 风险 |
| `model_names` | `[]` | 导入后由目标环境选择，不写死模型名 |
| `model_params_override` | `temperature=0` | 降低波动 |
| `skill_names` | 4 个 | 见上表 |
| `tools` | `KnowledgeBaseSearchTool` × 1 | `top_k=3`、hybrid |
| `mcp_info` | `bid-review` × 8 工具 | SSE 8765 |
| `verification_config` | 步骤 + 终局校验 | `pass_score=0.75` |

> `agent.json` 的知识库索引 `4-5897...` 是导出方租户的索引名；导入目标环境后必须替换为实际索引 ID。

---

## 六、导入 Nexent 的步骤

1. 技能仓库 → 我的 Skill → 创建 → 依次上传 `skills/` 下 4 个 zip；
2. 智能体开发 → 导入 → 上传 `agent.json`；
3. 新建知识库，上传 `knowledge/rules-full.md`（或 `knowledge/rules/R01.md … R40.md`），按 `## Rxx` 切分；
4. **必改**：`agent.json` → `tools[0].params.index_names` 替换为本环境索引 ID；
5. 启动完整后端与 MCP：按 `DEPLOY.md` 执行 `docker compose up -d --build`（app / MCP）；
6. 在 MCP 配置中填实际 `mcp_url`（同栈默认 `http://mcp:8765/sse`，跨机用宿主地址）；
7. 选择目标环境模型，保存/发布。

> `mcps/bid_review_mcp.py` 不是独立服务，依赖完整后端的 `api/`、`data/`、`knowledge/`；只启动这个 py 文件会缺依赖。

---

## 七、自测结果与证据

- 解析 25/25、字段 146/146、8 字段扩展 14/14；
- 资格性 250/250；风险 TP 15 / FN 0 / FP 0；
- 规则 40 = 27 自动 + 10 人工 + 3 未实现；依据 30 verified / 6 pending / 4 na；
- 评分 N01–N10：旧 4/10、校准 10/10，平均偏差 0.00（单评审人，拟合内）；
- 报告 14/14；
- 3 次一致性：`python tools/check_repeatable.py` 四类结果 3/3 完全一致；
- pytest：本地 66 passed / 1 skipped（39.3s）；容器 67 passed；
- 时延（确定性 API）：文本解析 p95 87ms、评审 p95 27ms、docx 报告 p50 349ms、pdf 105ms；OCR 热启 p50 18.8s、冷启 45.6s；页面 `app_ready` 约 1.0s。

原始记录与复算脚本：`docs/评审功能测评数据/`；完整报告：`docs/测试报告.md`。

---

## 八、数据与合规

- 25 份基线 + 15 份植入风险 + 5 份干净对照 + N01–N10，全部为**自造虚构数据**；
- 企业名、项目名、金额、工期均为示例，不含真实企业/个人敏感信息；本项目不采集姓名、证件号、联系方式等个人字段；
- 依据三态：verified 30 / pending 6 / na 4；pending 只写“未检索到权威依据”，不编造条号；
- 前端顶部常驻免责声明；输出不构成中标/废标结论；
- 第三方依赖与许可证：`rapidocr-onnxruntime==1.2.3`（Apache-2.0）、`pypdfium2`（Apache-2.0/BSD-3-Clause）等，详见 `requirements.txt`；
- MIT License。

---

## 九、已知限制

- **演示视频待补**：`docs/video/` 目前为空；这是当前唯一未完成的必需交付物；
- 评分为单评审人盲评、校准与验证同一批样本，属拟合内结果；n=10 不能外推；
- N01–N08 的 T1/T3/T4 文本相同，样本对这三项区分力有限；
- R25/R32/R33 需多家投标人比价，单份不可判定；
- 4 条经验型规则（R30/R31/R33/R40）无直接法规条号，依据标为 `na`；
- OCR 质量影响扫描件字段与评分，扫描件需人工复核；
- LLM 对话链路的首字/端到端未单独计时，上文时延为确定性 API 与页面渲染实测值。

---

## 十、目录结构

```text
行业智能体/政务/招投标评审助手/
├── api/                    # FastAPI：解析 / 字段 / 资格性 / 评分 / 风险 / 报告
├── web/                    # 前端（原生 JS，无构建）
├── data/                   # 规则 YAML、3 套评分细则、25+ 份样本
├── knowledge/              # 规则知识库（rules-full.md + 40 分片 + manifest）
├── mcps/                   # MCP 服务（8 工具）
├── skills/                 # 4 个 Skill（SKILL.md + zip）
├── tests/                  # pytest（66 passed / 1 skipped）
├── tools/                  # 评测 / 校验 / 复算 / 同步脚本
├── docs/                   # 开发 / 数据 / 评审 / 测试 / 使用说明、截图、评测数据
├── agent.json              # Nexent 智能体定义
├── prompt.md               # 系统提示词（agent.json 的唯一来源）
├── DEPLOY.md  Dockerfile  docker-compose.yml  .env.example
├── LICENSE（MIT）  CHANGELOG.md  VERSION
└── .github/workflows/ci.yml
```

---

## 十一、提交记录

- 本次提交：补齐完整工程（`web/`、`api/`、`data/`、`tools/`、`tests/`、`docs/`、Docker 文件）、独立《测试报告》、重写 `DEPLOY.md`、补 4 个 Skill zip 与 5 张截图；
- 此前提交：`c4a6a87` 更新截图与 prompt；`a0a698b` 同步 N01–N10 复评；`7dbf59e` 补 DEPLOY / 知识库前置说明。
