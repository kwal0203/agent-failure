from pydantic import BaseModel, Field
from typing import Literal, Annotated, Union


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
    tool_name: Literal["list_inbox", "read_email"]
    args: dict[str, str] = Field(default_factory=dict)


class TextResponse(BaseModel):
    kind: Literal["text"]
    text: str | None = None


LLMResponse = Annotated[Union[LLMToolCall, TextResponse], Field(discriminator="kind")]
