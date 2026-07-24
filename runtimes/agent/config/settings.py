from uuid import UUID

from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    runtime_shared_token: str = ""
    runtime_session_id: UUID | None = None


def get_runtime_settings() -> RuntimeSettings:
    return RuntimeSettings()


def get_runtime_shared_token() -> str:
    return get_runtime_settings().runtime_shared_token.strip()
