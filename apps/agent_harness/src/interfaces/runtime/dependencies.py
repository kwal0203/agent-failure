# class ModelClientPort(Protocol):
# class LabContextBuilder(Protocol):
# class EventSinkPort(Protocol):

from apps.agent_harness.src.application.session_loop.ports import (
    ModelClientPort,
    LabContextBuilderPort,
    EventSinkPort,
)
from apps.agent_harness.src.infrastructure.lab_context.local_v1 import (
    LocalV1LabContextBuilder,
)
from apps.agent_harness.src.infrastructure.model.fake_streaming_client import (
    LocalV1ModelClient,
)
from apps.agent_harness.src.infrastructure.event_sink.local_v1 import LocalV1EventSink


def get_model_client() -> ModelClientPort:
    return LocalV1ModelClient()


def get_context_builder() -> LabContextBuilderPort:
    return LocalV1LabContextBuilder()


def get_event_sink() -> EventSinkPort:
    return LocalV1EventSink()
