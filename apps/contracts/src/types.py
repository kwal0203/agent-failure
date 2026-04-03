from typing import Literal, TypeAlias, Mapping


TraceFamily = Literal["lifecycle", "learner", "runtime", "tool", "model"]


JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
RuntimePayload: TypeAlias = Mapping[str, JSONValue]
