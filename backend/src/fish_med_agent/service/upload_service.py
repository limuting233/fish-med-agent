import uuid
from datetime import datetime, timezone

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile

from fish_med_agent.clients.minio_client import get_s3_client
from fish_med_agent.core.config import settings
from fish_med_agent.core.exception import (
    NoFileUploadedError,
    TooManyFilesError,
    UnsupportedFileTypeError,
    UploadFailedError,
    UploadFileTooLargeError,
)
from fish_med_agent.core.logging import get_logger
from fish_med_agent.schemas.upload import UploadImageItem

logger = get_logger(__name__)


class UploadService:
    """
    图片上传业务逻辑：校验 → 生成 key → 写入 MinIO。
    """

    MAX_BYTES = 10 * 1024 * 1024  # 单张最大 10MB
    MAX_FILES = 6  # 一次最多上传张数
    # mime -> 文件扩展名
    _MIME_TO_EXT: dict[str, str] = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
    }

    _bucket_ensured = False

    async def upload_images(
            self, user_id: int, files: list[UploadFile]
    ) -> list[UploadImageItem]:
        """
        批量上传图片到 MinIO。

        先整体校验数量，再逐张读取 + 校验 + 写入。任一张失败则回滚：
        把本次已写入的图片全部删除，再把异常抛出去（保证整批要么全成功、
        要么 MinIO 里不留下半截脏数据）。

        Args:
            user_id: 当前登录用户 ID（仅用于日志，不进 key 路径）
            files: FastAPI 解析出的上传文件列表

        Returns:
            UploadImageItem 列表，顺序与上传顺序一致
        """
        # 过滤掉空表单项（前端有时会带一个 filename 为空的占位 part）
        valid_files = [f for f in files if f is not None and f.filename]
        if not valid_files:
            raise NoFileUploadedError()
        if len(valid_files) > self.MAX_FILES:
            raise TooManyFilesError()

        results: list[UploadImageItem] = []
        async with get_s3_client() as s3:
            await self._ensure_bucket(s3)
            try:
                for file in valid_files:
                    results.append(await self._upload_one(s3, user_id, file))
            except Exception:
                # 任一张失败 → 回滚本次已写入的对象，避免留下孤儿文件
                await self._rollback(s3, [item.object_key for item in results])
                raise
        return results

    async def _rollback(self, s3, object_keys: list[str]) -> None:
        """
        删除本次批量上传中已成功写入的对象。回滚本身的失败只记日志，
        不覆盖原始上传异常。
        """
        if not object_keys:
            return
        logger.warning(f"rolling back {len(object_keys)} uploaded objects: {object_keys}")
        try:
            await s3.delete_objects(
                Bucket=settings.MINIO_BUCKET,
                Delete={
                    "Objects": [{"Key": key} for key in object_keys],
                    "Quiet": True,
                },
            )
        except (BotoCoreError, ClientError):
            # 回滚失败不应淹没真正的上传异常，留下日志人工/GC 兜底
            logger.exception("rollback delete_objects failed; orphan objects may remain")

    async def _upload_one(
            self, s3, user_id: int, file: UploadFile
    ) -> UploadImageItem:
        """
        校验并上传单张图片，复用已建立的 s3 client。
        """
        data = await self._read_with_limit(file)
        mime = self._detect_mime(data)
        if mime is None:
            logger.debug(f"upload rejected: unsupported file type ({file.filename})")
            raise UnsupportedFileTypeError()

        ext = self._MIME_TO_EXT[mime]
        size = len(data)
        now = datetime.now(timezone.utc)
        object_key = f"images/{now:%Y/%m/%d}/{uuid.uuid4().hex}.{ext}"

        try:
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
        return UploadImageItem(
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
