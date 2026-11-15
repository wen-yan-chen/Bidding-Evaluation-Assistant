# data/ — 模拟数据与运行时产物

全部为**自造数据**，不含任何真实招投标信息（合规红线）。

```text
data/
├── meta/milestones.json   # 里程碑与阶段交付清单（页面/文档同源）✅
├── uploads/               # 运行时上传件（git 忽略）✅
├── parsed/                # 解析结果 JSON（运行时生成，git 忽略）✅ D2
├── samples/               # 投标文件样本 + manifest.json（标准答案）✅ D2 10 份
│   └── boundary/          # D3：边界样本（跨页、无编号、低质量扫描）
├── rules/                 # D4：40 条规则 YAML（资质/废标/围标/报价 各 10 条）
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

`manifest.json` 是人工标准答案（58 个字段），`tools/eval_parse.py` 以它为唯一口径复算指标。
重新生成：`python tools/make_samples.py`（`--no-pdf` 可在没有 LibreOffice 的环境跳过 pdf）。
