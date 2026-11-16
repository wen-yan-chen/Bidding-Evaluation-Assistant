# mcps/ — MCP 工具服务（阶段 2）

FastMCP 单文件服务 `bid_review_mcp.py`，`transport=sse`，容器内端口 8765；已实现 8 个工具。

| 工具 | 作用 | 关键返回 |
| --- | --- | --- |
| `parse_tender` | 解析招标/投标文件 | 8 字段（含资质/业绩清单）+ `page` + `quote` + 条款切分 |
| `check_qualification` | 资格性审查 | 逐项 `provided/missing/insufficient` |
| `score_item` | 按细则算分 | 分项得分 + 扣分理由 + 依据 |
| `scan_risks` | 40 条规则扫描 | `rule_id/level/page/span/quote/basis_status` |
| `locate_span` | quote 反查页码偏移 | `page/char_start/char_end` |
| `export_report` | 导出 docx/pdf | 文件路径 |
| `list_documents` | 列出最近解析文档 | `doc_id/file_name/pages/parse_status` |
| `parse_attachment` | 解析聊天附件 s3 路径 | `doc_id` + 字段 |

规则覆盖：**40 = 27 自动 + 10 人工 + 3 未实现**；R25/R32/R33 需多家投标人比价，单份不可判定。

工程约束（手册 §5.6）：单一职责、入参出参可序列化、错误返回 `{"error": ...}` 不抛异常、
幂等、单次调用 ≤ 60s、不访问外网。

