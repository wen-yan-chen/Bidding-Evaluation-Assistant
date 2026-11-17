"""UI 测试夹具：创建一份“只有解析结果、没有上传原件”的临时文档并评审。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as q

TEXT = """项目名称：测评无原件项目
项目编号：QA-2026-NORAW
采购人：测评采购人
投标人：测评投标人
投标报价：人民币 1,286,000.00 元
工期：90 日历天
最高投标限价：人民币 2,000,000.00 元
技术方案：技术路线与总体架构。
实施方案：实施计划与进度计划。
质量保证措施：质量管理与质量控制。
应急预案：应急保障与安全保障。
类似项目业绩：同类项目合同业绩。
项目负责人：项目经理。
售后服务：售后服务与质保期。
"""


def main() -> int:
    q.ensure_dirs()
    path = q.RAW / "QA20261116-noraw.txt"
    path.write_text(TEXT, encoding="utf-8")
    up = q.upload(path, name="QA20261116-noraw.txt")
    if up["status"] != 200:
        print("upload failed", up)
        return 1
    doc_id = up["body"]["doc_id"]
    rv = q.review(doc_id, "profile-a")
    review_id = (rv["body"] or {}).get("review_id")
    # 模拟历史/测试数据：只有解析结果，没有上传原件
    raw = q.ROOT / "data" / "uploads" / f"{doc_id}.txt"
    removed = False
    if raw.exists():
        os.remove(raw)
        removed = True
    fixtures = {"noraw_doc_id": doc_id, "noraw_review_id": review_id, "raw_removed": removed,
                "upload_ms": up["ms"], "review_ms": rv["ms"]}
    q.jdump(q.RAW / "ui-fixtures.json", fixtures)
    print(json.dumps(fixtures, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
