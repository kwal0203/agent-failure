from uuid import uuid4

from apps.evaluator.src.application.completion_policy.lab1_success_v1 import (
    Lab1SuccessCompletionPolicy,
)
from apps.evaluator.src.application.completion_policy.objective_resolution import (
    resolve_policy_objectives,
)
from apps.evaluator.src.application.completion_policy.types import (
    CompletionPolicyInput,
    LabObjectiveTemplateRow,
    SessionObjectiveStateRow,
)


def test_resolution_uses_authoritative_template_order_and_requirement() -> None:
    resolved = resolve_policy_objectives(
        template_objectives=(
            LabObjectiveTemplateRow(objective_key="obj_b", sort_order=1),
            LabObjectiveTemplateRow(objective_key="obj_a", sort_order=0),
            LabObjectiveTemplateRow(
                objective_key="obj_c",
                sort_order=2,
                required=False,
            ),
        ),
        session_objectives=(
            SessionObjectiveStateRow(objective_key="obj_a", status="complete"),
            SessionObjectiveStateRow(objective_key="obj_b", status="pending"),
            SessionObjectiveStateRow(objective_key="obj_c", status="complete"),
        ),
    )

    assert tuple(row.objective_key for row in resolved) == ("obj_a", "obj_b", "obj_c")
    assert tuple(row.required for row in resolved) == (True, True, False)


def test_resolution_treats_session_only_objectives_as_optional() -> None:
    resolved = resolve_policy_objectives(
        template_objectives=(
            LabObjectiveTemplateRow(objective_key="required_obj", sort_order=0),
        ),
        session_objectives=(
            SessionObjectiveStateRow(objective_key="required_obj", status="complete"),
            SessionObjectiveStateRow(
                objective_key="extra_optional_obj",
                status="pending",
            ),
        ),
    )

    assert tuple(row.objective_key for row in resolved) == (
        "required_obj",
        "extra_optional_obj",
    )
    assert resolved[0].required is True
    assert resolved[1].required is False

    policy = Lab1SuccessCompletionPolicy()
    decision = policy.evaluate(
        input=CompletionPolicyInput(
            session_id=uuid4(),
            lab_id=uuid4(),
            lab_version_id=uuid4(),
            objectives=resolved,
        )
    )

    assert decision.completion_status == "completed_success"


def test_resolution_defaults_missing_template_objective_state_to_pending() -> None:
    resolved = resolve_policy_objectives(
        template_objectives=(
            LabObjectiveTemplateRow(objective_key="required_obj", sort_order=0),
        ),
        session_objectives=(),
    )

    assert len(resolved) == 1
    assert resolved[0].objective_key == "required_obj"
    assert resolved[0].required is True
    assert resolved[0].status == "pending"
