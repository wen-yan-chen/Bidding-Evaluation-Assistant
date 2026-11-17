"""清理本次测评创建的临时文档（QA20261116-* + smoke_test 的两份），保留原有数据。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as q

SMOKE_IDS = {"20261116-b189d094", "20261116-4efe0b58"}  # smoke_test 于 14:37/14:38 上传的 bid-001 / scan-001


def main() -> int:
    s = q.admin_login()
    overview = s.get(q.BASE + "/api/admin/overview", timeout=60).json()
    docs = overview.get("docs") or []
    targets = [d for d in docs if str(d.get("file_name", "")).startswith(q.PREFIX) or d.get("doc_id") in SMOKE_IDS]
    # 安全闸：绝不能删到非本次测评创建的文档
    bad = [d for d in targets if not (str(d.get("file_name", "")).startswith(q.PREFIX) or d.get("doc_id") in SMOKE_IDS)]
    if bad:
        raise SystemExit(f"安全检查失败，拒绝删除：{bad[:3]}")
    before = overview.get("counts")
    results = []
    for i in range(0, len(targets), 80):
        chunk = [d["doc_id"] for d in targets[i:i + 80]]
        r = s.post(q.BASE + "/api/admin/batch-delete", json={"doc_ids": chunk}, timeout=300)
        results.append({"chunk": i // 80, "requested": len(chunk), "status": r.status_code,
                        "body": r.text[:500]})
        print(f"chunk {i//80}: {len(chunk)} docs -> HTTP {r.status_code}")
    after = s.get(q.BASE + "/api/admin/overview", timeout=60).json()
    out = {"before": before, "targets": len(targets), "results": results, "after": after.get("counts"),
           "remaining_docs": [{"doc_id": d["doc_id"], "file_name": d["file_name"]} for d in after.get("docs") or []],
           "remaining_targets": [d["doc_id"] for d in after.get("docs") or []
                                 if str(d.get("file_name", "")).startswith(q.PREFIX) or d.get("doc_id") in SMOKE_IDS]}
    q.jdump(q.RAW / "cleanup.json", out)
    print(json.dumps({k: out[k] for k in ("before", "targets", "after", "remaining_targets")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
