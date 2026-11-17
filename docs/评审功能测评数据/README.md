# 评测数据索引

> 本目录只放评测产物，不放被测代码；所有样本均为自造虚构数据。
> 结论见 [`../评审说明.md`](../评审说明.md)，数据口径见 [`../数据说明.md`](../数据说明.md)。

## 一、当前有效数据

| 路径 | 内容 |
| --- | --- |
| `老师参考评分回收/评分表_N01-N08.xlsx` | N01–N08 重评后的参考评分（B3 严格口径） |
| `老师参考评分回收/评分意见_N01-N08.docx` | N01–N08 逐份评分依据 |
| `老师参考评分回收/评分表_N09-N10.xlsx` | N09–N10 参考评分 |
| `老师参考评分回收/评分意见_N09-N10.docx` | N09–N10 逐份依据 |
| `资格性标注材料/` | 25 份 × R01–R10 = 250 条三态标注（A/B 表、终稿、一致性报告） |
| `重评10份-calibrated评测.txt` | `eval_calibrated.py --strict` 输出：旧 4/10，校准 10/10 |
| `重评10份-scoring评测.txt` | `eval_scoring.py --strict` 输出：10/10，平均偏差 0.00 |
| `raw/` | 解析、评分、风险、报告的原始 CSV/日志 |
| `perf/` | 性能记录 |
| `scripts/` | 评测脚本/辅助脚本 |

## 二、已删除的第一批数据

第一批 S01–S10 的评分参数不准确，已不作为任何结论依据；相关学生评审材料、
旧盲评包、旧汇总与中间 CSV 已从仓库移除（git 历史可追溯）。

## 三、复算

```powershell
python tools\eval_calibrated.py --strict
python tools\eval_scoring.py --strict
python tools\eval_qualification.py --strict --require-full
python tools\eval_parse.py --strict
python tools\eval_risks.py --strict
```
