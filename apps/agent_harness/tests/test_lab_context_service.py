from uuid import uuid4

from apps.agent_harness.src.application.session_loop.types import HarnessTurnInput
from apps.agent_harness.src.infrastructure.lab_context.prompts import (
    SYSTEM_PROMPT_EASY,
    SYSTEM_PROMPT_MEDIUM,
)
from apps.agent_harness.src.infrastructure.lab_context.service import LabContextBuilder
from apps.agent_harness.src.interfaces.runtime.dependencies import get_context_builder


def _turn(prompt: str = "summarize inbox") -> HarnessTurnInput:
    return HarnessTurnInput(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        prompt=prompt,
    )


def test_lab_context_builder_uses_easy_prompt_when_env_is_easy(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LAB_DIFFICULTY", "easy")
    builder = LabContextBuilder()

    messages = builder.build_messages(_turn(prompt="hello"))

    assert messages[0].role == "system"
    assert messages[0].content == SYSTEM_PROMPT_EASY
    assert messages[1].role == "user"
    assert messages[1].content == "hello"


def test_lab_context_builder_uses_medium_prompt_when_env_is_medium(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LAB_DIFFICULTY", "medium")
    builder = LabContextBuilder()

    messages = builder.build_messages(_turn())

    assert messages[0].role == "system"
    assert messages[0].content == SYSTEM_PROMPT_MEDIUM


def test_lab_context_builder_defaults_to_medium_when_env_is_unknown(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LAB_DIFFICULTY", "unknown-tier")
    builder = LabContextBuilder()

    messages = builder.build_messages(_turn())

    assert messages[0].role == "system"
    assert messages[0].content == SYSTEM_PROMPT_MEDIUM


def test_get_context_builder_returns_lab_context_builder() -> None:
    builder = get_context_builder()
    assert isinstance(builder, LabContextBuilder)
