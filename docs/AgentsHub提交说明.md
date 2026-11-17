# AgentsHub 提交说明（课题 8）

> 目标仓库：<https://gitcode.com/ModelEngine/AgentsHub>
> 活动帖：<https://gitcode.com/org/ModelEngine/discussions/26>
> 提交方式：Fork → 按目录放置 → PR 到 `main`；PR 标题 `[new agent] 招投标评审助手`
> **已创建 PR：<https://gitcode.com/ModelEngine/AgentsHub/merge_requests/170>**
> **只提交 `行业智能体/政务/招投标评审助手/` 这个智能体目录，不要把整个源码工程/测评数据/截图全塞进 PR。**

## 一、已准备好的提交目录

本机路径：

```text
D:\contest-8\行业智能体\政务\招投标评审助手\agentshub-submission\行业智能体\政务\招投标评审助手\
```

内容：

```text
招投标评审助手/
├── agent.json
├── README.md
├── skills/
│   ├── bid-rule-cards/SKILL.md
│   ├── missing-qualification/SKILL.md
│   ├── bid-risk-selfcheck/SKILL.md
│   └── summary-compiler/SKILL.md
├── mcps/
│   ├── bid_review_mcp.py
│   └── README.md
└── screenshots/
    ├── 01-评审看板.png
    └── 02-报告预览.png
```

## 二、Fork 与目录放置

1. 打开 <https://gitcode.com/ModelEngine/AgentsHub>，点 **Fork** 到自己的账号；
2. 克隆自己的 fork：

```powershell
cd D:\contest-8
git clone https://gitcode.com/<你的账号>/AgentsHub.git
cd AgentsHub
```

3. 把准备好的目录复制进去：

```powershell
$src = "D:\contest-8\行业智能体\政务\招投标评审助手\agentshub-submission\行业智能体\政务\招投标评审助手"
$dst = "D:\contest-8\AgentsHub\行业智能体\政务\招投标评审助手"
New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
Copy-Item $src $dst -Recurse -Force
```

4. 检查目录：

```powershell
Get-ChildItem "行业智能体\政务\招投标评审助手" -Recurse
```

应看到 `agent.json`、`README.md`、4 个 Skill、MCP 文件和 2 张截图。

## 三、提交分支与 PR

```powershell
cd D:\contest-8\AgentsHub
git switch -c add-bid-review-agent
git add "行业智能体/政务/招投标评审助手"
git status --short
git commit -m "[new agent] 招投标评审助手: topic 8"
git push -u origin add-bid-review-agent
```

然后在 GitCode 页面发起 PR：

- 源分支：`add-bid-review-agent`
- 目标分支：`main`
- 标题：`[new agent] 招投标评审助手`
- 描述：用下面模板

## 四、PR 描述模板

```text
【课题】8 招投标评审助手（政务民生 / 中级）

【智能体目录】
行业智能体/政务/招投标评审助手/

【agent.json 关键配置】
- display_name：招投标评审助手
- 模型：导入后由目标环境选择（agent.json 不写死模型名）
- Skills：bid-rule-cards、missing-qualification、bid-risk-selfcheck、summary-compiler
- MCP：bid-review（8 个工具：parse_tender / check_qualification / score_item / scan_risks /
  locate_span / export_report / list_documents / parse_attachment）
- 知识库：40 条规则索引（导入时按目标环境替换 index_names）

【依赖安装】
1. 导入 agent.json；
2. 依次导入 skills/ 下 4 个 SKILL.md；
3. 启动 mcps/bid_review_mcp.py（SSE，默认 8765），在 MCP 配置中填实际地址；
4. 导入知识库规则文档，确认 index_names 可用。

【自测结论】
- 25 份解析 25/25、6 字段 146/146；
- 8 字段扩展样本 14/14；
- 资格性人工标注 25 份 / 250 项 = 100%；
- 风险 TP 15 / FN 0 / FP 0；
- 规则覆盖 40 = 27 自动 + 10 人工 + 3 未实现（R25/R32/R33 需多家比价）；
- 本地 pytest 63 passed, 1 skipped（MCP 依赖缺失跳过）；容器回归待补。

【已知限制】
- T2/B2/B3 仍是 presence 档，可能把标题/一句话当实质响应；
- R25/R32/R33 单份不可判定；
- 专家评分项未获得人类专家盲评，学生/AI 分不替代。
- 全部演示数据为自造虚构，不输出中标/废标结论。

【截图】
见 screenshots/01-评审看板.png、screenshots/02-报告预览.png
```

## 五、合入后

1. 在 PR 评论或活动帖 <https://gitcode.com/org/ModelEngine/discussions/26> 回复：
   “课题 8 已合入 main，附 PR 链接”；
2. 按活动要求提交验收申请；
3. 保留过程仓库的提交记录、Issue、测试记录和部署文档；
4. 不要删除 fork 分支，便于复核。

## 六、注意

- **不要**把整个 `招投标评审助手` 源码工程（api/web/tests/data）放进 AgentsHub 目录；AgentsHub 只放智能体包；
- `agent.json` 必须是 Nexent 导出的版本，`prompt` 已由 `tools/agent_config.py sync` 同步；
- `mcp_url` 的 `host.docker.internal` 只适用于本机 Docker；目标环境按实际地址改；
- 知识库索引 `4-5897...` 如果目标环境没有，必须替换，不能留一个不存在的索引；
- 提交即同意 MIT License；
- 当前本机 Docker 不可用，容器全量 pytest 未跑；PR 前最好在干净环境补跑一次。
