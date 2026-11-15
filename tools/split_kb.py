"""把知识库文档拆成「一条规则一个文件」，解决平台按大小切分导致多规则混块的问题。

背景（D6 实测）：把 40 条规则的 22 KB 单文件上传后，平台只切出 **8 个分片**（约 2.8 KB/块），
一条规则被切碎、多条规则混在一块，检索时容易串号。拆成 40 个文件后，每个文件至少一个分片，
配合平台的多文件上传即可保证「一块一条规则」。

用法：
  python tools/split_kb.py            # 生成 knowledge/rules/R01.md … R40.md + index.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB = ROOT / "knowledge"
SOURCE = KB / "rules-full.md"
OUT = KB / "rules"

HEADER = """# {title}

> 规则编号：{rule_id}　｜　来源：`data/rules/rules.yaml`（自动生成，勿手改）
> 依据状态：{basis_status}　｜　检测方式：{detect}

{body}
"""


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    blocks = re.split(r"^## ", text, flags=re.M)[1:]
    if not blocks:
        print("未找到 `## Rxx` 小节，检查 rules-full.md")
        return 1

    if OUT.exists():
        for path in OUT.glob("*.md"):
            path.unlink()
    OUT.mkdir(parents=True, exist_ok=True)

    index: list[dict] = []
    for block in blocks:
        first_line, _, body = block.partition("\n")
        match = re.match(r"(R\d{2})\s+(.*)", first_line.strip())
        if not match:
            continue
        rule_id, title = match.group(1), match.group(2).strip()
        basis = re.search(r"- 依据状态：(\w+)", body)
        detect = re.search(r"检测方式：([^\n｜]+)", body)
        content = HEADER.format(
            title=f"{rule_id} {title}",
            rule_id=rule_id,
            basis_status=basis.group(1) if basis else "pending",
            detect=detect.group(1).strip() if detect else "",
            body=body.strip(),
        )
        path = OUT / f"{rule_id}.md"
        path.write_text(content + "\n", encoding="utf-8")
        index.append(
            {
                "rule_id": rule_id,
                "title": title,
                "file": f"rules/{rule_id}.md",
                "chars": len(content),
            }
        )

    (OUT / "index.json").write_text(
        json.dumps({"count": len(index), "items": index}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已拆分 {len(index)} 条规则 → {OUT}（一文件一规则，便于平台一块一条切分）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
