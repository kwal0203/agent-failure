# from typing import Iterable

# from apps.control_plane.src.application.common.types import PrincipalContext
# from apps.control_plane.src.application.common.errors import ForbiddenError

# from .types import TraceEvent, TraceFamily


# VisibilityKey = tuple[TraceFamily, str]

# LEARNER_VISIBLE_ALLOWLIST: set[VisibilityKey] = {
#     ("learner", "USER_PROMPT_SUBMITTED"),
#     ("model", "MODEL_TURN_COMPLETED"),
#     ("model", "MODEL_TURN_FAILED"),
# }


# def is_learner_visible(event: TraceEvent) -> bool:
#     return (event.family, event.event_type) in LEARNER_VISIBLE_ALLOWLIST


# def project_learner_visible_events(principal: PrincipalContext, events: Iterable[TraceEvent]) -> tuple[TraceEvent, ...]:
#     if principal.role not in {"learner", "admin"}:
#         raise ForbiddenError(role=principal.role)

#     projected: list[TraceEvent] = []
#     for event in events:
#         if is_learner_visible(event=event):
#             projected.append(event)

#     return tuple(projected)
