"""从 Nexent 的附件存储（MinIO / S3）取回聊天里上传的文件。

为什么需要它：Nexent 聊天上传的文件存在它自己的对象存储里，路径形如
`s3://nexent/attachments/<uuid>/<时间戳>_<hash>.docx`；而我们的 `parse_tender` 只认本服务的
`doc_id`。MCP 工具 `parse_attachment(s3_path)` 用它把文件取回来，再走同一套入库流程。

配置（compose 环境变量，不写进代码）：
  S3_ENDPOINT   默认 host.docker.internal:9010（Nexent 的 minio 宿主端口）
  S3_ACCESS_KEY / S3_SECRET_KEY  从 MinIO 控制台或容器环境变量取
  S3_SECURE     "1" 表示 https，默认 http
  S3_BUCKET     默认 nexent
"""

from __future__ import annotations

import os
from pathlib import Path


def _cfg() -> dict[str, str]:
    return {
        "endpoint": os.getenv("S3_ENDPOINT", "host.docker.internal:9010"),
        "access_key": os.getenv("S3_ACCESS_KEY", ""),
        "secret_key": os.getenv("S3_SECRET_KEY", ""),
        "bucket": os.getenv("S3_BUCKET", "nexent"),
        "secure": os.getenv("S3_SECURE", "0"),
    }


def configured() -> bool:
    cfg = _cfg()
    return bool(cfg["access_key"] and cfg["secret_key"])


def parse_s3_path(s3_path: str) -> tuple[str, str]:
    """`s3://bucket/key` → (bucket, key)；也接受不带 scheme 的 `bucket/key`。"""
    text = (s3_path or "").strip()
    if text.startswith("s3://"):
        text = text[5:]
    if "/" not in text:
        raise ValueError(f"s3 路径格式不对：{s3_path}（应形如 s3://bucket/key）")
    bucket, key = text.split("/", 1)
    if not bucket or not key:
        raise ValueError(f"s3 路径格式不对：{s3_path}")
    return bucket, key


def fetch(s3_path: str, max_bytes: int = 60 * 1024 * 1024) -> tuple[str, bytes]:
    """下载对象，返回 (文件名, 字节)。超过大小上限直接报错，避免把大文件塞进内存。"""
    cfg = _cfg()
    if not configured():
        raise RuntimeError(
            "未配置 S3 凭据（S3_ACCESS_KEY / S3_SECRET_KEY），无法读取聊天附件；"
            "请改用页面 http://<host>:8080 上传，或让助手调用 list_documents 找已解析文档"
        )

    try:
        from minio import Minio
    except Exception as exc:  # 依赖缺失
        raise RuntimeError(f"minio 客户端不可用：{exc}") from exc

    bucket, key = parse_s3_path(s3_path)
    client = Minio(
        cfg["endpoint"],
        access_key=cfg["access_key"],
        secret_key=cfg["secret_key"],
        secure=cfg["secure"] == "1",
    )
    stat = client.stat_object(bucket, key)
    if stat.size and stat.size > max_bytes:
        raise ValueError(f"附件过大（{stat.size / 1024 / 1024:.1f} MB），超过解析上限")

    response = client.get_object(bucket, key)
    try:
        blob = response.read()
    finally:
        response.close()
        response.release_conn()

    name = Path(key).name
    # Nexent 附件名带"时间戳_"前缀，去掉它让前端展示更干净
    if "_" in name and name.split("_", 1)[0].isdigit():
        name = name.split("_", 1)[1]
    return name, blob
