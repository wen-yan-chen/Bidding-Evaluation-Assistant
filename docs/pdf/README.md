# PDF 文档

由 `docs/` 下四份 Markdown 生成，适合打印/发送。

| 文件 | 内容 |
| --- | --- |
| `招投标评审助手-文档合集.pdf` | 封面 + 目录 + 四份文档，23 页 |
| `开发说明.pdf` | 开发/维护 |
| `数据说明.pdf` | 样本、规则、标注、N01–N10 |
| `评审说明.pdf` | 重评方法、10/10 结果、局限 |
| `使用说明.pdf` | 页面操作、报告、常见问题 |

重新生成：

```powershell
python tools\build_docs_pdf.py
```

脚本使用 Windows 宋体/黑体与 reportlab，保留 Markdown 标题、表格、代码块和 `screenshots/` 图片。
