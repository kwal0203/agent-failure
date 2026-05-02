from apps.agent_harness.src.application.session_loop.ports import (
    ModelClientPort,
    LabContextBuilderPort,
    EventSinkPort,
)
from apps.agent_harness.src.infrastructure.lab_context.service import (
    LabContextBuilder,
)
from apps.agent_harness.src.infrastructure.model.fake_streaming_client import (
    LocalV1ModelClient,
)
from apps.agent_harness.src.infrastructure.event_sink.local_v1 import LocalV1EventSink
from apps.agent_harness.src.infrastructure.model.gateway_client import (
    GatewayModelClient,
)
from apps.agent_harness.src.infrastructure.model.config import load_gateway_config
from apps.agent_harness.src.infrastructure.config.settings import get_model_client_mode


def get_model_client() -> ModelClientPort:
    mode = get_model_client_mode()
    if mode == "gateway":
        return GatewayModelClient(config=load_gateway_config())
    return LocalV1ModelClient()


def get_context_builder() -> LabContextBuilderPort:
    return LabContextBuilder()


def get_event_sink() -> EventSinkPort:
    return LocalV1EventSink()
