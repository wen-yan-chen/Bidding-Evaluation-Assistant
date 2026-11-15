# docs/reports — 报告样张

由 id-001.docx（综合评分法 profile-a）生成的真实报告，用于交付展示与评审抽查。

| 文件 | 内容 | 关键数字 |
| --- | --- | --- |
| 样例报告-bid-001-rev1.docx | 九章报告（docx） | 总分 68.0/100 ｜ 风险 0 条 ｜ 资格性 4/6 |
| 样例报告-bid-001-rev1.pdf | 同一份报告的 pdf | 双指纹 fd898ab7… / 188bf9a7… |

复现：

```bash
curl -F "file=@data/samples/bid-001.docx" http://127.0.0.1:8080/api/upload
curl -X POST -H "Content-Type: application/json" -d '{"doc_id":"<上一步>","profile_id":"profile-a"}' http://127.0.0.1:8080/api/review
curl -OJ "http://127.0.0.1:8080/api/report/<review_id>?format=docx"
curl -OJ "http://127.0.0.1:8080/api/report/<review_id>?format=pdf"
```

> 报告里的数值来自 data/reviews/<review_id>.json，可用 python tools/check_report.py --review-id <id> 复核。