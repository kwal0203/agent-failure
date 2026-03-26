class TraceValidationError(Exception):
    def __init__(
        self,
        message: str = "Trace event validation failed.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class UnknownTraceFamilyError(TraceValidationError):
    def __init__(
        self,
        family: str,
        message: str = "Unknown trace event family.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.family = family
        self.message = message
        self.details = details or {"family": family}
        super().__init__(self.message, self.details)


class UnknownTraceEventTypeError(TraceValidationError):
    def __init__(
        self,
        family: str,
        event_type: str,
        message: str = "Unknown trace event type for family.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.family = family
        self.event_type = event_type
        self.message = message
        self.details = details or {"family": family, "event_type": event_type}
        super().__init__(self.message, self.details)


class MissingTraceContextError(TraceValidationError):
    def __init__(
        self,
        missing_fields: list[str],
        message: str = "Trace event is missing required context.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.missing_fields = missing_fields
        self.message = message
        self.details = details or {"missing_fields": missing_fields}
        super().__init__(self.message, self.details)


class InvalidTracePayloadError(TraceValidationError):
    def __init__(
        self,
        family: str,
        event_type: str,
        message: str = "Trace event payload is invalid.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.family = family
        self.event_type = event_type
        self.message = message
        self.details = details or {"family": family, "event_type": event_type}
        super().__init__(self.message, self.details)
