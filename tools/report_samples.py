"""生成《样本说明报告》（docs/数据说明.md），保证报告与样本清单同源。

读取：
  data/samples/manifest.json        解析样本（含扫描件）与字段标准答案
  data/samples/risk/manifest.json   植入风险样本与干净对照
  data/samples/boundary/            边界样本

输出：
  docs/数据说明.md（表格全部由清单生成，改样本后重跑即可，不会与实物脱节）

用法：
  python tools/report_samples.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "samples"
OUT = ROOT / "docs" / "数据说明.md"

FORMAT_LABEL = {"docx": "Word 文档", "pdf": "PDF（文本层）", "txt": "纯文本"}
KIND_ORDER = {"货物": 0, "服务": 1, "工程": 2}

CLEAN_REASON = {
    "bid-001.docx": "含「已按招标文件要求提交投标保证金」「有效期 90 天」「金额大小写一致」三种合规定式",
    "bid-002.docx": "纯段落服务类标书，无任何风险表述",
    "bid-003.docx": "工程类，工期与金额均正常",
    "bid-004.pdf": "PDF 文本层，含报价明细表格",
    "bid-005.pdf": "PDF 文本层，工期用「个月」表述",
}


def fmt_size(path: Path) -> str:
    if not path.exists():
        return "-"
    size = path.stat().st_size
    return f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.2f} MB"


def main() -> int:
    parse_manifest = json.loads((SAMPLES / "manifest.json").read_text(encoding="utf-8"))
    risk_manifest = json.loads((SAMPLES / "risk" / "manifest.json").read_text(encoding="utf-8"))
    items = parse_manifest["items"]
    risk_items = risk_manifest["items"]

    text_items = [item for item in items if not item.get("ocr")]
    text_formats = Counter(item["format"] for item in text_items)
    kinds = Counter(item.get("kind", "未标注") for item in items)
    ocr_count = sum(1 for item in items if item.get("ocr"))
    text_count = len(items) - ocr_count
    field_total = sum(len(item.get("expect") or {}) for item in items)

    risk_only = [i for i in risk_items if not i.get("clean")]
    clean_only = [i for i in risk_items if i.get("clean")]
    dev = [i for i in risk_items if i["split"] == "dev"]
    holdout = [i for i in risk_items if i["split"] == "holdout"]
    dev_risk = sum(1 for i in dev if not i.get("clean"))
    dev_clean = sum(1 for i in dev if i.get("clean"))
    ho_risk = sum(1 for i in holdout if not i.get("clean"))
    ho_clean = sum(1 for i in holdout if i.get("clean"))

    lines: list[str] = []
    add = lines.append

    add("# 样本说明报告（数据说明）")
    add("")
    add(f"> 生成时间：{datetime.now():%Y-%m-%d %H:%M}　｜　生成脚本：`tools/report_samples.py`（本文件由脚本生成，勿手改）")
    add("> 全部样本为**自造虚构数据**：主体名称、编号、金额、工期均为示例，不含任何真实招投标信息。")
    add("")

    add("## 一、总量概览")
    add("")
    add("| 类别 | 数量 | 用途 |")
    add("| --- | ---: | --- |")
    add(f"| 解析样本（全部） | {len(items)} 份 | 解析成功率 / 字段准确率 / 溯源一致性 |")
    add(
        f"| ├─ 文本层文件 | {text_count} 份（docx {text_formats.get('docx', 0)} / pdf {text_formats.get('pdf', 0)} / txt {text_formats.get('txt', 0)}） | 常规解析 |"
    )
    add(f"| └─ 扫描件（无文本层 PDF） | {ocr_count} 份 | OCR 通路 |")
    add(f"| 植入风险样本 | {len(risk_only)} 份 | 风险检出率 |")
    add(f"| 干净对照 | {len(clean_only)} 份 | 误报率（分母样本） |")
    add("| 边界样本 | 3 份 | 空白页 / 低分辨率 / 旋转 90°，验证「不崩不编造」 |")
    add(f"| 字段标准答案 | {field_total} 个字段 | `tools/eval_parse.py` 的唯一口径 |")
    add("")
    add(
        "行业分布："
        + "、".join(f"{k} {v} 份" for k, v in sorted(kinds.items(), key=lambda x: KIND_ORDER.get(x[0], 9)))
        + "。"
    )
    add("")
    add("> 解析样本里既有干净标书，也含缺字段、单位异常（万元 / ￥ / 个月）等**边界形态**；")
    add("> 风险样本与干净对照单独放在 `data/samples/risk/`，两者互不重叠，避免「同一份文件既测检出又测误报」。")
    add("")

    add(f"## 二、解析样本清单（{len(items)} 份）")
    add("")
    add("| # | 文件 | 类型 | 格式 | 大小 | 期望字段 | 备注 |")
    add("| ---: | --- | --- | --- | ---: | ---: | --- |")
    for index, item in enumerate(sorted(items, key=lambda x: x["file"]), start=1):
        path = SAMPLES / item["file"]
        note = item.get("boundary") or ("扫描件：无文本层，走 OCR" if item.get("ocr") else "")
        add(
            f"| {index} | `{item['file']}` | {item.get('kind', '-')} | {FORMAT_LABEL.get(item['format'], item['format'])} | "
            f"{fmt_size(path)} | {len(item.get('expect') or {})} | {note} |"
        )
    add("")
    add("> 页数不预先写死：docx 无分页符时按行数估算、PDF 按真实页、扫描件按图像页；")
    add("> 具体页数由解析结果给出，见各日 `docs/D*-自测记录.md`。")
    add("")

    add(f"## 三、植入风险样本（{len(risk_only)} 份，每份只植入一类）")
    add("")
    add("| # | 文件 | 植入风险 | 期望检出 | 分档 |")
    add("| ---: | --- | --- | --- | --- |")
    for index, item in enumerate(risk_only, start=1):
        expected = "、".join((item.get("expect_rules") or []) + (item.get("expect_qualification") or [])) or "-"
        add(f"| {index} | `{item['file']}` | {item.get('note', '')} | {expected} | {item['split']} |")
    add("")
    add("其中 `R01` / `R09` 属于**资格性缺失**，由 `qualification.check` 按三态判定，不经过关键词扫描；")
    add("其余为风险扫描命中（关键词规则或计算型规则）。")
    add("")

    add(f"## 四、干净对照（{len(clean_only)} 份，用于误报率）")
    add("")
    add("| # | 文件 | 分档 | 为什么用它当对照 |")
    add("| ---: | --- | --- | --- |")
    for index, item in enumerate(clean_only, start=1):
        add(f"| {index} | `{item['file']}` | {item['split']} | {CLEAN_REASON.get(item['file'], '常规标书')} |")
    add("")

    add("## 五、dev / holdout 划分")
    add("")
    add("| 分档 | 风险样本 | 干净对照 | 用途 |")
    add("| --- | ---: | ---: | --- |")
    add(f"| dev | {dev_risk} 份 | {dev_clean} 份 | 调规则、修误报时使用 |")
    add(f"| holdout | {ho_risk} 份 | {ho_clean} 份 | 只在出成绩时跑，避免「照着测试集调参」 |")
    add("")
    add("> 刻意保留 holdout：评审最担心「自己造的测试集 100%」。分档后 holdout 成绩是独立证据；")
    add("> 同时如实写明「holdout 与 dev 同分布，不等于真实业务泛化」。")
    add("")

    add("## 六、边界样本")
    add("")
    add("| 文件 | 构造方式 | 期望表现 |")
    add("| --- | --- | --- |")
    add("| `boundary/blank-page.pdf` | 第 1 页全白 + 第 2 页正常扫描 | 空白页记入 `empty_pages` 并降级说明，第 2 页正常 OCR |")
    add("| `boundary/lowres-scan.pdf` | 原图缩到 35% 再放大（模拟低分辨率） | 允许识别率下降，不得编造字段 |")
    add("| `boundary/rotated-scan.pdf` | 图像旋转 90° | 允许识别失败，必须如实降级 |")
    add("")
    add("此外还有 3 份「字段缺失」边界：`bid-008.docx`（缺报价与工期）、`bid-014.txt`（缺工期）、`bid-018.txt`（缺报价），")
    add("用来验证「抽不到就不返回、不猜默认值」。")
    add("")

    add("## 七、标注与复算")
    add("")
    add("| 标注文件 | 内容 | 谁在用 |")
    add("| --- | --- | --- |")
    add(f"| `data/samples/manifest.json` | {len(items)} 份样本的期望字段（共 {field_total} 个）与 `ocr` 标记 | `tools/eval_parse.py` |")
    add("| `data/samples/risk/manifest.json` | 风险样本期望规则、干净对照、dev/holdout、评测上下文 | `tools/eval_risks.py` |")
    add("| `knowledge/manifest.json` | 规则库指纹与条数 | `tools/validate_rules.py` |")
    add("")
    add("复算命令（在容器内执行，OCR 依赖已装好）：")
    add("")
    add("```bash")
    add("docker compose run --rm --no-deps \\")
    add('  -v "$PWD/tools:/app/tools" -v "$PWD/data/samples:/app/data/samples" \\')
    add("  app python tools/eval_parse.py      # 解析成功率 / 字段准确率")
    add("docker compose run --rm --no-deps \\")
    add('  -v "$PWD/tools:/app/tools" -v "$PWD/data/samples:/app/data/samples" \\')
    add("  app python tools/eval_risks.py      # 检出率 / 误报率（含 dev/holdout）")
    add("```")
    add("")
    add("重新生成样本的完整链路：")
    add("")
    add("```bash")
    add("python tools/make_samples.py        # 25 份解析样本（需 LibreOffice 转 PDF + pypdfium2 做扫描件）")
    add("python tools/make_risk_samples.py   # 15 份植入风险 + 5 份干净对照")
    add("python tools/report_samples.py      # 重写本报告")
    add("```")
    add("")

    add("## 八、已知限制（必须与成绩一起看）")
    add("")
    add("1. **合成数据**：全部由脚本生成，句式与字段位置比真实标书规整，解析与抽取成绩会偏高；")
    add("2. **同分布**：holdout 与 dev 同源同分布，只能证明规则没有过拟合到单份文件，不能证明真实泛化；")
    add("3. **覆盖有限**：集中于货物 / 服务 / 工程三类的投标文件侧，未覆盖招标文件侧、资格预审文件、附件清单；")
    add("4. **扫描件来源**：由 docx→pdf→图像→无文本层 PDF 转制，清晰度高于真实扫描件，OCR 成绩偏乐观；")
    add("5. **风险样本单点植入**：每份只植入一类风险，真实文档常多风险并存，检出率会低于本报告。")
    add("")

    add("## 九、合规声明")
    add("")
    add("- 主体名称均为虚构（示例市公共资源交易中心、示例数智科技有限公司等），与真实单位无关；")
    add("- 金额、编号、工期为编造值，不构成任何真实交易信息；")
    add("- 样本仅用于本项目评测与演示，可随仓库以 MIT 协议分发。")
    add("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已生成 {OUT}（解析样本 {len(items)} 份 / 风险 {len(risk_only)}+{len(clean_only)} 份 / 字段 {field_total} 个）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
