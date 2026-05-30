"""手动测试 rag_search 工具。

用法（在 backend 目录下执行）：
    uv run python tests/test_rag_search.py              # 跑全部
    uv run python tests/test_rag_search.py basic        # 只跑基础查询
    uv run python tests/test_rag_search.py modes        # 跑所有 mode
    uv run python tests/test_rag_search.py history      # 测对话历史注入
    uv run python tests/test_rag_search.py concurrent   # 测并发
    uv run python tests/test_rag_search.py retry        # 测重试（用 mock）
    uv run python tests/test_rag_search.py stability    # 串行 10 次测稳定性
    uv run python tests/test_rag_search.py custom "你的查询"  # 自定义查询

依赖前置：
- LightRAG 服务在 settings.LIGHTRAG_BASE_URL（默认 http://localhost:9621）已启动
- .env.dev 里 LIGHTRAG_API_KEY 正确
"""
import asyncio
import sys
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx

from fish_med_agent.agents.tools import RAGSearchTool


# ---------- 输出辅助 ----------

def header(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print("=" * 70)


def fmt_result(elapsed: float, result: dict[str, Any], prefix: str = "") -> str:
    if "error" in result:
        return f"{prefix}{elapsed:6.2f}s  ❌ {result['error']}"
    chunks = len(result.get("chunks", []))
    refs = len(result.get("references", []))
    return f"{prefix}{elapsed:6.2f}s  ✅ chunks={chunks:>3} refs={refs}"


async def timed_call(tool: RAGSearchTool, **kwargs: Any) -> tuple[float, dict[str, Any]]:
    t0 = time.time()
    result = await tool.execute(**kwargs)
    return time.time() - t0, result


# ---------- 测试用例 ----------

async def test_basic() -> None:
    header("基础查询：默认 mode=mix")
    tool = RAGSearchTool()
    try:
        elapsed, result = await timed_call(tool, query="草鱼烂鳃病")
        print(fmt_result(elapsed, result))
        # 打印前 2 条 chunk 预览
        for i, c in enumerate(result.get("chunks", [])[:2]):
            print(f"  [chunk {i}] source={c.get('source')}")
            print(f"    {c.get('content', '')[:120]}...")
    finally:
        await tool.aclose()


async def test_modes() -> None:
    header("所有 mode 各跑一次")
    tool = RAGSearchTool()
    try:
        for mode in ["naive", "local", "global", "hybrid", "mix"]:
            elapsed, result = await timed_call(tool, query="草鱼烂鳃病", mode=mode)
            print(fmt_result(elapsed, result, prefix=f"  mode={mode:7}"))
    finally:
        await tool.aclose()


async def test_history() -> None:
    header("conversation_history 注入测试")
    tool = RAGSearchTool()
    try:
        history = [
            {"role": "user", "content": "我家草鱼最近死了好几条"},
            {"role": "assistant", "content": "请描述一下症状和水温"},
            {"role": "user", "content": "鳃部发白，水温 28 度"},
        ]
        print(f"  注入 history 共 {len(history)} 条")
        elapsed, result = await timed_call(
            tool, query="草鱼鳃部发白 治疗", mode="mix",
            conversation_history=history,
        )
        print(fmt_result(elapsed, result, prefix="  with history    "))

        elapsed, result = await timed_call(tool, query="草鱼鳃部发白 治疗", mode="mix")
        print(fmt_result(elapsed, result, prefix="  without history "))
        print("  （查日志 'history_turns=N' 确认注入数量）")
    finally:
        await tool.aclose()


async def test_invalid_mode() -> None:
    header("非法 mode 测试（应自动 fallback 到默认 mix）")
    tool = RAGSearchTool()
    try:
        elapsed, result = await timed_call(tool, query="草鱼烂鳃病", mode="invalid_xxx")
        print(fmt_result(elapsed, result, prefix="  invalid mode "))
        print("  （查日志 'invalid mode ... fallback to mix' 确认 fallback）")
    finally:
        await tool.aclose()


async def test_concurrent() -> None:
    header("并发 5 路 mix 查询")
    tool = RAGSearchTool()
    try:
        async def one(idx: int) -> str:
            elapsed, result = await timed_call(tool, query="草鱼烂鳃病", mode="mix")
            return fmt_result(elapsed, result, prefix=f"  [p{idx + 1}]  ")
        results = await asyncio.gather(*[one(i) for i in range(5)])
        for r in results:
            print(r)
    finally:
        await tool.aclose()


async def test_stability() -> None:
    header("串行 10 次稳定性（看是否会有偶发 5xx）")
    tool = RAGSearchTool()
    ok = 0
    fail = 0
    try:
        for i in range(10):
            elapsed, result = await timed_call(tool, query="草鱼烂鳃病", mode="mix")
            print(fmt_result(elapsed, result, prefix=f"  [{i + 1:>2}]  "))
            if "error" in result:
                fail += 1
            else:
                ok += 1
        print(f"\n  汇总：成功 {ok}/10，失败 {fail}/10")
    finally:
        await tool.aclose()


async def test_retry() -> None:
    """用 mock 验证重试逻辑。不需要真实 LightRAG。"""
    header("重试逻辑测试（mock httpx，不打真实服务）")

    # Case A: 持续 503
    print("\n  [A] 持续 503：应调用 3 次，总耗时 ~1.5s")
    tool = RAGSearchTool()
    mock_resp = MagicMock(status_code=503, text="upstream timeout")
    tool._client.post = AsyncMock(return_value=mock_resp)
    t0 = time.time()
    result = await tool.execute(query="test")
    print(f"      call_count={tool._client.post.call_count} elapsed={time.time() - t0:.2f}s")
    print(f"      result={result}")
    await tool.aclose()

    # Case B: 503 → 200
    print("\n  [B] 第 1 次 503，第 2 次 200：应调用 2 次")
    tool = RAGSearchTool()
    success = MagicMock(status_code=200)
    success.json = MagicMock(return_value={
        "status": "success",
        "data": {"chunks": [], "references": []},
    })
    fail = MagicMock(status_code=503, text="upstream timeout")
    tool._client.post = AsyncMock(side_effect=[fail, success])
    t0 = time.time()
    result = await tool.execute(query="test")
    print(f"      call_count={tool._client.post.call_count} elapsed={time.time() - t0:.2f}s")
    print(f"      result.error={result.get('error')}")
    await tool.aclose()

    # Case C: 网络异常（TimeoutException）
    print("\n  [C] 持续 ReadTimeout：应调用 3 次")
    tool = RAGSearchTool()
    tool._client.post = AsyncMock(side_effect=httpx.ReadTimeout("timed out"))
    t0 = time.time()
    result = await tool.execute(query="test")
    print(f"      call_count={tool._client.post.call_count} elapsed={time.time() - t0:.2f}s")
    print(f"      result={result}")
    await tool.aclose()

    # Case D: 422 不重试
    print("\n  [D] 422：应只调用 1 次")
    tool = RAGSearchTool()
    mock_resp = MagicMock(status_code=422, text="validation failed")
    tool._client.post = AsyncMock(return_value=mock_resp)
    t0 = time.time()
    result = await tool.execute(query="test")
    print(f"      call_count={tool._client.post.call_count} elapsed={time.time() - t0:.2f}s")
    print(f"      result={result}")
    await tool.aclose()


async def test_custom(query: str) -> None:
    header(f"自定义查询: {query!r}")
    tool = RAGSearchTool()
    try:
        elapsed, result = await timed_call(tool, query=query, mode="mix")
        print(fmt_result(elapsed, result))
        for i, c in enumerate(result.get("chunks", [])[:3]):
            print(f"\n  [chunk {i}] source={c.get('source')}")
            print(f"    {c.get('content', '')[:300]}")
    finally:
        await tool.aclose()


# ---------- 入口 ----------

ALL_TESTS = {
    "basic": test_basic,
    "modes": test_modes,
    "history": test_history,
    "invalid": test_invalid_mode,
    "concurrent": test_concurrent,
    "stability": test_stability,
    "retry": test_retry,
}


async def main() -> None:
    if len(sys.argv) == 1:
        # 跑全部
        for name, fn in ALL_TESTS.items():
            await fn()
    elif sys.argv[1] == "custom":
        if len(sys.argv) < 3:
            print("用法: ... custom '你的查询语句'")
            sys.exit(1)
        await test_custom(sys.argv[2])
    elif sys.argv[1] in ALL_TESTS:
        await ALL_TESTS[sys.argv[1]]()
    else:
        print(f"未知测试: {sys.argv[1]}")
        print(f"可选: {', '.join(ALL_TESTS.keys())}, custom")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
