"""解析分发：按扩展名选解析器，异常一律降级成 `Doc`，绝不把 500 抛给前端。

原则：**解析失败也是结果**。`parse_status=failed` + `degraded` 说明原因，
前端能显示"这份文件没解析成功，原因是什么"，比一个 500 有用得多。
"""

from __future__ import annotations

from api.docmodel import Doc
from api.parsers import ParseError, ext_of
from api.parsers import docx_parser, pdf_parser, txt_parser
from api.parsers.clauses import split_clauses

SUPPORTED_EXTS = (".docx", ".pdf", ".txt", ".md")


def parse_file(blob: bytes, file_name: str, doc_id: str, sha256: str) -> Doc:
    ext = ext_of(file_name)

    try:
        if ext == ".docx":
            doc = docx_parser.parse(blob, file_name, doc_id, sha256)
        elif ext == ".pdf":
            doc = pdf_parser.parse(blob, file_name, doc_id, sha256)
        elif ext in (".txt", ".md"):
            doc = txt_parser.parse(blob, file_name, doc_id, sha256, ext=ext)
        else:
            raise ParseError(f"暂不支持的文件类型：{ext or '无扩展名'}（支持 docx / pdf / txt / md）")
    except ParseError as exc:
        doc = Doc(
            doc_id=doc_id,
            file_name=file_name,
            ext=ext,
            sha256=sha256,
            page_source="none",
            full_text="",
            parse_status="failed",
        )
        doc.degraded.append(str(exc))
        return doc
    except Exception as exc:  # noqa: BLE001 - 解析器内部异常也必须可展示
        doc = Doc(
            doc_id=doc_id,
            file_name=file_name,
            ext=ext,
            sha256=sha256,
            page_source="none",
            full_text="",
            parse_status="failed",
        )
        doc.degraded.append(f"解析异常：{type(exc).__name__}: {exc}")
        return doc

    doc.clauses = split_clauses(doc)
    return doc
