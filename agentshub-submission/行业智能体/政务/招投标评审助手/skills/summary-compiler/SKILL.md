---
name: summary-compiler
description: 生成评审摘要或报告时，只用工具返回的数字组织六要素摘要与九章报告，并追加免责声明。
allowed-tools:
  - parse_tender
  - check_qualification
  - score_item
  - scan_risks
  - export_report
tags:
  - 招投标评审
  - 报告成文
---

# summary-compiler

## When to use

生成评审摘要、评审报告或导出 docx/pdf 之前；用户要求“汇总 / 成文 / 出报告 / 给我一段结论”时。
只组织语言与结构，不重新算分、不新增判定。

## Inputs

- `doc_id`：已解析文档 ID
- `review_id`：已有评审编号（可选；没有则先触发评审）
- `profile_id`：评分细则 ID（可选，默认当前评审使用的细则）
- 已获得的工具结果：`parse_tender` / `check_qualification` / `score_item` / `scan_risks`

## Outputs

- 3–5 行结论摘要：总分 / 满分、资格性三态、高风险条数、所用细则与指纹
- 合同六要素：标的 / 金额 / 工期 / 付款 / 违约 / 争议解决（抽不到写“未约定”）
- 九章报告结构：封面与文档信息、评审依据与口径、项目与投标人、资格性核验、分项评分、风险清单、合同摘要、结论与建议、免责声明
- 双指纹：`profile.digest` + `rule_digest`
- 结尾固定追加免责声明原文

## Hard rules

1. 所有数字只来自 `score_item` / `check_qualification` / `scan_risks` / 已有报告 JSON；不得自算、不得四舍五入改写、不得写示例分数。
2. 合同要素缺失写“未约定”，不得猜测；字段值必须带来源页码或原文片段。
3. 风险按等级（高→中→低）、同等级按页码排序；`detect=manual` 的规则只提示人工核对。
4. 导出报告调用 `export_report(review_id, format)`；同一 `review_id` 重复导出是幂等的，不要手工改报告文件。
5. 不输出“中标 / 废标 / 资格审查不通过”等最终结论；只写“疑似 / 建议复核 / 建议补充材料”。
6. 每次回答结尾固定追加，且不得改写：
   `AI 辅助评审结果，最终以评标委员会评审结论为准`
