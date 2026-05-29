import uuid
from datetime import datetime, timezone

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile

from fish_med_agent.clients.minio_client import get_s3_client
from fish_med_agent.core.config import settings
from fish_med_agent.core.exception import (
    UnsupportedFileTypeError,
    UploadFailedError,
    UploadFileTooLargeError,
)
from fish_med_agent.core.logging import get_logger
from fish_med_agent.schemas.upload import UploadImageResponse

logger = get_logger(__name__)


class UploadService:
    """
    图片上传业务逻辑：校验 → 生成 key → 写入 MinIO。
    """

    MAX_BYTES = 10 * 1024 * 1024  # 10MB
    # mime -> 文件扩展名
    _MIME_TO_EXT: dict[str, str] = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
    }

    _bucket_ensured = False

    async def upload_image(self, user_id: int, file: UploadFile) -> UploadImageResponse:
        """
        上传单张图片到 MinIO。

        Args:
            user_id: 当前登录用户 ID（仅用于日志，不进 key 路径）
            file: FastAPI 解析出的上传文件

        Returns:
            UploadImageResponse，含 object_key / content_type / extension / size / original_filename
        """
        data = await self._read_with_limit(file)
        mime = self._detect_mime(data)
        if mime is None:
            logger.debug("upload rejected: unsupported file type")
            raise UnsupportedFileTypeError()

        ext = self._MIME_TO_EXT[mime]
        size = len(data)
        now = datetime.now(timezone.utc)
        object_key = f"images/{now:%Y/%m/%d}/{uuid.uuid4().hex}.{ext}"

        try:
            async with get_s3_client() as s3:
                await self._ensure_bucket(s3)
                await s3.put_object(
                    Bucket=settings.MINIO_BUCKET,
                    Key=object_key,
                    Body=data,
                    ContentType=mime,
                )
        except (BotoCoreError, ClientError):
            logger.exception("put_object to MinIO failed")
            raise UploadFailedError()

        logger.info(f"user {user_id} uploaded image: {object_key} ({size} bytes)")
        return UploadImageResponse(
            object_key=object_key,
            content_type=mime,
            extension=ext,
            size=size,
            original_filename=file.filename,
        )

    async def _read_with_limit(self, file: UploadFile) -> bytes:
        """
        分块读取上传文件，超过 MAX_BYTES 立刻中止，避免把超大文件全部读进内存。
        """
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = await file.read(1024 * 1024)  # 1MB
            if not chunk:
                break
            total += len(chunk)
            if total > self.MAX_BYTES:
                raise UploadFileTooLargeError()
            chunks.append(chunk)
        return b"".join(chunks)

    @staticmethod
    def _detect_mime(data: bytes) -> str | None:
        """
        通过 magic number 判断图片类型，避免单纯信任 Content-Type。
        """
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
            return "image/gif"
        if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        return None

    @classmethod
    async def _ensure_bucket(cls, s3) -> None:
        """
        懒加载式确保 bucket 存在，进程内只检查一次。
        """
        if cls._bucket_ensured:
            return
        bucket = settings.MINIO_BUCKET
        try:
            await s3.head_bucket(Bucket=bucket)
        except ClientError:
            logger.info(f"bucket {bucket} not found, creating")
            await s3.create_bucket(Bucket=bucket)
        cls._bucket_ensured = True
