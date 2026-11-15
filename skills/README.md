# skills/ — 自定义 Skill（D5 落地）

四个 Skill 各一个 zip，`SKILL.md` 只写四段（When to use / Inputs / Outputs / Hard rules），
**只放流程，不放判定逻辑**（判定在 MCP）。

| Skill | 触发时机 | 作用 |
| --- | --- | --- |
| `bid-rule-cards` | 判断某条内容是否违规前 | 按类别取规则卡，取不到不得判定 |
| `missing-qualification` | 资格性审查时 | 缺失/效力不足/已提供三态判定 |
| `risk-selfcheck` | 输出与导出之前 | 逐条核对溯源，不通过就删（降误报） |
| `summary-compiler` | 生成摘要与报告时 | 六要素摘要 + 九章报告成文 |

> D1 状态：目录占位。`agent.json` 已登记 4 个 skill 名，未上传。
