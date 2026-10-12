"""S3 兼容存储（spec §5.3）：dev MinIO / prod Supabase Storage，同一套代码。

boto3 为同步库，一律 asyncio.to_thread 包装（全计划约定）。
"""

import asyncio
import contextlib
from typing import Any, cast

from interview_agent.core.config import get_settings

_client: Any = None


def _get_client() -> Any:
    global _client
    if _client is None:
        import boto3

        s = get_settings()
        _client = boto3.client(
            "s3",
            endpoint_url=s.s3_endpoint_url,
            aws_access_key_id=s.s3_access_key,
            aws_secret_access_key=s.s3_secret_key,
            region_name=s.s3_region,
        )
    return _client


async def put_bytes(key: str, data: bytes, content_type: str) -> None:
    s = get_settings()

    def _put() -> None:
        _get_client().put_object(Bucket=s.s3_bucket, Key=key, Body=data, ContentType=content_type)

    await asyncio.to_thread(_put)


async def get_bytes(key: str) -> bytes:
    s = get_settings()

    def _get() -> bytes:
        body = _get_client().get_object(Bucket=s.s3_bucket, Key=key)["Body"]
        return cast(bytes, body.read())

    return await asyncio.to_thread(_get)


async def ensure_bucket() -> None:
    """dev 便利：MinIO 首次启动桶不存在时自建（prod 由 Supabase 预建，无权限则忽略报错）。"""
    s = get_settings()

    def _ensure() -> None:
        c = _get_client()
        buckets = [b["Name"] for b in c.list_buckets().get("Buckets", [])]
        if s.s3_bucket not in buckets:
            c.create_bucket(Bucket=s.s3_bucket)

    # prod 上无创建权限属正常
    with contextlib.suppress(Exception):
        await asyncio.to_thread(_ensure)
