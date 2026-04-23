from apps.control_plane.src.application.session_completion.guard import (
    evaluate_completion_transition,
)


def test_transition_from_in_progress_to_completed_success_is_allowed() -> None:
    decision = evaluate_completion_transition(
        current_status="in_progress",
        requested_status="completed_success",
    )

    assert decision.should_apply is True
    assert decision.reason == "allowed_in_progress_to_terminal"


def test_transition_from_in_progress_to_completed_failure_is_allowed() -> None:
    decision = evaluate_completion_transition(
        current_status="in_progress",
        requested_status="completed_failure",
    )

    assert decision.should_apply is True
    assert decision.reason == "allowed_in_progress_to_terminal"


def test_repeated_same_completion_status_is_no_op() -> None:
    decision = evaluate_completion_transition(
        current_status="completed_success",
        requested_status="completed_success",
    )

    assert decision.should_apply is False
    assert decision.reason == "no_op_same_status"


def test_transition_out_of_completed_state_is_blocked() -> None:
    decision = evaluate_completion_transition(
        current_status="completed_success",
        requested_status="completed_failure",
    )

    assert decision.should_apply is False
    assert decision.reason == "terminal_status_is_immutable"


def test_transition_back_to_in_progress_is_blocked() -> None:
    decision = evaluate_completion_transition(
        current_status="completed_failure",
        requested_status="in_progress",
    )

    assert decision.should_apply is False
    assert decision.reason == "terminal_status_is_immutable"
