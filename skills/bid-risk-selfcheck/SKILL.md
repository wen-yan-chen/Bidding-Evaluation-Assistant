---
name: bid-risk-selfcheck
description: 输出风险清单或报告前逐条核对溯源，不在工具命中列表的一律删除，并输出删除清单。
allowed-tools:
  - scan_risks
  - locate_span
tags:
  - 招投标评审
  - 误报治理
---

# bid-risk-selfcheck

## When to use

任何风险清单、评审结论或报告导出**之前**；用户要求“再核对一遍 / 有没有误报 / 能不能删几条”时。
目标是降误报，不是增加风险条数。

## Inputs

- `doc_id`：已解析文档 ID
- `draft_risks`：待核对的风险列表（可来自上一次对话或报告草稿）
- `draft_summary`：可选，待核对的结论摘要

## Outputs

- `kept`：保留项（`rule_id` / `level` / `page` / `quote` / `basis_status` / 一句话理由）
- `dropped`：删除项（`rule_id` / 删除原因：不在 scan_risks 命中 / 无页码 / 无原文 / 仅 manual / 命中合规定式）
- 一行统计：保留 N 条、删除 M 条；如有删除，列出 drop 清单

## Hard rules

1. 逐条对照 `scan_risks(doc_id)` 的实际命中；**不在命中列表里的一律删除**，不得因为“看起来像”而保留。
2. 每条保留项必须有 `page` + `quote`；缺任一条件就删除，或对 `detect=manual` 的规则标注“需人工核对”，不得估页码。
3. 需要确认原文位置时调用 `locate_span(doc_id, quote)`；找不到就如实说找不到。
4. 依据三态必须匹配：`verified` 原样引用；`pending` 写「未检索到权威依据」；`na` 写「经验判据，无法条依据」。
5. 删除“中标 / 废标 / 资格审查不通过”等结论性措辞，改为“疑似 / 建议复核”。
6. 输出 drop 清单与数量，便于复核；不得静默删除。
