"""图片 / 视频帧 → 文字描述的前置 transform 服务。

调用 MiMo VLM（OpenAI 兼容协议）把用户上传的鱼病相关图片/视频帧转成简洁中文描述，
供 DeepSeek 主对话模型阅读。设计要点：

- DeepSeek 永远不见图，只见 vision 转录后的文字
- 描述会被持久化进 user 消息的 content（在 chat_service 拼接），
  每轮不重复调 vision
- 单张图/单帧失败不阻塞整体，返回占位文本，让后续诊断仍能进行
- **全局 Semaphore(6) 限流**：图片描述与视频帧描述共享这一额度，
  避免一次消息把 MiMo 打爆（最坏 6 视频×3 帧=18 帧排队等 6 个槽）
"""
import asyncio
import base64
import time
from typing import Sequence

from openai import AsyncOpenAI

from fish_med_agent.core.config import settings
from fish_med_agent.core.logging import get_logger
from fish_med_agent.schemas.chat import ImageInput
from fish_med_agent.service.upload_service import UploadService

logger = get_logger(__name__)

# vision 模型的描述任务 prompt。约束三件事：
#   1) 关注鱼病相关特征（体表/鳃/行为/环境）
#   2) 只描述不诊断（诊断交给主对话模型综合多模态信息后给出）
#   3) 长度可控，避免占用太多 DeepSeek 上下文
_VISION_PROMPT = (
    "你是一位水产养殖辅助识图助手。请用简洁中文客观描述这张图片中与鱼病诊断相关的特征，重点关注：\n"
    "- 体表：是否有溃烂、出血点、白点、寄生物、鳞片脱落\n"
    "- 鳃部：颜色是否正常、有无附着物、有无充血或发白\n"
    "- 行为/姿态：是否浮头、侧翻、贴边、游动异常\n"
    "- 环境线索：水体颜色、水面有无泡沫、有无死鱼\n"
    "如果图中没有鱼，请直接说明图中实际内容（如设备、水体、文档等）。"
    "**只描述客观现象，不要下诊断结论**。控制在 120 字以内。"
)

# 全局并发限流：图片 + 视频帧共享同一份额度
# 视频可能一次抽 6×3=18 帧，没有限流会一波打满 MiMo 触发限速
_VISION_SEMAPHORE = asyncio.Semaphore(6)


class VisionService:
    """把图片/视频帧转成中文描述。模块级单例使用，详见本文件底部 `vision_service`。"""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.MIMO_API_KEY,
            base_url=settings.MIMO_BASE_URL,
            timeout=settings.MIMO_TIMEOUT,
        )
        # UploadService 无状态，按需 new 一份共用
        self._upload_service = UploadService()

    async def describe_images(self, images: Sequence[ImageInput]) -> list[str]:
        """并行把多张图片转成文字描述。

        - 单张失败返回占位 "[图片识别失败：xxx]"，**不抛异常**，不阻塞整体流程
        - 返回顺序与入参一一对应
        - 实际并发受全局 _VISION_SEMAPHORE 节流
        """
        if not images:
            return []
        t0 = time.perf_counter()
        results = await asyncio.gather(
            *[self._describe_one_image(img, idx) for idx, img in enumerate(images)]
        )
        logger.info(
            f"vision describe_images done: count={len(images)} "
            f"elapsed={time.perf_counter() - t0:.2f}s"
        )
        return results

    async def describe_bytes(
        self, data: bytes, content_type: str, tag: str
    ) -> str:
        """通用接口：从字节流直出描述，供视频抽帧场景直接调用。

        把 `(bytes, content_type)` 转成 data URL 后送 MiMo VLM；
        失败统一压成占位文本（"[图片识别失败：xxx]"），不抛异常。

        Args:
            data: 图片字节（视频帧的 JPEG/PNG 编码、或图片原始字节）
            content_type: MIME 类型，如 "image/jpeg"
            tag: 日志/调试用标识，例如 "img#0(gill.jpg)" 或 "vid#0/frame#1(5s)"

        Returns:
            描述文本或 "[图片识别失败：...]" 占位
        """
        b64 = base64.b64encode(data).decode("ascii")
        data_url = f"data:{content_type};base64,{b64}"

        async with _VISION_SEMAPHORE:
            try:
                t0 = time.perf_counter()
                resp = await self._client.chat.completions.create(
                    model=settings.MIMO_MODEL,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": _VISION_PROMPT},
                                {"type": "image_url", "image_url": {"url": data_url}},
                            ],
                        }
                    ],
                    temperature=0.2,  # 描述任务要稳定，不要发散
                )
                elapsed = time.perf_counter() - t0
            except Exception:
                logger.exception(f"vision {tag}: model call failed")
                return "[图片识别失败：视觉模型异常]"

        msg = (resp.choices[0].message.content or "").strip()
        if not msg:
            logger.warning(f"vision {tag}: empty content returned")
            return "[图片识别失败：返回为空]"

        logger.info(
            f"vision {tag}: ok elapsed={elapsed:.2f}s len={len(msg)} "
            f"bytes={len(data)}"
        )
        return msg

    async def _describe_one_image(self, image: ImageInput, idx: int) -> str:
        """识别单张用户上传图片：先从 MinIO 取字节，再走 describe_bytes。"""
        tag = f"img#{idx}({image.original_filename or image.object_key})"

        try:
            data, _content_type = await self._upload_service.fetch_image_bytes(
                image.object_key
            )
        except Exception:
            logger.exception(f"vision {tag}: fetch_image_bytes failed")
            return "[图片识别失败：无法读取原图]"

        return await self.describe_bytes(data, image.content_type, tag)


# 模块级单例：复用 httpx 连接池
vision_service = VisionService()
