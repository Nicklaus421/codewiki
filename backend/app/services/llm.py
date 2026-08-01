"""DeepSeek LLM 客户端（OpenAI 兼容协议），带并发限制与重试。"""
import asyncio
import logging

from ..config import get_settings

logger = logging.getLogger(__name__)

_client = None
_sem: asyncio.Semaphore | None = None


class LlmUnavailable(RuntimeError):
    pass


def llm_available() -> bool:
    return bool(get_settings().deepseek_api_key)


def get_llm_client():
    global _client, _sem
    if _client is not None:
        return _client
    settings = get_settings()
    if not settings.deepseek_api_key:
        return None
    try:
        from openai import AsyncOpenAI
    except ImportError as e:  # pragma: no cover
        raise LlmUnavailable("未安装 openai SDK") from e
    _client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
    )
    _sem = asyncio.Semaphore(settings.llm_concurrency)
    return _client


async def complete(system: str, user: str) -> str:
    """调用 DeepSeek 生成 markdown。失败抛出异常，由调用方兜底。"""
    client = get_llm_client()
    if client is None:
        raise LlmUnavailable("未配置 DEEPSEEK_API_KEY")
    settings = get_settings()
    assert _sem is not None
    async with _sem:
        resp = await client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=settings.llm_temperature,
            max_tokens=4096,
        )
    content = resp.choices[0].message.content or ""
    return content.strip()
