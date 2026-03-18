from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeImageEntry:
    lab_slug: str
    lab_version: str
    image_ref: str
    status: str
