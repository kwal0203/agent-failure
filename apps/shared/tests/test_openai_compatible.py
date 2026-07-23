from apps.shared.openai_compatible import api_base_url


def test_api_base_url_strips_chat_completions_path() -> None:
    assert (
        api_base_url("https://openrouter.ai/api/v1/chat/completions")
        == "https://openrouter.ai/api/v1"
    )


def test_api_base_url_preserves_existing_api_root() -> None:
    assert (
        api_base_url("https://openrouter.ai/api/v1/") == "https://openrouter.ai/api/v1"
    )
