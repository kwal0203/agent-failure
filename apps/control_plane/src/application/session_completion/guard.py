from dataclasses import dataclass

from .types import (
    COMPLETION_STATUS_IN_PROGRESS,
    TERMINAL_COMPLETION_STATUSES,
    CompletionStatus,
)


@dataclass(frozen=True)
class CompletionTransitionDecision:
    should_apply: bool
    reason: str


def evaluate_completion_transition(
    *,
    current_status: CompletionStatus,
    requested_status: CompletionStatus,
) -> CompletionTransitionDecision:
    if current_status == requested_status:
        return CompletionTransitionDecision(
            should_apply=False,
            reason="no_op_same_status",
        )

    if current_status in TERMINAL_COMPLETION_STATUSES:
        return CompletionTransitionDecision(
            should_apply=False,
            reason="terminal_status_is_immutable",
        )

    if requested_status == COMPLETION_STATUS_IN_PROGRESS:
        return CompletionTransitionDecision(
            should_apply=False,
            reason="cannot_transition_back_to_in_progress",
        )

    if requested_status in TERMINAL_COMPLETION_STATUSES:
        return CompletionTransitionDecision(
            should_apply=True,
            reason="allowed_in_progress_to_terminal",
        )

    return CompletionTransitionDecision(
        should_apply=False,
        reason="unsupported_transition",
    )
