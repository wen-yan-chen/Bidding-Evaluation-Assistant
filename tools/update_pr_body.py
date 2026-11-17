import subprocess
import requests

BODY = """[new agent] 招投标评审助手（课题 8）

## 课题 8 · 招投标评审助手（政务民生 / 中级档）

> 提交目录：`行业智能体/政务/招投标评审助手/`　|　作者：AtomGit `@gcw_N79tXvDq`　|　版本：v0.9.0（阶段 2）
>
> 源码 / 过程仓库：https://github.com/wen-yan-chen/Bidding-Evaluation-Assistant

面向政企采购的招投标文件辅助评审智能体：上传投标文件（**docx / pdf / txt / md，含扫描件 OCR**），
解析 8 类字段、做资格性三态核验、按 9 项细则逐项算分、扫描 40 条规则，输出**带页码与原文片段**的
风险清单和 docx/pdf 报告；所有结论可点击回原文。

> **辅助评审，不替代评标委员会。** 不输出中标/废标结论，不判断证件真伪、不核验业绩真实性；最终以评标委员会结论为准。

![评审看板](https://raw.githubusercontent.com/wen-yan-chen/Bidding-Evaluation-Assistant/main/docs/screenshots/20261117-01-%E8%AF%84%E5%AE%A1%E7%9C%8B%E6%9D%BF.png)

---

## 一、交付物清单

| 交付物 | 路径 | 状态 / 要点 |
| --- | --- | --- |
| 前端工程 | `web/` | 评审看板、双栏对照、报告中心、系统状态、数据管理；原生 JS，无构建、无占位按钮 |
| 后端 / 智能体工程 | `api/`、`agent.json`、`prompt.md`、`skills/`、`mcps/` | FastAPI + Nexent 导出配置 + 4 个 Skill + 8 个 MCP 工具 |
| 知识库资产 | `knowledge/rules-full.md`、`manifest.json` | 40 条规则全文，含判定条件、依据三态；导入后替换 `index_names` |
| 模拟数据 | `data/samples/` | 25 份基线（20 文本层 + 5 扫描件）+ N01–N10 十份评测样本 + 15 份植入风险 + 5 份干净对照 |
| 部署文档 | `DEPLOY.md`、`Dockerfile`、`docker-compose.yml`、`.env.example` | app 18080 / MCP 8765；OCR 依赖已写入镜像 |
| 使用文档 | `docs/使用说明.md`、`docs/screenshots/` | 功能地图、5 分钟上手、8 项功能、三张结果表、双栏、报告、FAQ；当前界面截图 |
| 测试 / 评测 | `docs/评审说明.md`、`docs/数据说明.md`、`docs/评审功能测评数据/` | N01–N10 盲评 10/10、250 条资格性标注、15/15 风险、66/67 pytest、数据与复算脚本 |
| 设计说明 | `docs/开发说明.md` | 架构分层、模块职责、请求链路、部署拓扑、M0–M6 开发阶段 |
| 演示视频 | `docs/video/` | **待补**（当前为空） |
| 许可 / 变更 | `LICENSE`（MIT）、`CHANGELOG.md` | — |

> 结论：8 项交付物中 7 项完成，**演示视频仍缺**；不做“已完成视频”的虚假声明。

---

## 二、验收对照

| 验收项 | 要求 / 口径 | 实测 | 判定 |
| --- | --- | --- | :--: |
| 解析成功率 | 25 份样本 | **25/25 = 100%** | 达标 |
| 6 字段基线 | 146 个字段 | **146/146 = 100%** | 达标 |
| 8 字段扩展 | 14 个扩展样本 | **14/14** | 达标 |
| 资格性核验 | 25 份 × R01–R10 | **250/250 = 100%** | 达标 |
| 风险检出 | 15 份植入 + 5 份干净对照 | **TP 15 / FN 0 / FP 0** | 达标 |
| 规则覆盖 | 40 条 | **40 = 27 自动 + 10 人工 + 3 未实现** | 如实披露 |
| 规则依据 | 三态 | **30 verified / 6 pending / 4 na** | 达标 |
| 评分与专家一致 | N01–N10，±5 分 | **10/10 = 100%，平均偏差 0.00** | 达标 |
| 旧口径对照 | 同一批 N01–N10 | 旧 `profile-a` 4/10，平均偏差 11.60 | 对照 |
| 报告一致性 | 14 份 baseline | **14/14** | 达标 |
| 单测 | 本地 / 容器 | 本地 **66 passed / 1 skipped**；容器 **67 passed** | 达标 |
| 部署 | Docker Compose | app + mcp 可启动；当前环境实测 18080 / 8765 | 基本达标 |

说明：

- 评分对照采用 **N01–N10 一次盲评**；校准版 `profile-a-calibrated` 与参考分逐份一致；
- N01–N08 的 T1/T3/T4 文本相同，样本对这三项区分力有限；N09/N10 已加入“有/无”对照；
- n=10 仍属小样本，95% 置信区间约 72%–100%，不能外推。

---

## 三、五分钟验收路径

```bash
git clone https://github.com/wen-yan-chen/Bidding-Evaluation-Assistant.git
cd Bidding-Evaluation-Assistant

pip install -r requirements-dev.txt
python tools/validate_rules.py
python tools/eval_qualification.py --strict --require-full
python tools/eval_parse.py --strict
python tools/eval_risks.py --strict
python tools/eval_rule_coverage.py --strict
python tools/eval_calibrated.py --strict
python tools/eval_scoring.py --strict
python -m pytest -q
```

期望：

```text
规则：40 = 27 + 10 + 3
资格性：250/250 = 100%
评分：旧 4/10、校准 10/10，平均偏差 0.00
pytest：本地 66 passed / 1 skipped；容器 67 passed
```

Docker：

```bash
cp .env.example .env
docker compose up -d --build
# 浏览器打开 http://127.0.0.1:18080
```

容器内复跑：

```bash
docker compose run --rm --no-deps -v "$PWD:/app" app \
  sh -c "python -m pip install -q pytest httpx && python -m pytest -q"
```

---

## 四、平台能力落地

| 能力 | 落地方式 | 证据 |
| --- | --- | --- |
| 智能体编排 | 单主智能体，`max_steps=15`；`verification_config` 开启步骤级 + 终局校验，`pass_score=0.75`，失败 `repair_then_controlled_summary` | `agent.json` |
| 工具调用 | MCP `bid-review` 8 个工具；知识库 `KnowledgeBaseSearchTool`，`top_k=3`、`search_mode=hybrid` | `agent.json` → `mcp_info` / `tools` |
| 知识库挂载 | 40 条规则、`knowledge/rules-full.md`；导入后替换 `index_names` | `knowledge/`、`agent.json` |
| 自定义 Skill | `bid-rule-cards` / `missing-qualification` / `bid-risk-selfcheck` / `summary-compiler` | `skills/*/SKILL.md` |
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

1. 技能仓库 → 我的 Skill → 创建 → 依次上传 `skills/` 下 4 个 `SKILL.md`；
2. 智能体开发 → 导入 → 上传 `agent.json`；
3. 新建知识库，上传 `knowledge/rules-full.md`，按规则分节切分；
4. **必改**：`agent.json` → `tools[0].params.index_names` 替换为本环境索引 ID；
5. 启动完整后端与 MCP：按 `DEPLOY.md` 执行 `docker compose up -d --build`（app 18080 / MCP 8765）；
6. 在 MCP 配置中填实际 `mcp_url`（默认 `http://host.docker.internal:8765/sse`）；
7. 选择目标环境模型，保存/发布。

> `mcps/bid_review_mcp.py` 不是独立服务，依赖完整后端的 `api/`、`data/`、`knowledge/`；只启动这个 py 文件会缺依赖。

---

## 七、自测结果与证据

### 7.1 基础能力

- 25 份解析样本：**25/25 = 100%**；
- 6 字段基线：**146/146 = 100%**；
- 8 字段扩展：**14/14**；
- 资格性人工标注：**25 份 / 250 项 = 100%**；
- 风险：**TP 15 / FN 0 / FP 0**；
- 规则：**40 = 27 自动 + 10 人工 + 3 未实现**；依据 **30 verified / 6 pending / 4 na**；
- 报告：14 份 baseline **14/14**。

### 7.2 评分校准（N01–N10）

| 指标 | 旧 `profile-a` | 校准 `profile-a-calibrated` |
| --- | ---: | ---: |
| ±5 内 | **4/10** | **10/10** |
| 平均绝对偏差 | **11.60** | **0.00** |
| 最大偏差 | 22 | **0** |

- 评分表 / 意见：`docs/评审功能测评数据/01-评分结果/评分表_N01-N10.xlsx`、`评分意见_N01-N10.docx`；
- 回归：`python tools/eval_calibrated.py --strict`。

### 7.3 测试

```text
本地：66 passed, 1 skipped
容器：67 passed
```

容器命令：

```bash
docker compose run --rm --no-deps -v "$PWD:/app" app \
  sh -c "python -m pip install -q pytest httpx && python -m pytest -q"
```

---

## 八、数据与合规

- 25 份基线 + 15 份植入风险 + 5 份干净对照 + N01–N10，全部为**自造虚构数据**；
- 企业名、项目名、金额、工期均为示例，不含真实企业/个人敏感信息；
- 依据三态：verified 30 / pending 6 / na 4；pending 只写“未检索到权威依据”，不编造条号；
- 前端顶部常驻免责声明；输出不构成中标/废标结论；
- MIT License。

---

## 九、已知限制

- **演示视频待补**：`docs/video/` 目前为空；这是当前唯一未完成的必需交付物；
- N01–N08 的 T1/T3/T4 文本相同、恒为 24 分，样本对这三项区分力有限；N09/N10 已加入“有/无”对照；
- n=10 仍属小样本，95% 置信区间约 72%–100%，不能外推；
- R25/R32/R33 需多家投标人比价，单份不可判定；
- OCR 质量影响扫描件字段与评分，扫描件需人工复核；
- 规则依据 6 条 pending，运行期只输出“未检索到权威依据”；
- 容器 pytest 已通过，但 GitCode PR 页面未显示 CI 绿勾；如维护者要求 PR CI，需仓库侧再确认。

---

## 十、截图与文档

- 当前界面截图：`screenshots/01-评审看板.png`、`screenshots/02-报告预览.png`；
- 文档：`docs/开发说明.md`（架构）、`docs/数据说明.md`、`docs/评审说明.md`、`docs/使用说明.md`；
- 当前 PDF：`docs/pdf/20261117/招投标评审助手-文档合集.pdf`。

**演示视频：未录制；`docs/video/` 为空。**

---

## 十一、提交记录

- `c4a6a87` 更新 PR 包截图、同步当前 agent prompt；
- `d130fa2` 源码仓库补充架构、使用说明、当前截图、容器测试结果；
- `a0a698b` 补充 DEPLOY.md / knowledge/rules-full.md / 知识库替换说明。

源码仓库：https://github.com/wen-yan-chen/Bidding-Evaluation-Assistant
"""


def main() -> None:
    cred = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=gitcode.com\n\n",
        text=True,
        capture_output=True,
        check=True,
    )
    data = dict(line.split("=", 1) for line in cred.stdout.splitlines() if "=" in line)
    token = data["password"]
    resp = requests.patch(
        "https://gitcode.com/api/v5/repos/ModelEngine/AgentsHub/pulls/170",
        headers={"PRIVATE-TOKEN": token, "Content-Type": "application/json"},
        json={"body": BODY},
        timeout=20,
    )
    print(resp.status_code)
    print(resp.json().get("state"))


if __name__ == "__main__":
    main()
