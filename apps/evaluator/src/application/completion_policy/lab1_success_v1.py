from datetime import datetime, timezone

from .ports import SessionCompletionPolicyPort
from .types import CompletionPolicyDecision, CompletionPolicyInput


LAB1_COMPLETION_POLICY_ID = "lab1_success_v1"
LAB1_COMPLETION_SUCCESS_REASON = "ALL_REQUIRED_OBJECTIVES_COMPLETED"


class Lab1SuccessCompletionPolicy(SessionCompletionPolicyPort):
    def evaluate(
        self,
        *,
        input: CompletionPolicyInput,
        evaluated_at: datetime | None = None,
    ) -> CompletionPolicyDecision:
        ts = evaluated_at if evaluated_at is not None else datetime.now(timezone.utc)

        required_objectives = tuple(row for row in input.objectives if row.required)
        missing_required_keys = tuple(
            row.objective_key for row in required_objectives if row.status != "complete"
        )

        metadata: dict[str, object] = {
            "policy_id": LAB1_COMPLETION_POLICY_ID,
            "required_objective_count": len(required_objectives),
            "completed_required_objective_count": len(required_objectives)
            - len(missing_required_keys),
            "missing_required_objective_keys": missing_required_keys,
        }

        if len(missing_required_keys) == 0:
            return CompletionPolicyDecision(
                completion_status="completed_success",
                completed_at=ts,
                completion_reason_code=LAB1_COMPLETION_SUCCESS_REASON,
                decision_metadata=metadata,
            )

        return CompletionPolicyDecision(
            completion_status="in_progress",
            completed_at=None,
            completion_reason_code=None,
            decision_metadata=metadata,
        )
