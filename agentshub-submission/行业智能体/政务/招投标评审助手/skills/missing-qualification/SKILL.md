---
name: missing-qualification
description: 资格性审查时，按 R01–R10 逐项核验已提供、效力不足、缺失三态，不判断证件真伪。
allowed-tools:
  - parse_tender
  - check_qualification
  - locate_span
tags:
  - 招投标评审
  - 资格性
---

# missing-qualification

## When to use

进行资格性审查时；用户问“缺什么材料 / 资格性是否满足 / 为什么说缺失”时。
必须先完成解析，再逐项核验，不得直接根据文件名或目录猜测。

## Inputs

- `doc_id`：已解析文档 ID（由页面上传或 `list_documents` / `parse_attachment` 获得）
- `rule_ids`：可选，限定 R01–R10 中的某几项

## Outputs

- 三态计数：`provided` / `insufficient` / `missing`
- 逐项明细：`rule_id` / `item` / `state` / `page` / `quote` / `note`
- 一句结论式提示：如「存在 N 项需人工复核的资格材料」
- 固定提示：**文本核验不替代原件核验**

## Hard rules

1. 先调用 `parse_tender(doc_id)` 确认解析状态；`parse_status=failed` 时停止核验并说明原因。
2. 三态判定只认 `check_qualification(doc_id)` 的返回；不得自行把“提到”当成“已提供”，也不得把“没提到”编造成有页码。
3. `missing` 项没有 `quote` 就写「全文未检出」，不得虚构页码或原文。
4. 不判断证件真伪、不核验业绩真实性；缺失只能建议“澄清或补充材料”，不得说“资格审查不通过 / 废标”。
5. 资质类问题只在资格性核验里报告，不重复塞进风险清单。
6. 输出逐项带 `page` / `quote`（有则带），并保留「文本核验不替代原件核验」。
