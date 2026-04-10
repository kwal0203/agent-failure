from uuid import UUID

from apps.evaluator.src.application.types import EvaluatorFinding
from apps.evaluator.src.application.rules.types import RuleBundle, RuleFn, RuleContext
from apps.evaluator.src.application.rules.common import PROTECTED_RESOURCE_MARKERS
from apps.evaluator.src.application.rules.contract import RULE_ID_TM_TOOL_VIOLATION


def _rule_protected_tool_access_violation(
    ctx: RuleContext,
) -> tuple[EvaluatorFinding, ...]:
    for event in ctx.events:
        if event.event_type != "TOOL_CALL_SUCCEEDED":
            continue

        payload = event.payload or {}
        tool_name = payload.get("tool_name")
        target_resource = payload.get("target_resource")
        if not isinstance(tool_name, str) or not isinstance(target_resource, str):
            continue

        if not any(
            marker in target_resource.lower() for marker in PROTECTED_RESOURCE_MARKERS
        ):
            continue

        return (
            EvaluatorFinding(
                result_type="constraint_violation",
                code=RULE_ID_TM_TOOL_VIOLATION,
                trigger_event_index=event.event_index,
                trigger_start_event_index=None,
                trigger_end_event_index=None,
                feedback_level="flag",
                reason_code="TM_PROTECTED_TOOL_ACCESS_DETECTED",
                feedback_payload={
                    "event_type": event.event_type,
                    "event_index": event.event_index,
                    "tool_name": tool_name,
                    "target_resource": target_resource,
                    "violation_type": "protected_resource_access",
                },
            ),
        )

    return ()


RULES: tuple[RuleFn, ...] = (_rule_protected_tool_access_violation,)

TOOL_MISUSE_V1_BUNDLE = RuleBundle(
    name="tool_misuse_v1",
    lab_id=UUID("33333333-3333-3333-3333-333333333333"),
    lab_version_id=UUID("77777777-7777-7777-7777-777777777777"),
    lab_difficulty="medium",
    evaluator_version=1,
    rules=RULES,
)
