# 测试报告（D9 评测与交付）

> 版本：v0.9.0｜日期：2026-11-16｜环境：Docker Compose（app 18080 / mcp 8765）
> 数据：全部为自造虚构样本，不含真实招投标信息；不给出中标/废标结论。
> 免责声明：**AI 辅助评审结果，最终以评标委员会评审结论为准**

---

## 一、结论摘要

六条验收标准中，**5 项有实测数字并达成**；第 2 项「专家评分偏差」缺少真实专家双盲数据，
用两套评分细则的专家设定值做代理复算，**如实标注为遗留项**，不伪造专家分。

| # | 验收标准 | 要求 | 实测 | 判定 |
| :-: | --- | --- | --- | :-: |
| 1 | 20 份混合格式（含 5 扫描件）解析成功率 / 字段准确率 | ≥90% / ≥90% | **25/25 = 100% / 146/146 = 100%** | ✅ |
| 2 | 资格核验一致率 / 评分与专家偏差 ±5 分比例 | ≥90% / ≥85% | 资格核验 bid-001 10 项人工核对一致；评分用两套细则设定值代理；**无真实专家双盲** | ⚠️ 部分 |
| 3 | 10 份植入风险检出率 / 误报率 | ≥85% / ≤15% | **15/15 = 100% / 0/20 = 0%**（dev 10/10、holdout 5/5） | ✅ |
| 4 | 风险溯源准确率（抽查 20 条） | 100% | `validate_quotes.py`：**0 处不一致**；风险均带 page/quote | ✅ |
| 5 | 报告/摘要一键下载、格式正确、与页面一致 | 通过 | docx/pdf 下载成功；`check_report.py --all` **50/50** | ✅ |
| 6 | 通用验收（免责、无占位、可复现、自包含） | 全部 | smoke 10/10、pytest 49、无 CDN、1280/打印可读 | ✅ |

> 第 2 项的缺口不影响「确定性算分」本身：两套细则的总分 68.0 / 62.0、分项分数、扣分项都可逐项复算；
> 缺的是「真实专家对同一批样本的独立打分」这份外部参照。

---

## 二、评测集与规则库

### 2.1 解析样本（25 份）

| 类别 | 数量 | 构成 |
| --- | ---: | --- |
| 文本层文件 | 20 | docx 9 / pdf 4 / txt 7 |
| 扫描件（无文本层 PDF） | 5 | scan-001 ~ scan-005 |
| 边界样本 | 3 | 空白页 / 低分辨率 / 旋转 90° |
| 字段标准答案 | 146 | `data/samples/manifest.json` |

行业分布：货物 10 / 服务 10 / 工程 5；全部由 `tools/make_samples.py` 生成（内容虚构）。

### 2.2 风险样本（15 份植入 + 5 份干净对照）

- 15 份每份只植入一类风险，覆盖 R01/R09/R12/R13/R14/R15/R16/R17/R19/R20/R21/R27/R31/R35/R37；
- 5 份干净对照用于误报率；
- dev：10 份风险 + 3 份干净；holdout：5 份风险 + 2 份干净；
- 标注：`data/samples/risk/manifest.json`。

### 2.3 规则库与评分细则

| 项 | 值 |
| --- | --- |
| 规则条数 | 40（资质门槛 / 废标 / 围标 / 报价异常 各 10） |
| 检测方式 | manual 10 / pattern 18 / price 12 |
| 实际自动覆盖 | **23 条 = 18 关键词 + 5 计算型**（R12/R13/R17/R31/R37） |
| 暂未实现 | R25、R32、R33、R34、R36、R38、R39（7 条） |
| 依据三态 | verified 21 / pending 15 / na 4 |
| 规则指纹 | `188bf9a7ff58f159` |
| 评分细则 | `profile-a`（40/40/20，指纹 `fd898ab727cf8c12`）、`profile-b`（30/50/20，指纹 `5209c8caa7346be8`） |

> D9 修正：MCP `scan_risks.scanned_rules` 旧实现只统计 `pattern`，会把「扫描 23 条」误报成「18 条」；
> 现已改为 18 + 5 = 23，并在返回体中单列 `scanned_pattern_rules` / `scanned_price_rules` /
> `manual_rule_ids` / `unimplemented_rule_ids` / `scan_notes`。

---

## 三、标准 1：解析成功率与字段准确率

复算命令：

```bash
docker compose run --rm --no-deps \
  -v "$PWD/tools:/app/tools" -v "$PWD/data/samples:/app/data/samples" \
  app python tools/eval_parse.py --strict
```

实测输出（2026-11-16）：

```text
文本层：解析成功率 20/20 = 100.0%｜字段准确率 116/116 = 100.0%｜多抽 0
扫描件：解析成功率 5/5 = 100.0%｜字段准确率 30/30 = 100.0%｜多抽 0
合计：解析成功率 25/25 = 100.0%｜字段准确率 146/146 = 100.0%｜多抽 0
结论：通过
```

说明：

- docx 无分页符时按「每页约 38 行 × 38 字」估算页码，`parse_status=degraded`，页面与报告均标「估算」；
- 扫描件走 OCR，单份 3 页约 13–16 s（200 DPI）；`meta.ocr_pages` 标注 OCR 页，提示人工核对原件；
- 缺字段边界（bid-008/014/018）按 4/6、5/6、5/6 如实返回，不编造。

---

## 四、标准 2：资格核验一致率与评分偏差

### 4.1 资格性核验（bid-001，10 项）

| 状态 | 数量 | 规则 |
| --- | ---: | --- |
| 已提供 | 4 | R01、R04、R05、R10 |
| 效力不足 | 0 | — |
| 缺失 | 6 | R02、R03、R06、R07、R08、R09 |

人工对照（D5 自测记录 §5）：上述 10 项三态一致；R01/R09 在风险样本中也按预期命中缺失。
结论：**该样本 10/10 一致**；尚未对 25 份样本做逐项人工双盲标注，故不宣称全量 ≥90%。

### 4.2 评分（同一文件、两套细则）

| 项 | profile-a | profile-b | 差值 |
| --- | ---: | ---: | ---: |
| P1 投标报价 | 40.0 / 40 | 30.0 / 30 | −10.0 |
| T2 实施方案与进度计划 | 10.0 / 10 | 12.0 / 12 | +2.0 |
| T5 工期响应 | 6.0 / 6 | 8.0 / 8 | +2.0 |
| **总分** | **68.0 / 100** | **62.0 / 100** | **−6.0** |

- 同一 `doc_id + profile` 连续调用结果一致（无随机量），风险列表顺序一致；
- 每个分项带 `page / quote`，扣分项可逐项回溯。

### 4.3 专家评分偏差（遗留）

当前没有「真实评标专家对同一批样本的独立评分」数据，因此无法计算「±5 分内 ≥85%」。
本报告不把两套细则的设定值冒充专家分，只如实记录：

- 两套细则的专家设定值（68/62）与确定性引擎输出一致；
- 分项权重、扣分理由、证据均可复算；
- **建议 D10 前补 10–15 份专家双盲评分**，再计算偏差比例；在此之前该项标注为「未达成/待补」，不做虚假达标。

---

## 五、标准 3：风险检出率与误报率

复算命令：

```bash
docker compose run --rm --no-deps \
  -v "$PWD/tools:/app/tools" -v "$PWD/data/samples:/app/data/samples" \
  app python tools/eval_risks.py --strict
```

实测输出：

```text
合计：TP=15　FN=0　FP=0　检出率=100.0%（要求 ≥85%）　误报率=0.0%（要求 ≤15%）
dev：TP=10　FN=0　FP=0　检出率=100.0%　误报率=0.0%
holdout：TP=5　FN=0　FP=0　检出率=100.0%　误报率=0.0%
结论：通过
```

按规则：R01/R09/R12/R13/R14/R15/R16/R17/R19/R20/R21/R27/R31/R35/R37 均为 **1/1**。

说明：100%/0% 是在**自造合成样本**上得到的，holdout 与 dev 同分布，不代表真实业务泛化能力；
详见 `docs/数据说明.md` 与 `docs/留出集单独成绩.md`。

---

## 六、标准 4：风险溯源准确率

复算命令：

```bash
python tools/validate_quotes.py
```

当前运行时全量结果：

```text
校验 128 份文档 / 字段 747 / 条款 2621
不一致 0 处
结论：通过——所有 quote 是原文切片，页码与偏移完全自洽
```

验收样本层面的口径：25 份样本共 146 个字段、182 条条款，0 处不一致；
每条风险命中都带 `rule_id / level / page / char_start / char_end / quote / legal_basis / basis_status`，
抽查 20 条均可定位到原文。

---

## 七、标准 5：报告与摘要下载、格式、内容一致

### 7.1 下载与格式

以 `rv-20261116-092505-5ac921`（profile-b，62.0/100）为例：

| 格式 | 大小 | 校验 |
| --- | ---: | --- |
| docx | 42,439 B（41.4 KB） | python-docx 打开成功；37 段 / 6 表；页脚含免责声明 + `PAGE` 域 |
| pdf | 10,875 B（10.6 KB） | pypdf 打开成功；3 页；页码 1/2/3；免责声明可检索 |

### 7.2 报告数值 = 评审 JSON

```text
python tools/check_report.py --all（容器内）
  [ OK ] rv-20261116-092502-c55435: docx/pdf 数值与评审 JSON 一致
  [ OK ] rv-20261116-092505-5ac921: docx/pdf 数值与评审 JSON 一致
  ...
  校验 50 份：通过 50，失败 0
```

报告九章齐全，页脚同时有免责声明与页码；报告只读评审 JSON，不重新算分。

---

## 八、标准 6：通用验收

| 项 | 实测 |
| --- | --- |
| 干净环境起服务 | `docker compose up -d --build` 成功；app/mcp 均 healthy |
| smoke | `python tools/smoke_test.py --base http://127.0.0.1:18080` → **10/10** |
| pytest | **49 passed**（1 warning，Starlette 弃用提示，不影响） |
| 前端 | 无 CDN / 无外链字体；1280 宽无横向溢出；A4 打印可读 |
| 免责声明 | 页面、报告页脚、系统提示词三处固定原文 |
| 无占位按钮 | 所有按钮均有真实行为；未完成能力标「待 D9/D10」 |
| 脱敏 / 合规 | 样本主体名称、金额、编号均为虚构；不输出中标/废标结论 |
| 配置 | `agent_config.py check` → OK 11 / WARN 0 / ERROR 0 |

---

## 九、D9 平台侧：Skill 挂载

| 项 | 证据 |
| --- | --- |
| 4 个 Skill | `bid-rule-cards` / `missing-qualification` / `bid-risk-selfcheck` / `summary-compiler` |
| 平台文件 | 与本地 `SKILL.md` **SHA256 逐字节一致** |
| 上传审计 | 2026-11-16 10:02:24 `skill_upload result=success` |
| 智能体发布 | 2026-11-16 10:02:48 `agent_version_publish result=success`，v5「招投标评审助手-2611161002」 |
| 能力开关 | `/api/health` 的 `skills=true` |
| 风险扫描口径 | MCP 返回 `scanned_rules=23`（18 关键词 + 5 计算型），命中 0；10 manual + 7 未实现 |

平台已有 32 题 contract-review 的同名 `risk-selfcheck`，本项目改用唯一名 `bid-risk-selfcheck`，未覆盖他人 Skill。

---

## 十、缺陷、边界与后续

| # | 事项 | 状态 / 处置 |
| :-: | --- | --- |
| 1 | 真实专家双盲评分缺失 | **未达成**；D10 前补 10–15 份专家评分，再计算 ±5 比例 |
| 2 | docx 页码估算 | 已知限制；页面/报告标「估算」，跳转允许偏 1 页 |
| 3 | 表格单元格字段抽取 | 已知限制；D10 若增强，需改解析层，不在前端猜 |
| 4 | 报告幂等但无自动失效 | 已知限制；改数据需换新 `review_id` 重新导出 |
| 5 | `scan_risks` 旧计数 18 | **已修**；D9 改为 23，并加回归测试 |
| 6 | 合成数据同分布 | 100%/0% 不代表真实泛化；报告与自测记录均如实标注 |

---

## 十一、复现

```bash
docker compose up -d --build
docker compose ps

python tools/smoke_test.py --base http://127.0.0.1:18080

docker compose run --rm --no-deps -v "%CD%\tests:/app/tests" app \
  sh -c "pip install -q -i https://pypi.tuna.tsinghua.edu.cn/simple pytest httpx && python -m pytest -q"

docker compose run --rm --no-deps \
  -v "%CD%\tools:/app/tools" -v "%CD%\data\samples:/app/data/samples" \
  app python tools/eval_parse.py --strict

docker compose run --rm --no-deps \
  -v "%CD%\tools:/app/tools" -v "%CD%\data\samples:/app/data/samples" \
  app python tools/eval_risks.py --strict

python tools/validate_quotes.py
python tools/validate_rules.py
docker compose run --rm --no-deps -v "%CD%\tools:/app/tools" app \
  python tools/check_report.py --all
```

> 本报告的数字均可由上述命令复算；样本与标注见 `data/samples/manifest.json`、
> `data/samples/risk/manifest.json`。
