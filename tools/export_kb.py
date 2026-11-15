"""把规则库 YAML 导出成知识库文档（一块一条规则），并写出指纹清单。

为什么必须"同源自动导出"：规则库给人读（YAML/代码）、给平台检索（markdown），
两处手写必然漂移；一旦漂移，评审问"R12 的依据是什么"时，知识库和扫描结果会互相打架。

产物：
  knowledge/rules-full.md   40 块（## Rxx 开头），供平台按标题切分
  knowledge/manifest.json   指纹 / 条数 / 生成时间 / 源文件，供 validate_rules.py 与报告引用

用法：
  python tools/export_kb.py           # 导出并打印指纹
  python tools/export_kb.py --check   # 只校验现有导出是否与 YAML 一致（CI 用）
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api import rules as rules_api  # noqa: E402

KB_DIR = ROOT / "knowledge"
KB_FILE = KB_DIR / "rules-full.md"
MANIFEST = KB_DIR / "manifest.json"
CST = timezone(timedelta(hours=8))

BASIS_TEXT = {
    "verified": "已核对现行法规条号",
    "pending": "未逐条核验（输出「未检索到权威依据」）",
    "na": "经验判据，无法条依据",
}
DETECT_TEXT = {"pattern": "关键词命中（自动扫描）", "manual": "人工核对（不参与自动扫描）", "price": "报价计算（D6 实现）"}


def render(rules: list) -> str:
    digest = rules_api.rules_digest()
    lines: list[str] = [
        "# 招投标评审规则库",
        "",
        f"> 版本指纹：{digest}　条数：{len(rules)}　生成时间：{datetime.now(CST):%Y-%m-%d %H:%M}",
        "> 本文件由 `tools/export_kb.py` 从 `data/rules/rules.yaml` 自动生成，**请勿手改**；改规则请改 YAML 后重新导出。",
        "> 依据状态为 pending 的规则，输出一律为「未检索到权威依据」，不得自行补条号。",
        "",
    ]

    for rule in rules:
        lines.append(f"## {rule.id} {rule.title}")
        lines.append("")
        lines.append(f"- 类别：{rule.category}　｜　等级：{rule.level}　｜　检测方式：{DETECT_TEXT.get(rule.detect, rule.detect)}")
        lines.append(f"- 判定条件：{rule.condition}")
        if rule.patterns:
            lines.append(f"- 命中特征：{'、'.join('`' + p + '`' for p in rule.patterns)}")
        lines.append(f"- 依据状态：{rule.basis_status}（{BASIS_TEXT.get(rule.basis_status, rule.basis_status)}）")
        lines.append(f"- 法规依据：{rule.legal_basis}")
        if rule.basis_note:
            lines.append(f"- 依据说明：{rule.basis_note}")
        if rule.compliant:
            lines.append(f"- 合规定式（出现以下表述时不得报本条）：{'；'.join(rule.compliant)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="导出规则库知识库文档")
    ap.add_argument("--check", action="store_true", help="只校验，不写文件")
    args = ap.parse_args(argv)

    rules = list(rules_api.load_rules())
    digest = rules_api.rules_digest()
    content = render(rules)

    if args.check:
        if not KB_FILE.exists() or not MANIFEST.exists():
            print("[ERROR] 知识库尚未导出（缺 knowledge/rules-full.md 或 manifest.json）")
            return 1
        current = KB_FILE.read_text(encoding="utf-8")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        ok_content = current == content
        ok_digest = manifest.get("digest") == digest
        print(f"内容一致：{'是' if ok_content else '否'}｜指纹一致：{'是' if ok_digest else '否'}｜指纹 {digest}")
        if not (ok_content and ok_digest):
            print("结论：不一致，跑 python tools/export_kb.py 重新导出")
            return 1
        print("结论：一致")
        return 0

    KB_DIR.mkdir(parents=True, exist_ok=True)
    KB_FILE.write_text(content, encoding="utf-8")

    manifest = {
        "name": "bid-review-rules",
        "source": "data/rules/rules.yaml",
        "digest": digest,
        "rule_count": len(rules),
        "blocks": len(rules),
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "embedding_suggestion": "bge-m3",
        "split": "按 `## Rxx` 标题切分，一块一条规则",
        "note": "由 tools/export_kb.py 自动生成；导入平台后用 agent.json 的 index_names 指向本库。",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"已导出 {len(rules)} 条规则 → {KB_FILE}")
    print(f"指纹：{digest}（规则库与知识库必须一致，validate_rules.py 会校验）")
    print(f"文件大小：{KB_FILE.stat().st_size / 1024:.1f} KB｜块数：{len(rules)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
