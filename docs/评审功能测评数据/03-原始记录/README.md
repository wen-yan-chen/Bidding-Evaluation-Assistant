# 03-原始记录

本目录保留 2026-11-16 评测的原始产物，用于追溯，不是最终结论。

| 路径 | 内容 |
| --- | --- |
| `raw/00-environment.json` | 环境、git HEAD、镜像版本 |
| `raw/01-…`–`raw/06-…` | 规则、溯源、风险、解析、报告、冒烟 |
| `raw/10-run_accuracy.log`、`accuracy-*.json` | 25 份解析 + 15 风险 + 50 次评审原始记录 |
| `raw/11-run_edges.log`、`edges-raw.json` | 评分边界、重复性、幂等 |
| `raw/16-run_boundary.log`、`boundary-raw.json` | 空白页/低清/旋转/重复页 |
| `raw/17-pytest.txt`、`30-pytest-after-phase1.txt` | 当时 pytest 记录 |
| `raw/26-qual-semantics.log` | 资格性三态语义边界 |
| `raw/fields.csv`、`reviews.csv`、`qualification.csv`、`risks.csv`、`scores-by-doc.csv` | 逐字段/逐项/逐规则明细 |
| `perf/` | 冷启动、UI、Docker 资源性能记录 |

> 最终重评结论以 [`../01-评分重评/`](../01-评分重评/) 与 [`../../评审说明.md`](../../评审说明.md) 为准。
> 早期日志里出现的 `54 passed`、8/8、14/16 等数字是当时中间状态，不作为最终口径。
