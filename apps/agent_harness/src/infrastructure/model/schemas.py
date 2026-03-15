from pydantic import BaseModel
from typing import Literal


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
