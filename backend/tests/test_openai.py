import asyncio

from openai import AsyncOpenAI



async def main():
    client = AsyncOpenAI(
        api_key="sk-wVt796XhyLHhEYFBKx0M1NZ1afYYjqSUTYD6S9DU7ThRW9Ut",
        base_url="https://api.openai-proxy.org/v1",
        timeout=120.0,
    )

    resp_stream = await client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "你是一个专业的鱼医助手，你的任务是根据用户的问题和图片，生成专业的鱼医建议。",
            },
            {
                "role": "user",
                "content": "你好",
            },
        ],
        temperature=0.5,
        stream=True,
    )

    async for chunk in resp_stream:
        # print(chunk)
        if not chunk.choices:
            continue

        delta_content = chunk.choices[0].delta.content
        if not delta_content:
            continue

        print(delta_content, end="", flush=True)




if __name__ == "__main__":
    asyncio.run(main())
