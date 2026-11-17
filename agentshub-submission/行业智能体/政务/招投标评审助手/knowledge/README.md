# knowledge/ — 规则库资产

- `rules-full.md`：40 条规则，一块一条（`## Rxx`），由 `tools/export_kb.py` 从 `rules.yaml` 自动导出；
- `manifest.json`：规则条数、指纹、生成时间；只用于核对，不是平台索引。

导入方法：

1. 在 Nexent 知识库中上传 `rules-full.md`，按标题/块切分；
2. 得到新索引 ID 后，替换 `agent.json` 中
   `KnowledgeBaseSearchTool.params.index_names` 的 `4-5897...`；
3. 重新导入 `agent.json`。

`basis_status=pending` 的规则运行期只输出「未检索到权威依据」，不补条号。
