# 招投标评审助手

> 魔擎开发者激励 1 期 · 课题 8（政务民生 / 中级）  
> 基于 **Nexent + FastAPI + MCP** 的招投标文件辅助评审智能体：解析投标文件、抽取 8 类字段、
> 做资格性三态核验、按评分细则逐项算分、扫描 40 条规则，并生成**带页码与原文片段**的风险清单和报告。

> **定位：辅助评审，不替代评标委员会。** 系统不输出“中标/废标”结论，不判断证件真伪、不核验业绩真实性；
> 最终结论以评标委员会为准。

---

## 1. 这是什么

政企采购评审现场常见三个问题：

1. 投标文件长、格式杂，关键信息散落在不同章节；
2. 资格性材料“有没有、是否有效”靠人工翻页；
3. 评分细则和风险条款多，扣分理由难以回溯到原文。

本项目把这三件事做成一条确定性链路：

```text
上传文件 → 解析 + OCR → 8 字段抽取 → 资格性三态 → 分项评分 → 40 条规则扫描 → docx/pdf 报告
```

每个字段、每条得分、每条风险都带 `page + quote`，可以点击跳回原文；不靠模型“凭印象”给分。

---

## 2. 主要能力

### 2.1 解析与字段

- 支持 `.docx` / `.pdf` / `.txt` / `.md`；
- 扫描件走 OCR（RapidOCR），页码与原文偏移可追溯；
- 8 类字段：
  1. 项目名称
  2. 项目编号
  3. 采购人
  4. 投标人
  5. 报价
  6. 工期
  7. 资质清单（结构化条目：名称/颁发机构/编号/有效期/页码/quote）
  8. 业绩清单（结构化条目：项目名称/金额/采购人/时间/页码/quote）

### 2.2 资格性三态

R01–R10 逐项判定：

- `provided`：原文提供了该材料；
- `insufficient`：材料出现，但同句提示过期/失效/不满足；
- `missing`：全文未见，或明确写“未提供/无需提供”。

R07 的“无重大违法记录”按合规声明处理；R10 要求注册建造师/职称/证书等强证据，
不再因为出现“项目负责人”四个字就给分。

### 2.3 评分细则

内置 3 套 profile：

| 细则 | 说明 |
| --- | --- |
| `profile-a-calibrated` | **默认**。T2/B2/B3 要求实质内容，而不是章节标题/套话 |
| `profile-a` | 旧基线，保留用于前后对比 |
| `profile-b` | 技术优先型，用于演示“换细则分数变化” |

校准版的关键收紧：

- T2 要求里程碑/横道图/关键路径/节点/进度安排/工期安排/进度控制；其中
  节点/进度安排/工期安排必须与“数字+时间单位”同现；
- B2 要求项目管理机构/人员配置表/人员表/项目团队表/职称证书/注册建造师/建造师证书/项目经理证书；
- B3 要求小时内响应/小时响应/小时到场/SLA/服务级别/响应时限/解决时限；其中
  响应时限/解决时限必须与“小时/天/分钟”同现。

### 2.4 规则库

40 条规则，四类各 10 条：

- 资质门槛 R01–R10
- 废标条款 R11–R20
- 围标串标 R21–R30
- 报价异常 R31–R40

覆盖口径：

```text
40 = 27 自动 + 10 人工 + 3 未实现
```

- 自动 = 18 条关键词 + 9 条计算型（R12/R13/R17/R31/R34/R36/R37/R38/R39）；
- 人工 = 10 条；
- 未实现 = R25/R32/R33（需多家投标人比价，单份不可判定）；
- 规则依据三态：**30 verified / 6 pending / 4 na**；pending 运行期只输出“未检索到权威依据”，
  不编造条号。

### 2.5 项目类型门控

评审入口可选：

- `engineering`：工程类，招标投标法体系；
- `goods_services`：货物/服务类，政府采购法体系；
- `unknown`：未指定，门控规则不硬判。

### 2.6 报告

- 九章结构：封面与文档信息、评审依据、项目/投标人、资格性、分项评分、风险、合同摘要、结论、免责声明；
- 支持 docx / pdf；
- 每条风险、每个字段、每个扣分项都带页码与原文片段；
- 报告页脚固定免责声明。

---

## 3. 架构

```text
┌─────────────────────────────┐
│  浏览器（web/）              │
│  上传 / 评审 / 双栏对照 / 报告 │
└──────────────┬──────────────┘
               │ HTTP
┌──────────────▼──────────────┐
│  FastAPI（api/）             │
│  ├─ parsers：docx/pdf/txt/OCR │
│  ├─ extract：8 字段           │
│  ├─ review：资格性 / 评分     │
│  ├─ rules/checks：40 条规则   │
│  └─ report：docx/pdf          │
└──────────────┬──────────────┘
               │ MCP SSE（8765）
┌──────────────▼──────────────┐
│  Nexent Agent（agent.json）   │
│  ├─ 4 个 Skill               │
│  ├─ 8 个 MCP 工具            │
│  └─ 40 条规则知识库           │
└─────────────────────────────┘
```

- app 端口：`18080`
- MCP 端口：`8765`
- 数据目录：`data/`（运行时数据被 `.gitignore` 排除）

---

## 4. 快速开始

### 4.1 Docker（推荐）

```bash
git clone <this-repo>
cd 招投标评审助手

cp .env.example .env
# 按需修改 .env

docker compose up -d --build
```

打开：

- 评审页面：<http://127.0.0.1:18080>
- API 文档：<http://127.0.0.1:18080/docs>
- 健康检查：<http://127.0.0.1:18080/api/health>

停止：

```bash
docker compose down
```

### 4.2 本地开发

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements-dev.txt
uvicorn api.main:app --host 0.0.0.0 --port 18080
```

### 4.3 最小验证

```bash
python tools/validate_rules.py
python tools/eval_qualification.py --strict --require-full
python tools/eval_parse.py --strict
python tools/eval_risks.py --strict
python tools/eval_rule_coverage.py --strict
python tools/validate_quotes.py
python -m pytest -q
```

---

## 5. 评测结果

### 5.1 基础能力

| 项 | 结果 |
| --- | --- |
| 解析 | 25/25 = 100% |
| 6 字段基线 | 146/146 = 100% |
| 8 字段扩展样本 | 14/14 |
| 资格性人工标注 | 25 份 / 250 项 = **100%** |
| 风险 | TP 15 / FN 0 / FP 0 |
| 规则覆盖 | 40 = 27 自动 + 10 人工 + 3 未实现 |
| 报告一致性 | 14/14 |
| 本地 / 容器 pytest | 本地 66 passed, 1 skipped；容器 67 passed |

### 5.2 评分校准

旧 `profile-a` 在 10 份专家样本上存在系统性高估：

- 旧版：**0/10** 在 ±5 内；
- 校准版：**10/10** 与“老师逐项分反推总分”一致；
- 这是 **in-sample 规则对齐**，不是独立验证，不能外推。

### 5.3 新样本 out-of-sample（N01–N10，盲评定稿）

10 份新样本一次盲评，B3 按“具体时限/SLA/质保期”严格口径：

| 指标 | 旧版 `profile-a` | 校准版 `profile-a-calibrated` |
| --- | ---: | ---: |
| ±5 内 | **4/10（40%）** | **10/10（100%）** |
| 平均绝对偏差 | **11.60 分** | **0.00 分** |
| 最大差 | 22 | 0 |

- `eval_scoring --strict`：10 条、10/10、平均偏差 0.00，**脚本通过**；
- 唯一不足：n=10 仍属小样本，95% 置信区间约 72%–100%，不能外推；
- S08 是 S01 的扫描件（SHA256 前 16 位 `e0a011b326a3eb03`），旧 10 份中独立样本 9 份；
  扫描件的 T2/B2/B3 依赖 OCR，需人工复核。
- 样本硬伤处理：N02–N08 报价明细已按投标函重算（只改示意金额，评分不变）；
  N01–N08 的 T1/T3/T4 同质化保留为局限，N09/N10 已加入“有/无”对照。

---

## 6. 目录结构

```text
.
├── api/                    # FastAPI 后端
│   ├── parsers/            # docx / pdf / txt / OCR
│   ├── extract/            # 8 字段抽取
│   ├── review/             # 资格性 + 评审编排
│   ├── report/             # docx / pdf 报告
│   ├── rules.py            # 规则加载 + 扫描
│   └── checks.py           # 计算型规则
├── data/
│   ├── rules/rules.yaml    # 40 条规则
│   ├── scoring/            # profile-a / profile-a-calibrated / profile-b
│   └── samples/            # 25 份基线 + 扩展/新样本
├── knowledge/              # 规则知识库（rules-full.md + manifest）
├── mcps/                   # MCP 服务（8 个工具）
├── skills/                 # 4 个 Nexent Skill
├── web/                    # 前端页面
├── tools/                  # 评测/校验脚本
├── tests/                  # pytest
├── docs/                   # 开发/数据/评审/使用四份文档、截图、样例报告
├── agent.json              # Nexent 智能体定义
├── prompt.md               # 系统提示词
├── docker-compose.yml
├── DEPLOY.md
└── LICENSE
```

---

## 7. AgentsHub 智能体

AgentsHub 目录（只放智能体包，不含完整后端）：

```text
行业智能体/政务/招投标评审助手/
├── agent.json
├── README.md
├── DEPLOY.md
├── knowledge/
│   ├── rules-full.md
│   └── manifest.json
├── skills/
├── mcps/
└── screenshots/
```

PR：

- <https://gitcode.com/ModelEngine/AgentsHub/merge_requests/170>

注意：

- `mcps/bid_review_mcp.py` 依赖完整后端；需先按 `DEPLOY.md` 启动 app + MCP；
- `agent.json` 的知识库索引 `4-5897...` 需按目标环境替换为实际索引 ID；
- 导入顺序：先导入 Skill/MCP/知识库，再导入 `agent.json`。

---

## 8. 数据与合规

- 所有样本均为自造虚构数据，不含真实企业、真实公民或真实项目信息；
- 学生评审是“非专家预评审”，AI 参考不是专家；报告不把二者写成专家分；
- 法规引用只使用 `verified` 条号；`pending` 不编造；
- 输出是辅助建议，不构成中标/废标结论；
- 代码以 MIT License 发布。

---

## 9. 已知限制

- T2/B2/B3 的校准版依赖“实质内容词 + 数字/时限”，真实标书的复杂表格仍需人工复核；
- R25/R32/R33 需多家投标人比价，单份不可判定；
- OCR 质量会影响扫描件的字段与评分，扫描件结论需人工核对；
- 专家样本 10 份，n=10 仍属小样本，不能外推；
- 容器全量 pytest 已通过：67 passed；本地 66 passed / 1 skipped；
- 演示视频尚未录制。

---

## 10. 许可

MIT License。提交到 AgentsHub 即表示同意以仓库现有 MIT License 发布。

---

## 11. 相关文档

- [开发说明](docs/开发说明.md)
- [数据说明](docs/数据说明.md)
- [评审说明](docs/评审说明.md)
- [使用说明](docs/使用说明.md)
- [四份文档 PDF 合集](docs/pdf/20261117/招投标评审助手-文档合集.pdf)
- [演示视频脚本](docs/演示视频脚本.md)
- [演示视频 PPT](docs/演示视频-招投标评审助手-新版.pptx)
- [部署说明](DEPLOY.md)
- [评测数据索引](docs/评审功能测评数据/README.md)
