# 评测数据索引

> 本目录只放评测产物，不放被测代码；所有样本均为自造虚构数据。
> 结论见 [`../评审说明.md`](../评审说明.md)，数据口径见 [`../数据说明.md`](../数据说明.md)。

## 一、目录

| 目录/文件 | 内容 |
| --- | --- |
| `01-评分重评/` | N01–N10 重评评分表、逐份意见、`eval_calibrated`/`eval_scoring` 输出 |
| `02-资格性标注/` | 25 份 × R01–R10 = 250 条三态标注（A/B 表、终稿、一致性报告） |
| `03-原始记录/` | `raw/` 解析/评分/风险/报告 CSV 与日志；`perf/` 性能记录 |
| `04-评测脚本/` | 本次测评使用的脚本（归档，不随主程序运行） |

## 二、01-评分重评

| 文件 | 内容 |
| --- | --- |
| `评分表_N01-N08.xlsx` | N01–N08 重评参考评分（B3 严格口径） |
| `评分意见_N01-N08.docx` | N01–N08 逐份评分依据 |
| `评分表_N09-N10.xlsx` | N09–N10 参考评分 |
| `评分意见_N09-N10.docx` | N09–N10 逐份依据 |
| `重评10份-calibrated评测.txt` | 旧 4/10，校准 10/10 |
| `重评10份-scoring评测.txt` | 10/10，平均偏差 0.00 |

## 三、已删除

第一批 S01–S10 的评分参数不准确，已不作为任何结论依据；相关学生评审材料、
旧盲评包、旧汇总与中间 CSV 已从仓库移除（git 历史可追溯）。

## 四、复算

```powershell
python tools\eval_calibrated.py --strict
python tools\eval_scoring.py --strict
python tools\eval_qualification.py --strict --require-full
python tools\eval_parse.py --strict
python tools\eval_risks.py --strict
```
