from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import Literal, Annotated, Union, cast
from apps.contracts.src.types import ToolName, CANONICAL_TOOL_ARGS_REQUIRED


MessageRole = Literal["system", "user", "assistant", "tool"]


class ModelClientChatMessage(BaseModel):
    role: MessageRole
    content: str


class ModelClientRequest(BaseModel):
    model: str
    messages: list[ModelClientChatMessage]
    stream: bool = True


class StreamDelta(BaseModel):
    content: str | None = None


class StreamChoice(BaseModel):
    delta: StreamDelta


class StreamChunk(BaseModel):
    choices: list[StreamChoice]


class LLMToolCall(BaseModel):
    kind: Literal["tool_call"]
    tool_name: ToolName
    args: dict[str, str] = Field(default_factory=dict)

    @field_validator("args")
    @classmethod
    def _validate_required_args(
        cls, value: dict[str, str], info: ValidationInfo
    ) -> dict[str, str]:
        tool_name = info.data.get("tool_name")
        if not isinstance(tool_name, str):
            return value
        if tool_name not in CANONICAL_TOOL_ARGS_REQUIRED:
            return value

        required = CANONICAL_TOOL_ARGS_REQUIRED[cast(ToolName, tool_name)]
        missing = [
            key
            for key in required
            if key not in value
            or not isinstance(value.get(key), str)
            or not value.get(key, "").strip()
        ]
        if missing:
            missing_csv = ", ".join(missing)
            raise ValueError(
                f"missing required tool args for {tool_name}: {missing_csv}"
            )
        return value


class TextResponse(BaseModel):
    kind: Literal["text"]
    text: str | None = None


LLMResponse = Annotated[Union[LLMToolCall, TextResponse], Field(discriminator="kind")]
