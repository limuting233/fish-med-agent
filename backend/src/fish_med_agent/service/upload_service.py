import asyncio
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone

import ffmpeg
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile

from fish_med_agent.clients.minio_client import get_s3_client
from fish_med_agent.core.config import settings
from fish_med_agent.core.exception import (
    BizException,
    DeleteFailedError,
    ImageNotFoundError,
    InvalidObjectKeyError,
    UnsupportedFileTypeError,
    UnsupportedVideoFormatError,
    UploadFailedError,
    UploadFileTooLargeError,
    VideoCorruptedError,
    VideoNotFoundError,
    VideoTooLargeError,
    VideoTooLongError,
)
from fish_med_agent.core.logging import get_logger
from fish_med_agent.schemas.upload import UploadImageResponse, UploadVideoResponse

logger = get_logger(__name__)


class UploadService:
    """
    图片 / 视频上传业务逻辑：校验 → 生成 key → 写入 MinIO。
    """

    MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 单张图片最大 10MB
    MAX_VIDEO_BYTES = 50 * 1024 * 1024  # 单段视频最大 50MB
    MAX_VIDEO_DURATION_SECONDS = 30.0  # 单段视频最大时长 30s

    # 图片 mime -> 扩展名
    _IMAGE_MIME_TO_EXT: dict[str, str] = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
    }
    # 视频 mime -> 扩展名（mov 在标准 MIME 里是 video/quicktime）
    _VIDEO_MIME_TO_EXT: dict[str, str] = {
        "video/mp4": "mp4",
        "video/webm": "webm",
        "video/quicktime": "mov",
    }

    # 对象 key 前缀：图片走 images/，视频走 videos/
    _KEY_PREFIX_IMAGE = "images/"
    _KEY_PREFIX_VIDEO = "videos/"
    # 一组允许通过 presign 接口签名的前缀（前端历史回显图片和视频都能用同一个接口）
    _ALLOWED_KEY_PREFIXES = (_KEY_PREFIX_IMAGE, _KEY_PREFIX_VIDEO)

    # presigned URL 的默认有效期：1 小时
    # 与 access_token 时长一致，简化前端心智（token 失效时也该刷一下图）
    PRESIGN_EXPIRES_IN = 3600  # 秒，用于传给 boto3 的 ExpiresIn 参数

    _bucket_ensured = False

    def _compute_expires_at_ms(self) -> int:
        """计算"从现在起再过 PRESIGN_EXPIRES_IN 秒"的 UTC epoch 毫秒时间戳。

        前端拿到这个绝对时间戳后可以直接比较 Date.now()，不用额外算偏移。
        务必在签名之前调用，保证返回的时间戳不晚于 URL 实际过期点。
        """
        return int(time.time() * 1000) + self.PRESIGN_EXPIRES_IN * 1000

    def _is_valid_key_with_prefix(self, object_key: str, prefix: str) -> bool:
        """object_key 严格匹配指定前缀：非空 + 不含路径穿越 + startswith(prefix)。"""
        return (
            bool(object_key)
            and ".." not in object_key
            and object_key.startswith(prefix)
        )

    def _is_valid_image_key(self, object_key: str) -> bool:
        """严格要求 images/ 前缀。"""
        return self._is_valid_key_with_prefix(object_key, self._KEY_PREFIX_IMAGE)

    def _is_valid_video_key(self, object_key: str) -> bool:
        """严格要求 videos/ 前缀。"""
        return self._is_valid_key_with_prefix(object_key, self._KEY_PREFIX_VIDEO)

    def _is_valid_object_key(self, object_key: str) -> bool:
        """通用合法性校验：在 _ALLOWED_KEY_PREFIXES 中任一前缀下即可。

        供 generate_presigned_urls 这种"前端可能混传图片和视频 key"的接口使用；
        delete / fetch 走更严格的 _is_valid_image_key / _is_valid_video_key。
        """
        return any(
            self._is_valid_key_with_prefix(object_key, p)
            for p in self._ALLOWED_KEY_PREFIXES
        )

    async def _presign_get(self, s3, object_key: str) -> str:
        """生成单个 GET 操作的 presigned URL。

        boto3 的 generate_presigned_url 是纯计算（只算签名，不打网络），
        所以这里 await 只是为了拿到底层签名器的协程包装。
        """
        return await s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": settings.MINIO_BUCKET, "Key": object_key},
            ExpiresIn=self.PRESIGN_EXPIRES_IN,
        )

    async def generate_presigned_urls(
        self, object_keys: list[str]
    ) -> tuple[dict[str, str], int]:
        """批量为已有 object_key 生成 presigned URL。

        - 在一个 s3 client context 内循环签名，避免重复开 client 的开销
        - 支持混传图片（images/）和视频（videos/）key，任一允许前缀均可
        - 非法 key（不在允许前缀下、含路径穿越等）静默从结果中省略，前端按缺失处理
        - **不调 head_object 检查存在性**，节省一轮 RTT；对象若已被删，
          前端 <img onerror> / <video onerror> 兜底显示占位

        Args:
            object_keys: 待签名的 key 列表

        Returns:
            (urls dict, expires_at_ms) —— expires_at_ms 是统一的 UTC 毫秒时间戳
            （取批量开始前一刻作为基准，保证不晚于任一 URL 的实际过期点）
        """
        # 必须在签第一个 URL 之前算 expires_at，确保它 ≤ 所有 URL 的实际过期点
        expires_at_ms = self._compute_expires_at_ms()

        urls: dict[str, str] = {}
        valid_keys = [k.strip() for k in object_keys if self._is_valid_object_key(k.strip())]
        if not valid_keys:
            return urls, expires_at_ms

        async with get_s3_client() as s3:
            for key in valid_keys:
                try:
                    urls[key] = await self._presign_get(s3, key)
                except (BotoCoreError, ClientError):
                    # 单个 key 签名失败不影响其它；继续
                    logger.exception(f"presign failed for {key!r}")
        return urls, expires_at_ms

    async def delete_image(self, user_id: int, object_key: str) -> str:
        """删除单张图片。

        Raises:
            InvalidObjectKeyError: key 非法或不在 images/ 目录下
            ImageNotFoundError: 对象不存在
            DeleteFailedError: MinIO 删除调用失败
        """
        return await self._delete_object_with_check(
            user_id=user_id,
            object_key=object_key,
            key_validator=self._is_valid_image_key,
            not_found_exc=ImageNotFoundError,
            kind="image",
        )

    async def delete_video(self, user_id: int, object_key: str) -> str:
        """删除单段视频。

        Raises:
            InvalidObjectKeyError: key 非法或不在 videos/ 目录下
            VideoNotFoundError: 对象不存在
            DeleteFailedError: MinIO 删除调用失败
        """
        return await self._delete_object_with_check(
            user_id=user_id,
            object_key=object_key,
            key_validator=self._is_valid_video_key,
            not_found_exc=VideoNotFoundError,
            kind="video",
        )

    async def _delete_object_with_check(
        self,
        *,
        user_id: int,
        object_key: str,
        key_validator,
        not_found_exc: type[BizException],
        kind: str,
    ) -> str:
        """图片/视频通用删除：校验 key 前缀 → head_object 探活 → delete_object。

        kind 只用于日志区分 image / video。
        """
        key = object_key.strip()
        # 限定只能删自己分区下的对象，防止越权删 bucket 内其它命名空间
        if not key_validator(key):
            logger.debug(f"delete rejected: invalid {kind} object_key {key!r}")
            raise InvalidObjectKeyError()

        async with get_s3_client() as s3:
            # 先确认存在，给前端一个明确的 404，而不是静默成功
            try:
                await s3.head_object(Bucket=settings.MINIO_BUCKET, Key=key)
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                if code in ("404", "NoSuchKey", "NotFound"):
                    raise not_found_exc()
                logger.exception(f"head_object before delete failed (kind={kind})")
                raise DeleteFailedError()

            try:
                await s3.delete_object(Bucket=settings.MINIO_BUCKET, Key=key)
            except (BotoCoreError, ClientError):
                logger.exception(f"delete_object from MinIO failed (kind={kind})")
                raise DeleteFailedError()

        logger.info(f"user {user_id} deleted {kind}: {key}")
        return key

    async def fetch_image_bytes(self, object_key: str) -> tuple[bytes, str]:
        """按 object_key 从 MinIO 读出图片字节流。

        供 VisionService 把图片转成 base64 内联给 vision 模型时使用。

        Args:
            object_key: 上传接口返回的 key（必须在 images/ 目录下）

        Returns:
            (bytes, content_type) 元组

        Raises:
            InvalidObjectKeyError: key 为空 / 含路径穿越 / 不在 images/ 下
            ImageNotFoundError: 对象不存在
            botocore ClientError: 其它 MinIO 通信错误，由调用方决定降级策略
        """
        return await self._fetch_object_bytes(
            object_key, self._is_valid_image_key, ImageNotFoundError
        )

    async def fetch_video_bytes(self, object_key: str) -> tuple[bytes, str]:
        """按 object_key 从 MinIO 读出视频字节流。

        供 VideoService 把视频写入临时文件后用 ffmpeg 抽帧。

        Raises:
            InvalidObjectKeyError: key 非法或不在 videos/ 下
            VideoNotFoundError: 对象不存在
            botocore ClientError: 其它 MinIO 通信错误
        """
        return await self._fetch_object_bytes(
            object_key, self._is_valid_video_key, VideoNotFoundError
        )

    async def _fetch_object_bytes(
        self,
        object_key: str,
        validator,
        not_found_exc: type[BizException],
    ) -> tuple[bytes, str]:
        """从 MinIO 读取对象字节流的通用实现，供图片/视频两路复用。

        Args:
            object_key: 待读取的 key
            validator: 校验 key 合法性的回调（决定走 images/ 还是 videos/）
            not_found_exc: 对象不存在时抛的异常类型（图片/视频各自的 404）

        Returns:
            (bytes, content_type)
        """
        key = object_key.strip()
        if not validator(key):
            logger.debug(f"fetch rejected: invalid object_key {key!r}")
            raise InvalidObjectKeyError()

        async with get_s3_client() as s3:
            try:
                obj = await s3.get_object(Bucket=settings.MINIO_BUCKET, Key=key)
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                if code in ("404", "NoSuchKey", "NotFound"):
                    raise not_found_exc()
                logger.exception(f"get_object failed for key={key!r}")
                raise

            content_type = obj.get("ContentType") or "application/octet-stream"
            # StreamingBody，必须 await read 拿全部字节
            body = await obj["Body"].read()
            return body, content_type

    async def upload_image(
            self, user_id: int, file: UploadFile
    ) -> UploadImageResponse:
        """
        校验并上传单张图片到 MinIO。

        Args:
            user_id: 当前登录用户 ID（仅用于日志，不进 key 路径）
            file: FastAPI 解析出的上传文件

        Returns:
            UploadImageResponse，含 object_key / content_type / extension / size / original_filename

        Raises:
            UploadFileTooLargeError: 超过 MAX_BYTES
            UnsupportedFileTypeError: magic number 不是受支持的图片类型
            UploadFailedError: MinIO 写入失败
        """
        data = await self._read_with_limit(
            file, self.MAX_IMAGE_BYTES, UploadFileTooLargeError
        )
        mime = self._detect_image_mime(data)
        if mime is None:
            logger.debug(f"upload rejected: unsupported file type ({file.filename})")
            raise UnsupportedFileTypeError()

        ext = self._IMAGE_MIME_TO_EXT[mime]
        size = len(data)
        now = datetime.now(timezone.utc)
        object_key = f"{self._KEY_PREFIX_IMAGE}{now:%Y/%m/%d}/{uuid.uuid4().hex}.{ext}"

        try:
            async with get_s3_client() as s3:
                await self._ensure_bucket(s3)
                await s3.put_object(
                    Bucket=settings.MINIO_BUCKET,
                    Key=object_key,
                    Body=data,
                    ContentType=mime,
                )
                # 必须在签名前算 expires_at，保证它 ≤ URL 的实际过期点
                expires_at_ms = self._compute_expires_at_ms()
                # 复用同一个 client 顺手把展示用 URL 签出来，省前端一次 RTT
                presigned_url = await self._presign_get(s3, object_key)
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
            url=presigned_url,
            url_expires_at=expires_at_ms,
        )

    async def _read_with_limit(
        self,
        file: UploadFile,
        limit_bytes: int,
        too_large_exc: type[BizException],
    ) -> bytes:
        """
        分块读取上传文件，超过 limit_bytes 立刻中止，避免把超大文件读进内存。

        too_large_exc 区分图片 / 视频两种超限错误码（UploadFileTooLargeError /
        VideoTooLargeError），消息和 HTTP code 都不同。
        """
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = await file.read(1024 * 1024)  # 1MB
            if not chunk:
                break
            total += len(chunk)
            if total > limit_bytes:
                raise too_large_exc()
            chunks.append(chunk)
        return b"".join(chunks)

    @staticmethod
    def _detect_image_mime(data: bytes) -> str | None:
        """通过 magic number 判断图片类型，避免单纯信任 Content-Type。"""
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
            return "image/gif"
        if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        return None

    @staticmethod
    def _detect_video_mime(data: bytes) -> str | None:
        """通过 magic number 判断视频容器类型。

        - WebM (Matroska/EBML)：起始 4 字节固定 0x1A 0x45 0xDF 0xA3
        - MP4 / MOV：ISO BMFF 容器，前 4 字节是 box size，紧跟 "ftyp" + major brand
          - major brand 以 "qt" 开头 → QuickTime（.mov）
          - 其它（isom/mp42/avc1/dash/...）一律按 mp4 处理
        其它格式（avi/flv/mpeg 等）一律返回 None，不放行。
        """
        if data.startswith(b"\x1a\x45\xdf\xa3"):
            return "video/webm"
        if len(data) >= 12 and data[4:8] == b"ftyp":
            major_brand = data[8:12]
            if major_brand.startswith(b"qt"):
                return "video/quicktime"
            return "video/mp4"
        return None

    async def upload_video(
        self, user_id: int, file: UploadFile
    ) -> UploadVideoResponse:
        """校验并上传单段视频到 MinIO。

        Args:
            user_id: 当前登录用户 ID（仅用于日志，不进 key 路径）
            file: FastAPI 解析出的上传文件

        Returns:
            UploadVideoResponse

        Raises:
            VideoTooLargeError: 超过 MAX_VIDEO_BYTES（50MB）
            UnsupportedVideoFormatError: magic number 不匹配 mp4 / webm / mov
            VideoCorruptedError: ffmpeg.probe 解析失败
            VideoTooLongError: duration 超过 MAX_VIDEO_DURATION_SECONDS（30s）
            UploadFailedError: MinIO 写入失败
        """
        data = await self._read_with_limit(
            file, self.MAX_VIDEO_BYTES, VideoTooLargeError
        )
        mime = self._detect_video_mime(data)
        if mime is None:
            logger.debug(
                f"video upload rejected: unsupported format ({file.filename})"
            )
            raise UnsupportedVideoFormatError()

        # 写到临时文件给 ffmpeg.probe（ffmpeg 走文件路径比 pipe 稳）
        duration = await self._probe_video_duration(data, mime)
        if duration > self.MAX_VIDEO_DURATION_SECONDS:
            logger.debug(
                f"video upload rejected: too long {duration:.2f}s > "
                f"{self.MAX_VIDEO_DURATION_SECONDS}s ({file.filename})"
            )
            raise VideoTooLongError()

        ext = self._VIDEO_MIME_TO_EXT[mime]
        size = len(data)
        now = datetime.now(timezone.utc)
        object_key = (
            f"{self._KEY_PREFIX_VIDEO}{now:%Y/%m/%d}/{uuid.uuid4().hex}.{ext}"
        )

        try:
            async with get_s3_client() as s3:
                await self._ensure_bucket(s3)
                await s3.put_object(
                    Bucket=settings.MINIO_BUCKET,
                    Key=object_key,
                    Body=data,
                    ContentType=mime,
                )
                expires_at_ms = self._compute_expires_at_ms()
                presigned_url = await self._presign_get(s3, object_key)
        except (BotoCoreError, ClientError):
            logger.exception("put_object (video) to MinIO failed")
            raise UploadFailedError()

        logger.info(
            f"user {user_id} uploaded video: {object_key} "
            f"({size} bytes, {duration:.2f}s)"
        )
        return UploadVideoResponse(
            object_key=object_key,
            content_type=mime,
            extension=ext,
            size=size,
            duration_seconds=duration,
            original_filename=file.filename,
            url=presigned_url,
            url_expires_at=expires_at_ms,
        )

    async def _probe_video_duration(self, data: bytes, mime: str) -> float:
        """用 ffmpeg.probe 测视频时长（秒）。

        ffmpeg-python 是同步阻塞 API，包到 asyncio.to_thread 里避免阻塞事件循环。
        临时文件 ext 跟容器对齐，让 ffmpeg 走对应 demuxer。
        """
        ext = self._VIDEO_MIME_TO_EXT.get(mime, "bin")
        # 用 NamedTemporaryFile 拿路径，由 ffmpeg 子进程访问；
        # delete=False 自己手动清理，避免 Windows 上的句柄冲突
        tmp = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
        try:
            tmp.write(data)
            tmp.flush()
            tmp.close()

            def _probe_sync() -> float:
                try:
                    info = ffmpeg.probe(tmp.name)
                except ffmpeg.Error as e:
                    stderr = (e.stderr or b"").decode("utf-8", errors="replace")
                    logger.warning(f"ffmpeg.probe failed: {stderr[:300]}")
                    raise VideoCorruptedError()
                # 优先取 format.duration（容器级），缺失再扫视频流
                fmt = info.get("format") or {}
                if (d := fmt.get("duration")) is not None:
                    return float(d)
                for s in info.get("streams") or []:
                    if s.get("codec_type") == "video" and s.get("duration"):
                        return float(s["duration"])
                logger.warning(f"ffmpeg.probe returned no duration: {info!r}")
                raise VideoCorruptedError()

            return await asyncio.to_thread(_probe_sync)
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                logger.debug(f"failed to unlink temp file {tmp.name}")

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
