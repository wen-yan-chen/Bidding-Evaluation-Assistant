# data/ — 模拟数据与运行时产物

全部为**自造数据**，不含任何真实招投标信息（合规红线）。

```text
data/
├── meta/milestones.json   # 里程碑与阶段交付清单（页面/文档同源）✅
├── uploads/               # 运行时上传件（git 忽略）✅
├── parsed/                # 解析结果 JSON（运行时生成，git 忽略）✅ D2
├── samples/               # 投标文件样本 + manifest.json（标准答案）✅ 15 份（含 5 份扫描件）
│   └── boundary/          # 边界样本：空白页 / 低分辨率 / 旋转 90° ✅ D3
├── rules/rules.yaml       # 40 条规则（四类各 10 条，依据三态）✅ D4
├── scoring/               # D5：评分细则 YAML（至少两套，用于"换细则"演示）
├── labels/                # D6/D9：人工标注（风险条目、专家分、核验结论）
├── review/                # D7：评审结果落盘（JSON）
└── predictions/           # D9：批量评测输出（git 忽略）
```

命名约定：`{类型}-{序号}.{ext}`，例如 `bid-013.pdf`；标注与被标注文件同名 + `.labels.json`，保证可复算。

## D2 样本清单（10 份，全部虚构）

| 文件 | 格式 | 说明 |
| --- | --- | --- |
| `bid-001.docx` | docx | 货物类，含报价明细表格 |
| `bid-002.docx` | docx | 服务类，纯段落 |
| `bid-003.docx` | docx | 工程类，工期 180 日历天 |
| `bid-004.pdf` | pdf | 由 docx 转制，带文本层，3 页 |
| `bid-005.pdf` | pdf | 服务类，工期 12 个月 |
| `bid-006.txt` | txt | **GB18030 编码**，验证编码嗅探 |
| `bid-007.txt` | txt | 长文本（>1100 字），验证页码估算 |
| `bid-008.docx` | docx | **边界：缺报价与工期**（应判"未提供"，不得编造） |
| `bid-009.txt` | txt | **边界：报价只写 ￥968,000.00 无单位；工期"6 个月"** |
| `bid-010.docx` | docx | 工程类长文档，含表格 |

### D3 扫描件与边界样本

| 文件 | 说明 |
| --- | --- |
| `scan-001..005.pdf` | 5 份**无文本层**扫描件（docx→pdf→逐页图像→图像 PDF，200 DPI，约 0.6 MB/份） |
| `boundary/blank-page.pdf` | 第 1 页空白 + 第 2 页正常扫描，验证空白页降级 |
| `boundary/lowres-scan.pdf` | 原图缩到 35% 再放大，模拟低分辨率，允许少抽字段但不得编造 |
| `boundary/rotated-scan.pdf` | 图像旋转 90°，允许识别失败，必须如实降级 |

`manifest.json` 是人工标准答案（15 条、88 个字段），扫描件条目带 `"ocr": true`，
`tools/eval_parse.py` 以它为唯一口径并按"文本层 / 扫描件"分列复算。
重新生成：`python tools/make_samples.py`（`--no-pdf` 可在没有 LibreOffice 的环境跳过 pdf）。
