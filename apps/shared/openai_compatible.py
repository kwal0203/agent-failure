from openai import AsyncOpenAI, OpenAI


_CHAT_COMPLETIONS_SUFFIX = "/chat/completions"


def api_base_url(provider_endpoint: str) -> str:
    """Convert a configured chat-completions endpoint into an SDK API base URL."""

    normalized = provider_endpoint.rstrip("/")
    if normalized.endswith(_CHAT_COMPLETIONS_SUFFIX):
        return normalized[: -len(_CHAT_COMPLETIONS_SUFFIX)]
    return normalized


def build_client(
    *,
    provider_endpoint: str,
    api_key: str,
    timeout_seconds: float,
) -> OpenAI:
    return OpenAI(
        api_key=api_key,
        base_url=api_base_url(provider_endpoint),
        timeout=timeout_seconds,
    )


def build_async_client(
    *,
    provider_endpoint: str,
    api_key: str,
    timeout_seconds: float,
) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=api_key,
        base_url=api_base_url(provider_endpoint),
        timeout=timeout_seconds,
    )
