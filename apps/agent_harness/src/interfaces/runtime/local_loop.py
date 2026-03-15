from apps.agent_harness.src.application.session_loop.types import (
    HarnessTurnResult,
    HarnessTurnInput,
)
from apps.agent_harness.src.application.session_loop.service import run_single_turn
from .dependencies import get_context_builder, get_event_sink, get_model_client

from dotenv import load_dotenv


load_dotenv()


def run_local_one_turn(turn: HarnessTurnInput) -> HarnessTurnResult:
    model_client = get_model_client()
    event_sink = get_event_sink()
    context_builder = get_context_builder()

    return run_single_turn(
        turn=turn,
        model_client=model_client,
        event_sink=event_sink,
        context_builder=context_builder,
    )
