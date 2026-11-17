---
name: bid-rule-cards
description: 判断某条投标内容是否违反审查规则前，按类别取规则卡；取不到规则卡不得判定。
allowed-tools:
  - knowledge_base_search
  - scan_risks
  - locate_span
tags:
  - 招投标评审
  - 规则卡
---

# bid-rule-cards

## When to use

需要判断某一条投标文件内容是否违反审查规则时，**先**取对应类别的规则卡，再进入判定；
用户问“这条违反哪条规则 / 依据是什么”时，也先取规则卡，不得凭记忆回答。

取不到规则卡时，明确说“未检索到该规则卡”，不得自行发明判定条件。

## Inputs

- `category`：资质门槛 / 废标条款 / 围标串标 / 报价合规（一次只取一类）
- `rule_ids`：可选，指定规则编号（如 R12、R17）
- `clause_text` 或 `quote`：可选，待判断的原文片段

## Outputs

每张规则卡输出以下字段：

- `rule_id` / `title` / `level`
- `detect`：pattern / price / manual
- 判定条件
- 常见表述
- 合规定式（哪些写法**不算**问题）
- 已知误报形态
- `legal_basis` / `basis_status`

## Hard rules

1. 只使用 `knowledge_base_search` 检索到的规则卡；检索不到就如实说，不得补条号、文号、文件名。
2. 实际比对必须调用 `scan_risks(doc_id)`，不得自己逐字比对文本后新增或推翻结论。
3. 一次只取一类规则，禁止跨条款推理；`detect=manual` 的规则只提示“需人工核对”，不自动判定。
4. `basis_status=verified` 原样引用依据；`pending` 一律输出「未检索到权威依据」；`na` 输出「经验判据，无法条依据」。
5. 不输出“中标 / 废标 / 资格审查不通过”等结论性措辞。
