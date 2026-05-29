from contextlib import asynccontextmanager
from typing import AsyncIterator

import aioboto3
from botocore.config import Config

from fish_med_agent.core.config import settings

_session = aioboto3.Session()

# MinIO 兼容性配置：
# 1. path-style 寻址：否则 boto3 默认走 virtual-hosted-style，会去解析
#    `{bucket}.localhost`，DNS 查不到 → 请求卡死。
# 2. 关闭默认的 trailing checksum：boto3 ≥1.36 默认在 PutObject 时给请求体
#    加 `aws-chunked` + `x-amz-checksum-*` 尾部校验和；MinIO 不解析这个尾部，
#    会一直等 body 直到超时报 "A timeout occurred while trying to lock a
#    resource"。改成 when_required 后只在 S3 协议强制要求时才算校验和。
_s3_config = Config(
    signature_version="s3v4",
    s3={"addressing_style": "path"},
    request_checksum_calculation="when_required",
    response_checksum_validation="when_required",
    connect_timeout=5,
    read_timeout=30,
    retries={"max_attempts": 2, "mode": "standard"},
)


@asynccontextmanager
async def get_s3_client() -> AsyncIterator:
    """
    获取 MinIO（S3 协议）异步客户端。

    用法:
        async with get_s3_client() as s3:
            await s3.put_object(Bucket=..., Key=..., Body=...)
    """
    async with _session.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        region_name=settings.MINIO_REGION,
        config=_s3_config,
    ) as client:
        yield client
