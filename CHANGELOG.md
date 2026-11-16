# CHANGELOG

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与语义化版本。

## [0.9.0] — 2026-11-16（D9 Skill 挂载 + 评测交付）

### Added

- `skills/`：4 个可上传 Skill 包（`bid-rule-cards` / `missing-qualification` /
  `bid-risk-selfcheck` / `summary-compiler`），每个 zip 根目录一个 `SKILL.md`，含 YAML frontmatter
  （`name` / `description` / `allowed-tools`）与四段正文（When to use / Inputs / Outputs / Hard rules）。
- 平台侧：4 个 Skill 已上传；Nexent agent v5「招投标评审助手-2611161002」于 2026-11-16 10:02 发布；
  平台文件与本地 `SKILL.md` SHA256 逐字节一致。
- `docs/TEST_REPORT.md`：六条验收标准逐项数字、证据、差距；新增 AI 双盲参考评分
  （严格细则 15/15、专业裁量 0/15），人类专家项仍标代理。
- `docs/留出集单独成绩.md`：dev / holdout 单独成绩（检出 100%、误报 0%）。
- `USAGE.md`：页面 / API / MCP / 报告 / 排错。
- `docs/使用说明.md` / `.docx`：面向评标专家/采购经办人的图文操作说明（对象、需求、步骤、结果、限制）。
- 管理员入口：系统状态需 `ADMIN_USER` / `ADMIN_PASSWORD` 登录；MCP 显示「已接入 8 个工具」；
  新增文档/评审/报告的删除、批量删除与重复文档清理（`/api/admin/*`）。
- 评审看板上传支持**多选 / 拖拽多个文件**，逐份上传解析并汇总成功/失败。
- 评审看板隐藏「降级」标签；报告中心用「降级技术」标出 OCR/页码估算，报告内注明口径。
- 数据管理文档行新增「预览 / 保存」：PDF 界面内嵌原文，docx/txt/md 显示解析文本。
- 评审看板去掉所有渐变，步骤卡/进度条/总分卡改为纯蓝色。
- `docs/D9-自测记录.md`、`docs/D9-交接文档.md` / `.docx`。

### Fixed

- `mcps/bid_review_mcp.py`：`scan_risks.scanned_rules` 旧实现只统计关键词规则（18），
  漏掉 5 条已实现的计算型规则（R12/R13/R17/R31/R37）。现改为 **23**，并新增
  `scanned_pattern_rules` / `scanned_price_rules` / `manual_rule_ids` /
  `unimplemented_rule_ids` / `scan_notes`；平台输出不再出现 18 + 10 + 7 ≠ 40。
- `tests/test_rules.py`：锁定 23 + 10 + 7 = 40；`tests/test_health.py`：锁定 `skills=true`。

### Changed

- `agent.json`：第四个 Skill 由 `risk-selfcheck` 改为唯一名 `bid-risk-selfcheck`
  （平台已有 32 题 contract-review 的同名技能，不能覆盖）。
- `api/routes/health.py`：`skills` 能力开关置 `true`。
- 前端状态页：Skill 卡片显示「已挂载 4 个」；能力边界把“Skill 待 D9”改为已上线。
- `VERSION` / `docker-compose.yml`：`0.9.0`；默认 `APP_TAG=0.9.0`。
- README / milestones / docs README 同步到 D9。

### Verified

- Skill：4 个平台文件与本地 SHA256 一致；`agent_update` / `agent_version_publish` 审计成功；
  平台对话输出「扫描 23 条（18+5），命中 0」。
- 解析：25/25 = 100%；字段 146/146 = 100%；
- 风险：15/15 = 100%；误报 0/20 = 0%（dev 10/10、holdout 5/5）；
- 溯源：`validate_quotes.py` 0 处不一致；
- 报告：`check_report.py --all` 50/50；
- `pytest` **54 passed**；`smoke_test.py` **10/10**；`agent_config.py check` OK 11 / WARN 0 / ERROR 0。
- 已知缺口：人类专家双盲评分缺失；AI 双盲严格细则 15/15、专业裁量 0/15，
  `TEST_REPORT.md` 第 2 条标代理，D10 前补真人专家。

## [0.8.0] — 2026-11-16（D8 评审看板 + 双栏对照 + 报告中心）

### Added

- `web/` 重构为三大视图：**评审看板 / 报告中心 / 系统状态**，单页自包含、无 CDN、无外链字体。
  - 评审看板：选择已解析文档或上传新文件 → 选择 `profile-a` / `profile-b` → 触发评审 → 总分卡
    （总分/满分、资格性、风险、细则指纹、规则指纹、页码口径）+ 资格性表 / 分项评分表 / 风险清单。
  - 换细则对比：切换 `profile_id` 重新评审后，评分表逐项显示「较上次」分数与差值（68→62，P1 40→30、
    T2 10→12、T5 6→8），总分卡同步显示 `profile-a 68.0 → profile-b 62.0`。
  - 双栏对照：左栏按 `/api/doc/{id}` 的 `pages[]` 渲染原文，右栏按「全部/资格性/分项/风险/字段」列出证据；
    点击任一项用 `char_start/char_end` 定位并 `<mark>` 高亮 `quote`，找不到偏移时回退 `quote` 检索。
  - 报告中心：`GET /api/review` 列最近评审；行内下载 docx/pdf（`GET /api/report/{id}?format=`），
    文件大小与数值摘要来自 `/meta`；文档已不存在的历史评审默认隐藏、可切换显示。
  - 状态与错误：上传中显示已完成时间与进度，扫描件提示 13–16 秒；上传失败 / 解析 failed / 评审 404 /
    报告未生成都有可读提示；空态不白屏。
- `tests/test_web.py` 2 条：三视图 + 免责声明存在、静态资源自包含（无 http/https、无 `@import`）。
- `docs/screenshots/D8-评审看板.png`、`D8-双栏对照.png`、`D8-报告中心.png`、`D8-换细则对比.png`。
- `docs/D8-交接文档.md` / `.docx`、`docs/D8-自测记录.md`。

### Changed

- `VERSION` → `0.8.0`；`docker-compose.yml` 默认 `APP_TAG` → `0.8.0`；`data/meta/milestones.json`
  M5（前端看板）置 `done`、当前进度切 `D8`、阶段交付物换成 D8 清单。
- `tests/test_health.py`：修正 D7 后遗留的能力断言（`report_export` 应为 `true`），并补齐
  `ocr` / `qualification` / `scoring` 的断言。
- README 更新到 v0.8.0：D8 任务表、交付物索引、接口说明、已知限制（双栏纯文本、报告中心过滤、单机演示）。

### Verified

- 干净浏览器打开 `http://127.0.0.1:18080`：0 控制台错误、0 个 4xx 请求、无 CDN；
- 用例 1：`bid-001.docx` + `profile-a` → **68.0/100**、资格性 **4 已提供 / 6 缺失**、风险 **0**；
- 用例 2：切 `profile-b` → **62.0/100**，P1 **40→30**、T2 **10→12**、T5 **6→8**；
- 用例 3：点击「报价」字段 → 左栏第 1 页滚动并高亮 `投标报价：人民币 1,286,000.00 元`；
- 报告中心：docx 41.4 KB / pdf 10.6 KB 下载成功，`check_report.py` 数值一致，页脚含免责声明与页码；
- `pytest` **49 passed**、`smoke_test.py` **10/10**、1280/1600 宽度无横向溢出、打印样式可读。

## [0.7.0] — 2026-11-15（D7 知识库治理 + 提示词 v3 + 报告导出）

### Changed

- 知识库切到「一文件一规则」：索引由 `2-c6515a…`（1 文件 / 8 分片）换成 `4-5897…`（40 文件 / 40 分片），
  `agent.json` 的 `index_names` 同步更新；平台侧同名知识库现有 3 个副本，保留 40 文档那个、其余两个空库待删。
- `prompt.md` 升级到 **v2（3794 字）**：补充 5 个 MCP 工具的真实调用时机、「换 `profile_id` 重算并对比」、
  D6 的能力边界（10 条 manual / 7 条未实现 / 限价缺失时 R12-R13-R31 不判 / 资质类只在资格核验），
  并删除 D1 遗留的「工具尚未上线」与「待办」章节；`agent.json.prompt` 由脚本同步。
- 新增 `docs/D7-交接文档.md`（含 .docx）与 `docs/D7-自测记录.md`，记录本次改动、验证与平台侧待办。

### Added

- MCP 新增 `list_documents`（列出最近解析文档，解决"助手拿不到 doc_id"）与 `parse_attachment`（直接解析
  Nexent 聊天附件，S3/MinIO 取回后走统一入库），工具总数达到 **8 个**。
- `api/ingest.py`：页面与聊天附件共用的入库入口（解析 + 字段 + 落盘），保证两条路径口径一致。
- `api/s3fetch.py`：从 Nexent 附件存储按 `s3://bucket/key` 取文件（凭据走环境变量，不写进代码）。
- 报告导出：`api/report/builder.py`（九章装配 + 双指纹 + 合同六要素）、`docx_export.py`、`pdf_export.py`
  （reportlab + 内置 CID 中文字体，**不依赖 LibreOffice**）、`api/routes/report.py`
  （`POST /api/report`、`GET /api/report/{id}`、`GET /api/report/{id}/meta`）、MCP `export_report`。
- `tools/check_report.py`：报告数值一致性校验（docx/pdf 中总分、满分、风险数、双指纹必须与评审 JSON 一致）。
- `tests/test_report.py` 5 条：生成与数值一致、幂等、meta、下载、错误处理。
- 截图：`docs/screenshots/D7-报告docx样例.png`、`D7-报告pdf样例.png`。

### Changed

- `/api/health`：`report_export` 能力开关置 true。
- `agent.json`：`mcp_info` 补齐 8 个工具名；`prompt` 同步 v3。
- `data/reports/` 加入 `.gitignore`（报告为运行时产物）。

### Verified

- 报告：docx 41.5 KB（PK 头）/ pdf 10.7 KB（%PDF-），九章齐全，页脚免责 + 页码；
- `check_report.py`：docx/pdf 数值与评审 JSON 逐项一致（68.0/100、风险 0、双指纹）；
- `pytest` **47 passed**；`smoke_test.py` **10/10**；MCP 协议实测 8 工具可用。

## [0.6.0] — 2026-11-15（D6 风险扫描 + 误报治理）

### Added

- `api/checks.py`：计算型风险检查 —— R12 超限价、R13 低于成本、R17 投标有效期、R31 贴近限价、
  R37 大小写金额不一致、R40 整万元；含**中文大写金额解析**（`壹佰贰拾捌万陆仟元整` → 1286000）。
- `api/rules.py` 扫描引擎升级：合规定式过滤（`compliant`）、否定/处罚上下文（无需/没收/不予退还/扣除）、
  跳过资质门槛类（避免与资格性核验重复）、计算型规则合流、`scan_notes()` 说明"哪些规则本次不参与判定"。
- `data/samples/risk/`：15 份**植入风险样本**（每份一类：超限价、低于成本、有效期、大小写、
  资质缺失、串标编制人、保证金同账户、弄虚作假、贴标、联合体无协议）+ 5 份干净对照 + `manifest.json`（dev/holdout 标注）。
- `tools/make_risk_samples.py`：样本与标注一键重建。
- `tools/eval_risks.py`：检出率 / 误报率评测（逐样本表、分规则召回、dev/holdout 分档、`--strict`）。
- `tests/test_risks.py` 7 条：干净样本零命中、8 类植入命中、溯源一致、无限价不误判、大写解析、资格缺失、扫描幂等。

### Changed

- 规则库：R17 / R37 由 `pattern` 改为 `price`（关键词必误报），R40 改为 `manual`（需多投标人对比），
  R18 / R20 补充合规定式；知识库指纹变为 `188bf9a7ff58f159`（**平台需重新上传 `knowledge/rules-full.md`**）。
- `/api/health`：`risk_scan` 能力开关置 true；里程碑 M3 置为完成、当前进度切到 D6。

### Verified

- 植入风险样本：检出 **15/15 = 100%**（dev 10/10、holdout 5/5），误报 **0/20 = 0%**；
- 解析样本扩到 **25 份**（20 文本层 + 5 扫描件）：解析 25/25 = 100%、字段 146/146 = 100%；
- 新增 `tools/report_samples.py` 与 `docs/数据说明.md`（样本清单、标注、dev/holdout、限制与合规）；
- 干净对照（bid-001~005）扫描命中 **0 条**（误报回归基线）；
- `pytest` **42 passed**；`smoke_test.py` **10/10**；`validate_rules.py` 0 提示。

### Known issues

- 合成样本与开发集同分布，100%/0% 不代表真实业务泛化；
- R25/R32/R33/R34/R36/R38/R39 仍依赖多投标人比价或表格解析，尚未实现。

## [0.5.0] — 2026-11-15（D5 资格性核验 + 评分细则）

### Added

- 评分细则 `data/scoring/profile-a.yaml`（价格 40 / 技术 40 / 商务 20）与 `profile-b.yaml`（30/50/20），
  每套 9 个评分项，含分档（`tiers`）、依据（`basis`）、依据状态；`requirements` 声明最高限价与工期要求。
- `api/scoring.py`：细则加载与指纹、报价解析（元/万元/￥）、工期解析（天/月/年）、
  三类评分（`price_ratio` / `duration` / `presence`）、分项得分与扣分汇总、每项带 `evidence`。
- `api/review/qualification.py`：R01–R10 资格性三态（`provided` / `insufficient` / `missing`），
  含否定词上下文判定，明确"文本核验不替代原件核验"。
- `api/review/service.py`：评审编排（核验 → 算分 → 扫描 → 汇总 → 落盘 `data/reviews/`），
  结果带 `profile.digest` 与 `rule_digest` 双指纹。
- `api/routes/review.py`：`GET /api/scoring/profiles`、`POST /api/review`、`GET /api/review/{id}`、`GET /api/review`。
- MCP 新增 `check_qualification` 与 `score_item`（累计 5 个工具），协议实测 `tools(5)`。
- `tests/test_review.py` 8 条：细则加载/解析/分档/超限价/工期档/资格三态/确定性与换细则/接口往返。

### Changed

- `/api/health`：`qualification` 与 `scoring` 能力开关置 true；里程碑 M3 置为进行中、当前进度切到 D5。
- `.gitignore` 增加 `data/reviews/`（评审结果为运行时产物）。

### Verified

- 同一份 bid-001：A 套 **68.0/100**、B 套 **62.0/100**（P1 40→30、T2 10→12、T5 6→8）；
- 同一 `doc_id + profile_id` 连续两次调用均 68.0，风险列表一致；
- `pytest` **35 passed**；`smoke_test.py` **10/10**；`validate_rules.py` 0 提示；`agent_config.py check` 0 ERROR。

### Known issues

- 风险扫描存在 3 类误报（R18 合规定式、R17 需比较天数、R37 大小写金额），D6 通过 `compliant` 过滤与计算型规则修复。

## [0.4.0] — 2026-11-15（D4 规则库 + 知识库 + MCP）

### Added

- 规则库 `data/rules/rules.yaml`：40 条（资质门槛/废标条款/围标串标/报价异常 各 10 条），
  每条含 `condition / level / detect / patterns / basis_status / basis / compliant`；
  依据三态分布：verified 21、pending 15、na 4；等级分布：高 23 / 中 13 / 低 4。
- `api/rules.py`：规则加载（YAML 唯一来源）、指纹（sha256 前 16 位）、统计、确定性扫描
  （字面量匹配 + 条款定位，命中带 `clause_id/page/char_start/char_end/quote`），`legal_basis` 由三态统一出口。
- `api/routes/rules.py`：`GET /api/rules`、`/api/rules/stats`、`/api/rules/{rule_id}`。
- `tools/validate_rules.py`：条数/分类/id 连续/依据三态/知识库指纹一致性门禁（退出码可接 CI）。
- `tools/export_kb.py`：YAML → `knowledge/rules-full.md`（40 块，22.0 KB）+ `knowledge/manifest.json` 指纹清单；
  `--check` 模式校验"规则库 ↔ 知识库"未漂移。
- `mcps/bid_review_mcp.py`：FastMCP（SSE，8765）三个工具 `parse_tender` / `scan_risks` / `locate_span`；
  失败返回 `{"error": ...}` 不抛异常；内网关闭 DNS rebinding 防护（否则容器内 Host=mcp:8765 回 421）。
- `docker-compose.yml` 新增 `mcp` 服务（与 app 共用 `./data`），`MCP_URL` 默认 `http://mcp:8765/sse`。
- `tests/test_rules.py` 7 条：条数分类、依据三态、指纹一致、扫描溯源、扫描幂等、接口、MCP 工具直调。

### Changed

- `agent.json`：`index_names` 填入平台知识库索引 `2-c6515aaca42f46c58554031ab149e820`，
  `mcp_url` 改为 `http://mcp:8765/sse`；`agent_config.py check` 变为 **0 WARN / 0 ERROR**。
- `/api/health` 能力开关 `mcp` 置为 true；里程碑 M2 置为已完成、当前进度切到 D4。

### Verified

- `validate_rules.py`：40 条、四类各 10、依据 21/15/4、知识库指纹一致，0 提示；
- MCP 协议实测（SSE）：`tools(3)`，`scan_risks` 扫描 20 条可自动检测规则命中 6 条，`locate_span` 正负例均正确；
- `pytest` **27 passed**；`smoke_test.py` **10/10**。

## [0.3.0] — 2026-11-15（D3 扫描件 OCR + 边界样本）

### Added

- OCR 通道 `api/parsers/ocr.py`：`rapidocr-onnxruntime==1.2.3`（模型随 wheel 内置、离线可跑）+
  `pypdfium2` 渲染 200 DPI；引擎懒加载；按阅读顺序重排；置信度 < 0.30 的行丢弃并计数；异常不穿透。
- `pdf_parser` 逐页判定：有文本层走文本层、无文本层走 OCR、都失败记 `empty_pages`；
  `meta` 新增 `text_pages / ocr_pages / empty_pages / ocr_low_conf_lines`，并在 `degraded` 里写明
  "第 X 页为 OCR 识别文本（可能有识别误差，建议人工复核）"。
- 样本：`data/samples/scan-001..005.pdf`（5 份无文本层扫描件，200 DPI，约 0.6 MB/份）；
  `data/samples/boundary/`（空白页 / 低分辨率 / 旋转 90° + 说明）；`manifest.json` 扩到 15 条并加 `ocr` 标记。
- `tools/eval_parse.py` 指标按"文本层 / 扫描件"分列，新增 `OCR` 列与"多抽"统计。
- `tools/smoke_test.py` 第 10 项：扫描件走 OCR 的端到端检查（含耗时）。
- `tests/test_scan.py` 5 条：扫描件 OCR、字段、空白页、低清不编造、旋转优雅降级。
- 页面：解析面板显示「含 N 页 OCR 识别」与 `OCR 页 N 页` 徽标；`/api/upload` 返回 `text_pages/ocr_pages/empty_pages`。

### Changed

- `docx_parser` 页码估算从"按字符数（1100 字/页）"改为**按段落行数（每页 38 行 × 38 字）**，更贴近 Word 分页。
- `Dockerfile`：`rapidocr` 自带的 `opencv-python`（GUI 版）在 slim 镜像缺 `libxcb/libGL` 会导致 `import cv2` 失败，
  改为安装 `opencv-python-headless`，并在构建期执行 `import cv2, pypdfium2, rapidocr_onnxruntime` 自检。
- `/api/health` 能力开关新增 `ocr`（true）；里程碑 M1 置为已完成、当前进度切到 D3。

### Verified

- 15 份样本（10 文本层 + 5 扫描件）：解析成功率 **15/15 = 100%**、字段准确率 **88/88 = 100%**、多抽 **0**；
- `validate_quotes.py`：23 份文档 / 117 字段 / 336 条款，**0 处不一致**；
- 扫描件单份耗时 13.8–16.2 s（3 页 / 200 DPI）；边界样本 3 份全部降级但不崩；
- `smoke_test.py` **10/10**；`pytest` **20 passed**（59.84 s）。

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
