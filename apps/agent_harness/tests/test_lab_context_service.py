from uuid import uuid4

from apps.agent_harness.src.application.session_loop.types import HarnessTurnInput
from apps.agent_harness.src.infrastructure.lab_context.prompts import SYSTEM_PROMPT
from apps.agent_harness.src.infrastructure.lab_context.service import LabContextBuilder
from apps.agent_harness.src.interfaces.runtime.dependencies import get_context_builder


def _turn(prompt: str = "summarize inbox") -> HarnessTurnInput:
    return HarnessTurnInput(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        prompt=prompt,
    )


def test_lab_context_builder_uses_canonical_prompt() -> None:
    builder = LabContextBuilder()

    messages = builder.build_messages(_turn(prompt="hello"))

    assert messages[0].role == "system"
    assert messages[0].content == SYSTEM_PROMPT
    assert messages[1].role == "user"
    assert messages[1].content == "hello"


def test_get_context_builder_returns_lab_context_builder() -> None:
    builder = get_context_builder()
    assert isinstance(builder, LabContextBuilder)
