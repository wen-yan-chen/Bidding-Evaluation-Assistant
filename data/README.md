# data/ — 模拟数据与运行时产物

全部为**自造数据**，不含任何真实招投标信息（合规红线）。

```text
data/
├── meta/milestones.json   # 里程碑与 D1 交付清单（页面/文档同源）✅ D1
├── uploads/               # 运行时上传件（git 忽略）✅ D1 建目录
├── samples/               # D2：20 份投标文件（docx/pdf/txt，含 5 份扫描件）
│   └── boundary/          # D3：边界样本（跨页、无编号、低质量扫描）
├── rules/                 # D4：40 条规则 YAML（资质/废标/围标/报价 各 10 条）
├── scoring/               # D5：评分细则 YAML（至少两套，用于"换细则"演示）
├── labels/                # D6/D9：人工标注（风险条目、专家分、核验结论）
├── review/                # D7：评审结果落盘（JSON）
└── predictions/           # D9：批量评测输出（git 忽略）
```

命名约定：`{类型}-{序号}-{版本}.{ext}`，例如 `bid-013-v1.pdf`；
标注文件与被标注文件同名 + `.labels.json`，保证可复算。

> D1 状态：只有 `meta/` 与空目录 `uploads/`。样本 D2 起生成。
