from contextvars import ContextVar, Token
from uuid import UUID, uuid4

_correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


def set_correlation_id(value: str | None) -> Token[str]:
    normalized = (value or "").strip()
    if normalized:
        try:
            normalized = str(UUID(normalized))
        except ValueError:
            normalized = str(uuid4())
    else:
        normalized = str(uuid4())
    return _correlation_id_ctx.set(normalized)


def reset_correlation_id(token: Token[str]) -> None:
    _correlation_id_ctx.reset(token)


def get_correlation_id() -> str:
    value = _correlation_id_ctx.get().strip()
    return value or str(uuid4())


def log_fields(
    *,
    session_id: UUID | str | None = None,
    lab_id: UUID | str | None = None,
    principal_id: UUID | str | None = None,
    turn_id: UUID | str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, object]:
    fields: dict[str, object] = {"correlation_id": get_correlation_id()}
    if session_id is not None:
        fields["session_id"] = str(session_id)
    if lab_id is not None:
        fields["lab_id"] = str(lab_id)
    if principal_id is not None:
        fields["principal_id"] = str(principal_id)
    if turn_id is not None:
        fields["turn_id"] = str(turn_id)
    if idempotency_key is not None:
        fields["idempotency_key"] = idempotency_key
    return fields
