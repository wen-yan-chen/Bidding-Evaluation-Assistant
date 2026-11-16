# 使用文档（USAGE）

> 招投标评审助手 v0.9.0（D9）｜政企采购 · 课题 8
> **AI 辅助评审结果，最终以评标委员会评审结论为准**

> 面向评标专家/采购经办人的图文版见 [`docs/使用说明.md`](docs/使用说明.md) /
> [`docs/使用说明.docx`](docs/使用说明.docx)；本文件偏技术（部署 / API / MCP / 排错）。

本文件面向「拿到仓库后要跑起来、要用页面/API/MCP 完成一次评审」的人。
部署排错细节见 `DEPLOY.md`；评测数字见 `docs/TEST_REPORT.md`；接口实现见 `api/routes/`。

---

## 一、5 分钟跑起来

### 1.1 前置

- Docker Desktop / Docker Engine + Compose；
- 本机空闲端口：**app 18080**、**mcp 8765**（本项目本机演示用 18080；默认 compose 是 8080，
  8080 被 32 题 `contract-review` 占用时务必改）；
- 不需要外部数据库；上传件、评审、报告都落盘在 `data/`（已 gitignore）。

### 1.2 启动

```bash
cd "D:\contest-8\行业智能体\政务\招投标评审助手（开发仓库）"
docker compose up -d --build
docker compose ps          # bid-review / bid-review-mcp 均 healthy
```

本机 `.env` 已设置：

```text
HOST_PORT=18080
MCP_PORT=8765
APP_TAG=0.9.0
ADMIN_USER=admin
ADMIN_PASSWORD=见本机 .env（不提交）
ADMIN_SESSION_SECRET=见本机 .env（不提交）
```

> `.env` 含 S3 凭据与管理员密码，已被 gitignore，**不要提交**。换机器时从 `.env.example` 复制并填写。

### 1.3 打开页面

- 评审看板：<http://127.0.0.1:18080/#review>
- 报告中心：<http://127.0.0.1:18080/#reports>
- 系统状态：<http://127.0.0.1:18080/#status>（先管理员登录）
- OpenAPI：<http://127.0.0.1:18080/api/docs>

### 1.4 冒烟

```bash
python tools/smoke_test.py --base http://127.0.0.1:18080
# 期望 10/10 通过（含扫描件 OCR）
```

---

## 二、页面使用

### 2.1 评审看板（一次完整评审）

1. **选择文件（支持多选）**
   - 从「已解析文档」下拉选一份；
   - 点「选择文件（可多选）」：在系统文件框里用 Ctrl/Shift 或鼠标拉框选多个 `docx / pdf / txt / md`；
   - 也可以把资源管理器里拉框选中的多个文件，直接拖到上传区；
   - 选多个后按钮显示「上传并解析 (N)」，逐份上传/解析；完成后给出成功/失败汇总，并选中最后一份成功文档；
   - 单份 ≤50 MB；扫描件逐份 OCR，单份约 13–16 秒；180 秒超时给提示；
   - 解析完成会显示页数、字符、条款、字段 6/6、降级说明。docx 无分页符时页码为「估算」。
2. **选择评分细则**
   - `profile-a`：综合评分法（价格 40 / 技术 40 / 商务 20）；
   - `profile-b`：技术优先型（价格 30 / 技术 50 / 商务 20）；
   - 切换只改选择，不自动重评；按钮会变成「用 profile-b 重新评审」。
3. **开始评审**
   - 调 `POST /api/review {doc_id, profile_id}`；
   - 结果区：总分卡 + 资格性表（10 项三态）+ 分项评分表（9 项）+ 风险清单。
4. **换细则对比**
   - 切 `profile-b` 后重新评审；
   - 总分卡显示 `profile-a 68.0 → profile-b 62.0（−6.0）`；
   - 分项表显示「较 profile-a：40.0 → 30.0 分」与差值徽标（P1 −10、T2 +2、T5 +2）。
5. **双栏对照**
   - 左栏按 `pages[]` 渲染原文；右栏按「全部 / 资格性 / 分项 / 风险 / 字段」列证据；
   - 点任一证据或表格「定位」，左栏滚动到对应页并 `<mark>` 高亮 `quote`；
   - 页码估算页标「估算」，OCR 页标「OCR」。
6. **导出报告**
   - 总分卡右下「导出 docx / 导出 pdf」；或进报告中心下载。

### 2.2 报告中心

- 列出最近评审（默认最近 20 份），行内「下载 docx / 下载 pdf」；
- 文件大小与数值摘要来自 `/api/report/{review_id}/meta`；
- 文档已不存在的历史评审默认隐藏，右上角可切换显示；
- 同一 `review_id` 重复导出返回同一文件（幂等）。

### 2.3 系统状态（管理员）

- 点「系统状态」先显示管理员登录；账号密码来自 `.env` 的 `ADMIN_USER` / `ADMIN_PASSWORD`，未配置时登录返回 503；
- 登录成功后才显示服务自检 6 项、运行信息、平台能力（MCP 已接入 8 个工具 / 知识库 / Skill 已挂载 4 个）、
  项目能力总览（D1–D9）、里程碑与交付物；
- 右上角「退出管理员」；会话默认 8 小时；
- 管理员接口统一在 `/api/admin/*`，健康检查与 `/api/info` 仍公开。

### 2.4 数据管理（删除文件 / 报告）

登录后进入「报告中心」，页面底部「数据管理」：

- 筛选：按文件名 / `doc_id` / 评审号过滤；
- 勾选文档或评审（支持表头全选）→「删除所选文档 / 删除所选评审」批量删除；
- 文档「删除」：删解析 JSON + 上传原件，并级联删其评审/报告；
- 评审「删报告」：只删 docx/pdf，保留评审；
- 评审「删评审」：删评审 JSON + 报告；
- 「清理重复文档」：按文件名每组保留最新 1 份，删除其余；
- 「清理无文档评审」：清理文档已不存在的历史评审。

对应接口：

```bash
POST   /api/admin/login       {"username":"...","password":"..."}
GET    /api/admin/session
POST   /api/admin/logout
GET    /api/admin/overview
DELETE /api/admin/doc/{doc_id}
DELETE /api/admin/review/{review_id}
DELETE /api/admin/report/{review_id}
POST   /api/admin/batch-delete {"doc_ids":["..."],"review_ids":["..."]}
POST   /api/admin/cleanup     {"mode":"duplicates"|"orphan_reviews"}
```

> 删除不可恢复；管理接口需要管理员 Cookie，未登录返回 401。

---

## 三、常用 API

> 所有示例默认 `BASE=http://127.0.0.1:18080`。返回 JSON 的接口可直接用浏览器/`curl`。

```bash
# 健康 & 信息
curl $BASE/health
curl $BASE/api/health
curl $BASE/api/info

# 上传并解析
curl -F "file=@data/samples/bid-001.docx" $BASE/api/upload

# 文档列表 / 详情 / 原文
curl $BASE/api/documents
curl $BASE/api/doc/<doc_id>
curl "$BASE/api/doc/<doc_id>/raw" -o original.docx

# 规则 / 细则
curl $BASE/api/rules
curl $BASE/api/rules/stats
curl $BASE/api/scoring/profiles

# 评审
curl -X POST $BASE/api/review \
  -H "Content-Type: application/json" \
  -d '{"doc_id":"<doc_id>","profile_id":"profile-a"}'

curl $BASE/api/review
curl $BASE/api/review/<review_id>

# 报告
curl -X POST $BASE/api/report \
  -H "Content-Type: application/json" \
  -d '{"review_id":"<review_id>","format":"docx"}' -o report.docx
curl "$BASE/api/report/<review_id>?format=pdf" -o report.pdf
curl $BASE/api/report/<review_id>/meta
```

### 3.1 一次最小闭环（PowerShell）

```powershell
$BASE = "http://127.0.0.1:18080"
$upload = curl.exe -s -F "file=@data/samples/bid-001.docx" "$BASE/api/upload" | ConvertFrom-Json
$review = curl.exe -s -X POST "$BASE/api/review" `
  -H "Content-Type: application/json" `
  -d "{\"doc_id\":\"$($upload.doc_id)\",\"profile_id\":\"profile-a\"}" | ConvertFrom-Json
$review.scoring.total          # 68.0
$review.qualification.counts   # provided=4, missing=6
$review.risks.Count            # 0
curl.exe -s "$BASE/api/report/$($review.review_id)?format=docx" -o report.docx
```

---

## 四、MCP 工具（Nexent 智能体）

- 服务地址（平台登记）：`http://host.docker.internal:8765/sse`；
- 容器内互访：`http://mcp:8765/sse`；
- 工具（8 个）：
  `parse_tender` / `check_qualification` / `score_item` / `scan_risks` / `locate_span` /
  `export_report` / `list_documents` / `parse_attachment`。

### 4.1 `scan_risks` 返回口径（D9 修正）

```json
{
  "rule_total": 40,
  "scanned_rules": 23,
  "scanned_pattern_rules": 18,
  "scanned_price_rules": 5,
  "manual_rule_ids": ["R01", "..."],
  "unimplemented_rule_ids": ["R25", "..."],
  "hit_count": 0,
  "hits": [],
  "scan_notes": ["..."]
}
```

- `scanned_rules` = 18 关键词 + 5 已实现计算型（R12/R13/R17/R31/R37）= **23**；
- 另 10 条 manual、7 条未实现；23 + 10 + 7 = 40。

### 4.2 平台侧 Skill（D9 已挂载）

| Skill | 触发场景 |
| --- | --- |
| `bid-rule-cards` | 判断某条内容是否违规前，按类别取规则卡 |
| `missing-qualification` | 资格性审查 / 缺什么材料 |
| `bid-risk-selfcheck` | 输出或导出前逐条自检、删误报 |
| `summary-compiler` | 生成摘要 / 报告 / 导出前成文 |

> 平台 32 题已有同名 `risk-selfcheck`，本项目使用唯一名 `bid-risk-selfcheck`，未覆盖他人技能。

---

## 五、数据与报告位置

| 内容 | 位置 | 是否入库 |
| --- | --- | --- |
| 样本与标注 | `data/samples/` | ✅ |
| 规则库 | `data/rules/rules.yaml` | ✅ |
| 评分细则 | `data/scoring/profile-a.yaml`、`profile-b.yaml` | ✅ |
| 上传原件 | `data/uploads/` | ❌ gitignore |
| 解析 JSON | `data/parsed/` | ❌ gitignore |
| 评审 JSON | `data/reviews/` | ❌ gitignore |
| 报告 docx/pdf | `data/reports/` | ❌ gitignore |

报告/摘要内容与页面数字同源：报告只读评审 JSON，不重新算分。

---

## 六、排错

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 页面能开、接口网络错误 / 文档列表为空 | 用 `file://`、DSH 文件预览或错误端口打开 | 用 `http://127.0.0.1:18080/#review`，Ctrl+F5；不要用 8080 |
| `docker compose ps` 不 healthy | 构建/启动失败 | `docker compose logs --tail=200 app` |
| 上传 413 | 超过 50 MB | 压缩或拆分；或调 `MAX_UPLOAD_MB` |
| 上传 415 | 扩展名不支持 | 只支持 docx / pdf / txt / md |
| 扫描件 13–16 秒 | OCR 正常耗时 | 等进度条；不要重复点 |
| docx 页码「估算」 | 无分页符 | 以原件为准；跳转允许偏 1 页 |
| 评审 404 | 文档不存在/已清理 | 重新上传后再评审 |
| 报告 404 | 报告未生成或文档丢失 | 先评审再导出；确认 doc_id 还在 |
| 依据全变「未检索到权威依据」 | 知识库索引名不匹配 | 换成本环境 `index_names`；见 D4 交接 |
| 换机器后平台 Skill 不触发 | 未重新导入 agent / 名称不匹配 | 重新导入 `agent.json`，确认 4 个 skill_names |
| `.env` 报错 | 未复制 `.env.example` | 复制并填 S3/端口；不要提交 |

---

## 七、开发与回归命令

```bash
python tools/smoke_test.py --base http://127.0.0.1:18080
python tools/validate_rules.py
python tools/validate_quotes.py
python tools/agent_config.py check

docker compose run --rm --no-deps -v "%CD%\tests:/app/tests" app \
  sh -c "pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple pytest httpx && python -m pytest -q"

docker compose run --rm --no-deps \
  -v "%CD%\tools:/app/tools" -v "%CD%\data\samples:/app/data/samples" \
  app python tools/eval_parse.py --strict

docker compose run --rm --no-deps \
  -v "%CD%\tools:/app/tools" -v "%CD%\data\samples:/app/data/samples" \
  app python tools/eval_risks.py --strict

docker compose run --rm --no-deps -v "%CD%\tools:/app/tools" app \
  python tools/check_report.py --all
```

---

## 八、已知限制

1. docx 无分页符时页码为估算，跳转允许偏 1 页；
2. 双栏对照渲染解析后的纯文本，不还原原 PDF/docx 版式；
3. 表格单元格里的字段仍可能抽不到（D9 未增强解析层）；
4. 报告幂等但没有自动失效，改数据需换新 `review_id`；
5. 没有人类专家双盲评分；AI 双盲代理（严格细则 15/15、专业裁量 0/15）见 `docs/TEST_REPORT.md` §4.3；
6. 合成样本与开发集同分布，100%/0% 不代表真实业务泛化；
7. 主页面为单机演示；系统状态/数据管理有管理员密码门禁（演示级，不是多用户权限系统），
   `/api/health` 与 `/api/info` 仍公开，删除类接口才要求管理员 Cookie。

---

## 九、关键文件索引

- 部署：`DEPLOY.md`、`docker-compose.yml`、`Dockerfile`
- 交接：`docs/D1-交接文档.md` … `docs/D9-交接文档.md`
- 自测：`docs/D1-自测记录.md` … `docs/D9-自测记录.md`
- 评测：`docs/TEST_REPORT.md`、`docs/留出集单独成绩.md`、`docs/数据说明.md`
- 页面截图：`docs/screenshots/`
- 平台配置：`agent.json`、`prompt.md`、`skills/`
