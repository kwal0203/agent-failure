from typing import Literal, TypeAlias, Mapping


TraceFamily = Literal["lifecycle", "learner", "runtime", "tool", "model"]


JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
RuntimePayload: TypeAlias = Mapping[str, JSONValue]


# Canonical runtime tool contract shared across runtime/control-plane/evaluator.
ToolName = Literal["list_inbox", "read_email", "read_file", "delete_file"]

CANONICAL_TOOL_ARGS_REQUIRED: Mapping[ToolName, tuple[str, ...]] = {
    "list_inbox": (),
    "read_email": ("email_id",),
    "read_file": ("path",),
    "delete_file": ("path",),
}
