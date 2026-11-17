"""冷启动补测：重启后第一次 OCR 的耗时（run 2/3）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as q


def main() -> int:
    run = sys.argv[1] if len(sys.argv) > 1 else "2"
    src = q.ROOT / "data" / "samples" / "scan-001.pdf"
    up = q.upload(src, name=f"{q.PREFIX}cold{run}-scan-001.pdf", timeout=300)
    rec = {"run": run, "ms": round(up["ms"], 1), "status": up["status"],
           "parse_status": (up["body"] or {}).get("parse_status"),
           "ocr_pages": len((up["body"] or {}).get("ocr_pages") or []),
           "doc_id": (up["body"] or {}).get("doc_id"), "at": q.now()}
    path = q.PERF / "cold-extra.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    data.append(rec)
    q.jdump(path, data)
    print(json.dumps(rec, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
