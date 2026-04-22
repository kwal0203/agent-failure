from .types import (
    CompletionPolicyObjectiveRow,
    LabObjectiveTemplateRow,
    ObjectiveStatus,
    SessionObjectiveStateRow,
)


def resolve_policy_objectives(
    *,
    template_objectives: tuple[LabObjectiveTemplateRow, ...],
    session_objectives: tuple[SessionObjectiveStateRow, ...],
) -> tuple[CompletionPolicyObjectiveRow, ...]:
    """Resolve policy objectives from authoritative templates and session state.

    Template objectives define required-vs-optional semantics for the bound lab
    version. Session-only objectives that are not in templates are treated as
    optional so they cannot block completion decisions.
    """

    status_by_key: dict[str, ObjectiveStatus] = {
        row.objective_key: row.status for row in session_objectives
    }
    pending_status: ObjectiveStatus = "pending"

    resolved: list[CompletionPolicyObjectiveRow] = []
    template_keys: set[str] = set()

    for template_row in sorted(template_objectives, key=lambda row: row.sort_order):
        template_keys.add(template_row.objective_key)
        resolved.append(
            CompletionPolicyObjectiveRow(
                objective_key=template_row.objective_key,
                status=status_by_key.get(template_row.objective_key, pending_status),
                required=template_row.required,
            )
        )

    for session_row in sorted(session_objectives, key=lambda row: row.objective_key):
        if session_row.objective_key in template_keys:
            continue
        resolved.append(
            CompletionPolicyObjectiveRow(
                objective_key=session_row.objective_key,
                status=session_row.status,
                required=False,
            )
        )

    return tuple(resolved)
