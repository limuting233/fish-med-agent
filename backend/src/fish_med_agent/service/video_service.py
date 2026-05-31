"""视频 → 文字描述的前置 transform 服务。

对每个视频抽 N 帧（首/中/尾），并行喂给 vision 模型转描述。
所有抽帧 / vision 调用都受 VisionService 的全局 Semaphore 节流。

设计要点：
- 每段视频固定抽 3 帧（VIDEO_FRAMES_PER_CLIP），由 chat_service / schemas 约束
- ffmpeg 是同步阻塞，全部走 asyncio.to_thread
- 单帧失败返回占位文本，不影响其它帧/其它视频
- DeepSeek 永远不见图，只见描述文本
"""
import asyncio
import os
import tempfile
import time
from typing import Sequence

import ffmpeg

from fish_med_agent.core.logging import get_logger
from fish_med_agent.schemas.chat import VIDEO_FRAMES_PER_CLIP, VideoInput
from fish_med_agent.service.upload_service import UploadService
from fish_med_agent.service.vision_service import vision_service

logger = get_logger(__name__)


class VideoFrameDescription:
    """单帧描述：包含时间点（秒）+ 文本。"""

    __slots__ = ("ts_sec", "text")

    def __init__(self, ts_sec: float, text: str) -> None:
        self.ts_sec = ts_sec
        self.text = text


class VideoDescription:
    """单视频的描述结果：原始元数据 + 抽帧描述列表。"""

    __slots__ = ("filename", "duration", "frames")

    def __init__(
        self,
        filename: str | None,
        duration: float,
        frames: list[VideoFrameDescription],
    ) -> None:
        self.filename = filename
        self.duration = duration
        self.frames = frames


class VideoService:
    """把视频转成中文描述列表。模块级单例使用，详见本文件底部 `video_service`。"""

    def __init__(self) -> None:
        self._upload_service = UploadService()

    async def describe_videos(
        self, videos: Sequence[VideoInput]
    ) -> list[VideoDescription]:
        """并行把多段视频转成描述。

        - 视频间并行，视频内 3 帧也并行（受 VisionService 全局 Semaphore 节流）
        - 取视频失败 / probe 失败 → 整个视频降级，每帧占位
        - 返回顺序与入参一一对应
        """
        if not videos:
            return []
        t0 = time.perf_counter()
        results = await asyncio.gather(
            *[self._describe_one_video(v, idx) for idx, v in enumerate(videos)]
        )
        logger.info(
            f"video describe_videos done: count={len(videos)} "
            f"elapsed={time.perf_counter() - t0:.2f}s"
        )
        return results

    async def _describe_one_video(
        self, video: VideoInput, idx: int
    ) -> VideoDescription:
        """处理单个视频：取字节 → 落临时文件 → 抽 N 帧 → 并行喂 vision。"""
        tag = f"vid#{idx}({video.original_filename or video.object_key})"

        # 1) 从 MinIO 取视频字节
        try:
            data, _ct = await self._upload_service.fetch_video_bytes(video.object_key)
        except Exception:
            logger.exception(f"{tag}: fetch_video_bytes failed")
            return VideoDescription(
                filename=video.original_filename,
                duration=video.duration_seconds,
                frames=[
                    VideoFrameDescription(0.0, "[视频识别失败：无法读取原视频]")
                ],
            )

        # 2) 落临时文件给 ffmpeg
        tmp_video = tempfile.NamedTemporaryFile(
            suffix=f".{video.extension}", delete=False
        )
        try:
            tmp_video.write(data)
            tmp_video.flush()
            tmp_video.close()

            # 3) 抽 N 帧（在线程池里跑 ffmpeg）
            timestamps = self._pick_timestamps(
                video.duration_seconds, VIDEO_FRAMES_PER_CLIP
            )
            try:
                frame_bytes_list = await asyncio.to_thread(
                    _extract_frames_sync, tmp_video.name, timestamps
                )
            except Exception:
                logger.exception(f"{tag}: ffmpeg extract frames failed")
                return VideoDescription(
                    filename=video.original_filename,
                    duration=video.duration_seconds,
                    frames=[
                        VideoFrameDescription(ts, "[视频识别失败：抽帧错误]")
                        for ts in timestamps
                    ],
                )
        finally:
            try:
                os.unlink(tmp_video.name)
            except OSError:
                pass

        # 4) 并行喂 vision（受全局 Semaphore 节流）
        frame_tasks = []
        for fi, (ts, frame_bytes) in enumerate(zip(timestamps, frame_bytes_list)):
            if frame_bytes is None:
                # 抽帧时单帧失败的占位
                async def _placeholder(t: float = ts) -> tuple[float, str]:
                    return t, "[视频识别失败：该帧无法解码]"
                frame_tasks.append(_placeholder())
            else:
                frame_tag = f"{tag}/frame#{fi}({ts:.1f}s)"
                frame_tasks.append(
                    _describe_frame(ts, frame_bytes, frame_tag)
                )
        frame_results = await asyncio.gather(*frame_tasks)
        frames = [VideoFrameDescription(ts, text) for ts, text in frame_results]
        return VideoDescription(
            filename=video.original_filename,
            duration=video.duration_seconds,
            frames=frames,
        )

    @staticmethod
    def _pick_timestamps(duration: float, n_frames: int) -> list[float]:
        """挑 n_frames 个抽帧时间点：均匀分布在 (0, duration) 内部，避开两端可能的黑帧。

        例如 duration=12, n=3 → [2.0, 6.0, 10.0]
        例如 duration=30, n=3 → [5.0, 15.0, 25.0]
        """
        if n_frames <= 0 or duration <= 0:
            return []
        # 均匀切 n+1 段，取每段右端点（除最后一个右端点 = duration，跳过取中点）
        # 简单实现：(i+0.5) / n * duration，避开 0 和 duration
        return [round((i + 0.5) / n_frames * duration, 3) for i in range(n_frames)]


async def _describe_frame(
    ts: float, frame_bytes: bytes, tag: str
) -> tuple[float, str]:
    """单帧调 vision，返回 (timestamp, description)。"""
    text = await vision_service.describe_bytes(frame_bytes, "image/jpeg", tag)
    return ts, text


def _extract_frames_sync(
    video_path: str, timestamps: list[float]
) -> list[bytes | None]:
    """同步用 ffmpeg 抽帧（必须在 asyncio.to_thread 里调）。

    对每个 timestamp 单独跑一次 ffmpeg seek，输出 JPEG 字节流。
    单帧失败返回 None，不影响其它帧。

    Args:
        video_path: 临时文件路径
        timestamps: 秒数列表

    Returns:
        与 timestamps 等长的 list[bytes | None]
    """
    results: list[bytes | None] = []
    for ts in timestamps:
        try:
            # -ss <ts>  快速跳到时间点
            # -frames:v 1  只输出一帧
            # -f image2pipe  通过 stdout 管道
            # -vcodec mjpeg  JPEG 编码
            # -q:v 3  质量 (1-31, 3 是高质量)
            out, _ = (
                ffmpeg.input(video_path, ss=ts)
                .output(
                    "pipe:",
                    vframes=1,
                    format="image2pipe",
                    vcodec="mjpeg",
                    **{"q:v": 3},
                )
                .run(capture_stdout=True, capture_stderr=True, quiet=True)
            )
            if out:
                results.append(out)
            else:
                logger.warning(f"ffmpeg extract empty frame at ts={ts}")
                results.append(None)
        except ffmpeg.Error as e:
            stderr = (e.stderr or b"").decode("utf-8", errors="replace")
            logger.warning(f"ffmpeg extract failed at ts={ts}: {stderr[:200]}")
            results.append(None)
    return results


# 模块级单例
video_service = VideoService()
