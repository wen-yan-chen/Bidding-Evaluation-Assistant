"""OCR 通道：把"没有文本层"的 PDF 页变成可分析文本（D3）。

选型：`rapidocr-onnxruntime==1.2.3`（模型随 wheel 内置，离线可用）+ `pypdfium2` 渲染页面。
不用 PyMuPDF：它是 AGPL-3.0，与本项目 MIT 冲突。

三条工程约束：
1. **懒加载**：首次调用才 import/初始化引擎，避免拖慢服务启动（约 1–2s）；
2. **不穿透异常**：识别失败返回 `{"text": "", "error": ...}`，由解析器决定降级，不让 500 冒到前端；
3. **不编造**：置信度低于阈值的行直接丢弃，宁可少识别，也不给下游喂噪声。
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

DPI = int(os.getenv("OCR_DPI", "200"))
MIN_CONF = float(os.getenv("OCR_MIN_CONF", "0.30"))


def available() -> bool:
    """依赖是否齐全（页面会据此提示"OCR 可用/不可用"）。"""
    try:
        import pypdfium2  # noqa: F401
        import rapidocr_onnxruntime  # noqa: F401

        return True
    except Exception:
        return False


@lru_cache(maxsize=1)
def _engine() -> Any:
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


def _sort_reading_order(items: list) -> list:
    """按"先上后下、同一行从左到右"排序；OCR 返回的框顺序不保证是阅读顺序。"""

    def key(item: Any) -> tuple[float, float]:
        box = item[0]
        ys = [point[1] for point in box]
        xs = [point[0] for point in box]
        return (round(min(ys) / 12), min(xs))

    return sorted(items, key=key)


def ocr_pdf_page(blob: bytes, page_index: int) -> dict[str, Any]:
    """识别 PDF 的某一页（0 基）。返回 {text, lines, low_conf, error}。"""
    try:
        import pypdfium2 as pdfium
    except Exception as exc:  # 依赖缺失
        return {"text": "", "lines": 0, "low_conf": 0, "error": f"pypdfium2 不可用：{exc}"}

    try:
        pdf = pdfium.PdfDocument(blob)
        if page_index >= len(pdf):
            return {"text": "", "lines": 0, "low_conf": 0, "error": "页码越界"}
        page = pdf[page_index]
        image = page.render(scale=DPI / 72).to_pil().convert("RGB")
    except Exception as exc:
        return {"text": "", "lines": 0, "low_conf": 0, "error": f"页面渲染失败：{exc}"}

    try:
        import numpy as np

        # rapidocr 的 ndarray 入口按 OpenCV 约定（BGR），这里做一次转换，避免通道顺序影响识别
        array = np.array(image)[:, :, ::-1].copy()
        engine = _engine()
        result, _elapse = engine(array)
    except Exception as exc:
        return {"text": "", "lines": 0, "low_conf": 0, "error": f"OCR 推理失败：{exc}"}

    if not result:
        return {"text": "", "lines": 0, "low_conf": 0, "error": "未识别到文字"}

    kept: list[str] = []
    low_conf = 0
    for item in _sort_reading_order(list(result)):
        if len(item) < 3:
            continue
        text, score = item[1], float(item[2])
        if score < MIN_CONF:
            low_conf += 1
            continue
        if text.strip():
            kept.append(text.strip())

    return {"text": "\n".join(kept), "lines": len(kept), "low_conf": low_conf, "error": ""}
