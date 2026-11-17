"""性能实测（单独运行，跑前重启 app 以获得 OCR 冷启动）。

阶段：
1. 文本层上传+解析：20 份 × 3 次
2. OCR 冷启动：重启后第 1 份扫描件
3. OCR 热启动：5 份 × 3 次
4. /api/review 串行：30 次
5. 并发 1 / 5 / 10：各 20 个请求
6. 报告 docx/pdf：首次生成 + 二次下载（幂等）
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_lib as q

SAMPLES = q.ROOT / "data" / "samples"
TEXT = [f"bid-{i:03d}.{ext}" for i, ext in [(1, "docx"), (2, "docx"), (3, "docx"), (4, "pdf"), (5, "pdf"),
                                            (6, "txt"), (7, "txt"), (8, "docx"), (9, "txt"), (10, "docx"),
                                            (11, "pdf"), (12, "txt"), (13, "docx"), (14, "txt"), (15, "docx"),
                                            (16, "docx"), (17, "pdf"), (18, "txt"), (19, "docx"), (20, "txt")]]
SCANS = [f"scan-{i:03d}.pdf" for i in range(1, 6)]


def main() -> int:
    q.ensure_dirs()
    raw: dict = {"started_at": q.now(), "base": q.BASE, "text": [], "ocr_cold": None, "ocr_warm": [],
                 "review_seq": [], "concurrency": {}, "report": [], "env": {}}
    health = q.get_json("/api/health")
    raw["env"] = {"uptime_seconds": health.get("uptime_seconds"), "started_at": health.get("started_at"),
                  "version": health.get("version"), "container": "bid-review", "host": "Ryzen 7 7735H / 16GB / Win11"}

    # 1. 文本层
    for rep in range(3):
        for name in TEXT:
            path = SAMPLES / name
            up = q.upload(path, name=f"{q.PREFIX}perf-text-{rep}-{name}")
            raw["text"].append({"rep": rep, "file": name, "ms": up["ms"], "status": up["status"],
                                "parse_status": (up["body"] or {}).get("parse_status"),
                                "doc_id": (up["body"] or {}).get("doc_id")})
            print(f"TEXT rep{rep} {name:<14} {up['ms']:.0f}ms")

    text_ms = [r["ms"] for r in raw["text"] if r["status"] == 200]
    raw["text_summary"] = q.perf_summary(text_ms)

    # 2. OCR 冷启动（重启后第一次）
    up = q.upload(SAMPLES / SCANS[0], name=f"{q.PREFIX}perf-ocr-cold-{SCANS[0]}", timeout=300)
    raw["ocr_cold"] = {"file": SCANS[0], "ms": up["ms"], "status": up["status"],
                       "parse_status": (up["body"] or {}).get("parse_status"),
                       "ocr_pages": len((up["body"] or {}).get("ocr_pages") or []),
                       "doc_id": (up["body"] or {}).get("doc_id")}
    print(f"OCR COLD {SCANS[0]} {up['ms']:.0f}ms")

    # 3. OCR 热启动
    for rep in range(3):
        for name in SCANS:
            up = q.upload(SAMPLES / name, name=f"{q.PREFIX}perf-ocr-{rep}-{name}", timeout=300)
            raw["ocr_warm"].append({"rep": rep, "file": name, "ms": up["ms"], "status": up["status"],
                                    "parse_status": (up["body"] or {}).get("parse_status"),
                                    "ocr_pages": len((up["body"] or {}).get("ocr_pages") or []),
                                    "doc_id": (up["body"] or {}).get("doc_id")})
            print(f"OCR rep{rep} {name:<14} {up['ms']:.0f}ms")
    raw["ocr_warm_summary"] = q.perf_summary([r["ms"] for r in raw["ocr_warm"] if r["status"] == 200])
    raw["ocr_cold_summary"] = q.perf_summary([raw["ocr_cold"]["ms"]])

    # 评审用文档：第一份 bid-001 文本上传
    bench_doc = next(r["doc_id"] for r in raw["text"] if r["file"] == "bid-001.docx" and r["status"] == 200)

    # 4. 串行评审
    review_ids = []
    for i in range(30):
        rv = q.review(bench_doc, "profile-a")
        raw["review_seq"].append({"i": i, "ms": rv["ms"], "status": rv["status"],
                                  "review_id": (rv["body"] or {}).get("review_id")})
        if rv["status"] == 200:
            review_ids.append((rv["body"] or {}).get("review_id"))
        print(f"REVIEW {i+1:02d} {rv['ms']:.0f}ms")
    raw["review_seq_summary"] = q.perf_summary([r["ms"] for r in raw["review_seq"]])
    raw["review_error_rate"] = sum(1 for r in raw["review_seq"] if r["status"] != 200) / len(raw["review_seq"])

    # 5. 并发
    for workers in (1, 5, 10):
        n = {1: 20, 5: 50, 10: 100}[workers]
        records = []
        t0 = time.perf_counter()

        def one(_i: int) -> dict:
            t = time.perf_counter()
            rv = q.review(bench_doc, "profile-a")
            return {"ms": (time.perf_counter() - t) * 1000, "status": rv["status"]}

        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(one, i) for i in range(n)]
            for f in as_completed(futures):
                records.append(f.result())
        wall = (time.perf_counter() - t0) * 1000
        errs = sum(1 for r in records if r["status"] != 200)
        raw["concurrency"][str(workers)] = {
            "requests": n, "workers": workers, "wall_ms": round(wall, 1),
            "throughput_rps": round(n / (wall / 1000), 2),
            "error_rate": round(errs / n, 4),
            "summary": q.perf_summary([r["ms"] for r in records]),
        }
        print(f"CONC {workers} n={n} p95={raw['concurrency'][str(workers)]['summary']['p95']}ms err={errs}/{n}")

    # 6. 报告
    for rid in review_ids[:6]:
        for fmt in ("docx", "pdf"):
            r1 = q.get(f"/api/report/{rid}?format={fmt}")
            r2 = q.get(f"/api/report/{rid}?format={fmt}")
            raw["report"].append({"review_id": rid, "fmt": fmt, "first_ms": round(r1.elapsed.total_seconds() * 1000, 1),
                                  "second_ms": round(r2.elapsed.total_seconds() * 1000, 1),
                                  "status": r1.status_code, "size": len(r1.content),
                                  "same": r1.content == r2.content})
            print(f"REPORT {rid} {fmt} first={raw['report'][-1]['first_ms']}ms second={raw['report'][-1]['second_ms']}ms")
    for fmt in ("docx", "pdf"):
        vals = [r["first_ms"] for r in raw["report"] if r["fmt"] == fmt and r["status"] == 200]
        cached = [r["second_ms"] for r in raw["report"] if r["fmt"] == fmt and r["status"] == 200]
        raw[f"report_{fmt}_summary"] = q.perf_summary(vals)
        raw[f"report_{fmt}_cached_summary"] = q.perf_summary(cached)

    raw["finished_at"] = q.now()
    q.jdump(q.PERF / "perf-raw.json", raw)

    # CSV 平铺
    with (q.PERF / "perf-samples.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["stage", "file", "rep", "ms", "status", "parse_status", "ocr_pages"])
        for r in raw["text"]:
            w.writerow(["text", r["file"], r["rep"], r["ms"], r["status"], r["parse_status"], ""])
        if raw["ocr_cold"]:
            w.writerow(["ocr_cold", raw["ocr_cold"]["file"], 0, raw["ocr_cold"]["ms"], raw["ocr_cold"]["status"],
                        raw["ocr_cold"]["parse_status"], raw["ocr_cold"]["ocr_pages"]])
        for r in raw["ocr_warm"]:
            w.writerow(["ocr_warm", r["file"], r["rep"], r["ms"], r["status"], r["parse_status"], r["ocr_pages"]])
        for r in raw["review_seq"]:
            w.writerow(["review_seq", "bid-001.docx", r["i"], r["ms"], r["status"], "", ""])
        for workers, d in raw["concurrency"].items():
            w.writerow(["concurrency", f"workers={workers}", "", d["summary"]["p50"], "", "", ""])
        for r in raw["report"]:
            w.writerow(["report_" + r["fmt"], r["review_id"], "", r["first_ms"], r["status"], "", ""])
            w.writerow(["report_cached_" + r["fmt"], r["review_id"], "", r["second_ms"], r["status"], "", ""])

    print(json.dumps({k: v for k, v in raw.items() if k.endswith("summary") or k in ("concurrency", "env")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
