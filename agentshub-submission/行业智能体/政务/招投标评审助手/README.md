# 招投标评审助手

> 课题 8：招投标评审助手（政务民生 / 中级）
> 基于 Nexent 的招投标文件辅助评审智能体：解析投标文件 → 抽取 8 类字段 → 资格性三态核验 →
> 按评分细则逐项算分 → 40 条规则扫描 → 生成带页码与原文片段的风险清单/报告。

## 1. 目录结构

```text
招投标评审助手/
├── agent.json          # Nexent 平台导出的智能体定义（prompt / skills / MCP / 知识库）
├── README.md           # 本文件
├── DEPLOY.md           # 完整后端/容器启动说明（本目录只是智能体包）
├── knowledge/          # 规则库资产（rules-full.md + manifest.json）
├── skills/             # 4 个自定义 Skill
│   ├── bid-rule-cards/SKILL.md
│   ├── missing-qualification/SKILL.md
│   ├── bid-risk-selfcheck/SKILL.md
│   └── summary-compiler/SKILL.md
├── mcps/               # 自定义 MCP 服务（8 个工具）
│   ├── bid_review_mcp.py
│   └── README.md
└── screenshots/        # 评审看板、报告预览
```

## 2. 导入步骤

### 2.1 导入智能体

1. 登录 Nexent 平台；
2. 进入「智能体开发」→「导入」；
3. 上传本目录的 `agent.json`；
4. 平台解析后选择本环境可用的模型（`agent.json` 不写死模型名）；
5. 保存/发布。

### 2.2 导入 Skill

在「智能体开发」→「选择技能」→「构建技能」中，依次上传：

- `skills/bid-rule-cards/SKILL.md`
- `skills/missing-qualification/SKILL.md`
- `skills/bid-risk-selfcheck/SKILL.md`
- `skills/summary-compiler/SKILL.md`

导入技能后，回到智能体确认 `skill_names` 四项均已绑定。

### 2.3 配置 MCP（必须先启动完整后端）

**本目录不是完整后端。** `mcps/bid_review_mcp.py` 依赖 `api/`、`data/`、`knowledge/`，
只启动这个 py 文件会缺依赖。必须先在完整源码工程根目录按 [`DEPLOY.md`](DEPLOY.md) 启动
app + MCP（`docker compose up -d --build`），再把 `agent.json` 的 `mcp_url` 换成实际地址。

`agent.json` 中 MCP 配置为：

```json
{
  "mcp_server_name": "bid-review",
  "mcp_url": "http://host.docker.internal:8765/sse"
}
```

`mcps/bid_review_mcp.py` 是 FastMCP 单文件服务，默认端口 8765，提供：

`parse_tender`、`check_qualification`、`score_item`、`scan_risks`、`locate_span`、
`export_report`、`list_documents`、`parse_attachment`。

在「选择工具」→「MCP 配置」中新建 SSE 服务，URL 按你的部署地址填写；如果 Nexent 与 MCP
不在同一台机器，把 `host.docker.internal` 换成 MCP 服务的实际主机名/IP。

### 2.4 知识库

`agent.json` 引用索引 `4-5897239e69964605914680814969edbc`（40 条规则的知识库）。
目标环境没有该索引时：

1. 先上传本目录 `knowledge/rules-full.md`（40 块规则），按平台要求切分/建索引；
2. 在 `agent.json` 的 `KnowledgeBaseSearchTool.params.index_names` 中替换为新索引 ID；
3. 同步导入 `knowledge/manifest.json` 只用于核对规则指纹，不是索引本身。

`basis_status=pending` 的规则，运行期只输出「未检索到权威依据」，不补条号。

## 3. 能力与口径

- **8 类字段**：项目名称、项目编号、采购人、投标人、报价、工期、资质清单、业绩清单；
  清单字段是结构化条目（名称/页码/原文 quote，资质另含颁发机构/编号/有效期，
  业绩另含金额/采购人/时间）。
- **资格性三态**：`provided / insufficient / missing`；R07 的“无重大违法记录”是合规声明，
  R10 需要注册建造师/职称/证书等强证据，不能只凭“项目负责人”四个字。
- **规则库**：40 条 = **27 自动 + 10 人工 + 3 未实现**；未实现的 R25/R32/R33 需多家投标人
  比价，单份文档不可判定，报告中会如实写“未参与判定”。
- **项目类型门控**：工程类走招标投标法体系；货物/服务类走政府采购体系；未指定时门控规则
  不硬判。入口参数 `project_type = engineering / goods_services / unknown`。
- **报告**：九章、docx/pdf、页码 + quote + 依据三态；不输出中标/废标结论。

## 4. 自测结果（本机，2026-11-16）

| 项 | 结果 |
| --- | --- |
| 解析 | 25/25 = 100%；字段 146/146（6 字段基线） |
| 8 字段扩展样本 | 14/14 |
| 资格性人工标注 | 25 份 / 250 项 = **100%** |
| 风险 | TP 15 / FN 0 / FP 0 |
| 规则覆盖 | 40 = 27 + 10 + 3 |
| 报告一致性 | 14/14 |
| 本地 pytest | 66 passed, 1 skipped（MCP 用例因本机缺 `mcp` 依赖跳过） |
| 新样本 out-of-sample | N01–N10 一次盲评：旧版 4/10、校准版 **10/10** 在 ±5 内 |
| 专家评分 | 10 条盲评标注，平均偏差 0.00；n=10 小样本 |

> 容器全量 pytest 尚未在当前环境复跑（Docker 不可用）；提交前建议在干净环境补跑。
> 样本均为自造虚构数据；学生/AI 分不能替代专家分。

## 5. 已知限制

1. 默认 `profile-a-calibrated` 要求 T2/B2/B3 的实质内容；旧 `profile-a` 仍保留作对照。
2. R25/R32/R33 需多家投标人比价，单份不可判定；不假装 40 条全部自动。
3. 不判断证件真伪、不核验业绩真实性；OCR 页需人工核对原件。
4. 输出是辅助建议，最终以评标委员会结论为准。

## 6. 数据与合规

- 全部演示数据为自造虚构，不含真实企业/个人敏感信息；
- 政务场景输出不构成审批/废标结论；
- 法规引用只使用 `basis_status=verified` 的条号；pending 不编造；
- 本项目以 MIT License 发布。

## 7. 许可

MIT License，提交即同意以仓库现有 MIT License 发布。
