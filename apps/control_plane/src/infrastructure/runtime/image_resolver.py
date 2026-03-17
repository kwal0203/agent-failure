from pathlib import Path
from typing import Any, cast
import yaml

from .errors import (
    DefaultSelectionError,
    ImageNotFoundError,
    ImageRevokedError,
    InvalidImageLockError,
)
from .types import RuntimeImageEntry


class RuntimeImageResolver:
    def __init__(self, lock_file: Path, selection_file: Path) -> None:
        self._lock_file = lock_file
        self._selection_file = selection_file

    def resolve(self, lab_slug: str, lab_version: str) -> str:
        lock_doc = self._load_yaml(self._lock_file)
        selection_doc = self._load_yaml(self._selection_file)
        entries = self._parse_lock_entries(lock_doc)
        requested = self._find_entry(entries, lab_slug, lab_version)

        if requested is None:
            raise ImageNotFoundError(lab_slug, lab_version)

        if requested.status != "active":
            raise ImageRevokedError(lab_slug, lab_version, requested.status)

        if not self._is_digest_pinned(requested.image_ref):
            raise InvalidImageLockError(
                message="Runtime image_ref must be digest pinned",
                details={
                    "default_lab_slug": requested.lab_slug,
                    "default_lab_version": requested.lab_version,
                    "reason": "not_digest_pinned",
                    "image_ref": requested.image_ref,
                },
            )

        self._validate_default_selection(selection_doc, entries)
        return requested.image_ref

    def resolve_default(self) -> RuntimeImageEntry:
        lock_doc = self._load_yaml(self._lock_file)
        selection_doc = self._load_yaml(self._selection_file)
        entries = self._parse_lock_entries(lock_doc)

        default_lab_slug = self._required_str(selection_doc, "default_lab_slug")
        default_lab_version = self._required_str(selection_doc, "default_lab_version")

        default_entry = self._find_entry(entries, default_lab_slug, default_lab_version)
        if default_entry is None:
            raise DefaultSelectionError(
                "Default selection points to missing lock entry "
                f"(lab_slug={default_lab_slug}, lab_version={default_lab_version})"
            )
        if default_entry.status != "active":
            raise DefaultSelectionError(
                "Default selection must point to active entry "
                f"(status={default_entry.status})"
            )
        if not self._is_digest_pinned(default_entry.image_ref):
            raise DefaultSelectionError(
                f"Default image_ref must be digest pinned: {default_entry.image_ref}"
            )

        return default_entry

    def _validate_default_selection(
        self, selection_doc: dict[str, Any], entries: list[RuntimeImageEntry]
    ) -> None:
        default_lab_slug = self._required_str(selection_doc, "default_lab_slug")
        default_lab_version = self._required_str(selection_doc, "default_lab_version")
        default_entry = self._find_entry(entries, default_lab_slug, default_lab_version)

        if default_entry is None:
            raise DefaultSelectionError(
                "Default selection points to missing lock entry "
                f"(lab_slug={default_lab_slug}, lab_version={default_lab_version})"
            )
        if default_entry.status != "active":
            raise DefaultSelectionError(
                "Default selection must point to active entry "
                f"(status={default_entry.status})"
            )
        if not self._is_digest_pinned(default_entry.image_ref):
            raise DefaultSelectionError(
                f"Default image_ref must be digest pinned: {default_entry.image_ref}"
            )

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise InvalidImageLockError(
                message="Runtime image config file not found.",
                details={"file": str(path), "reason": "file_not_found"},
            )

        with path.open("r", encoding="utf-8") as f:
            loaded_any = yaml.safe_load(f)

        if not isinstance(loaded_any, dict):
            raise InvalidImageLockError(
                message="Runtime image config YAML root must be an object.",
                details={"file": str(path), "reason": "invalid_yaml_root"},
            )

        loaded = cast(dict[str, Any], loaded_any)
        return loaded

    @staticmethod
    def _parse_lock_entries(lock_doc: dict[str, Any]) -> list[RuntimeImageEntry]:
        raw_images_obj = lock_doc.get("images")
        if not isinstance(raw_images_obj, list):
            raise InvalidImageLockError(
                message="Lock file 'images' must be a list.",
                details={"field": "images", "reason": "invalid_type"},
            )

        raw_images = cast(list[object], raw_images_obj)
        entries: list[RuntimeImageEntry] = []
        for idx, raw_any in enumerate(raw_images):
            if not isinstance(raw_any, dict):
                raise InvalidImageLockError(
                    message="Each lock image entry must be an object.",
                    details={"entry_index": idx, "reason": "invalid_type"},
                )

            raw = cast(dict[str, Any], raw_any)
            lab_slug = raw["lab_slug"] if "lab_slug" in raw else None
            lab_version = raw["lab_version"] if "lab_version" in raw else None
            image_ref = raw["image_ref"] if "image_ref" in raw else None
            status = raw["status"] if "status" in raw else None

            if not isinstance(lab_slug, str) or not lab_slug:
                raise InvalidImageLockError(
                    message="Invalid 'lab_slug' in lock entry.",
                    details={"entry_index": idx, "field": "lab_slug"},
                )
            if not isinstance(lab_version, str) or not lab_version:
                raise InvalidImageLockError(
                    message="Invalid 'lab_version' in lock entry.",
                    details={"entry_index": idx, "field": "lab_version"},
                )
            if not isinstance(image_ref, str) or not image_ref:
                raise InvalidImageLockError(
                    message="Invalid 'image_ref' in lock entry.",
                    details={"entry_index": idx, "field": "image_ref"},
                )
            if not isinstance(status, str) or not status:
                raise InvalidImageLockError(
                    message="Invalid 'status' in lock entry.",
                    details={"entry_index": idx, "field": "status"},
                )

            entries.append(
                RuntimeImageEntry(
                    lab_slug=lab_slug,
                    lab_version=lab_version,
                    image_ref=image_ref,
                    status=status,
                )
            )

        return entries

    @staticmethod
    def _find_entry(
        entries: list[RuntimeImageEntry], lab_slug: str, lab_version: str
    ) -> RuntimeImageEntry | None:
        for entry in entries:
            if entry.lab_slug == lab_slug and entry.lab_version == lab_version:
                return entry

        return None

    @staticmethod
    def _is_digest_pinned(image_ref: str) -> bool:
        return "@sha256:" in image_ref

    @staticmethod
    def _required_str(doc: dict[str, Any], key: str) -> str:
        value = doc.get(key)
        if not isinstance(value, str) or not value.strip():
            raise DefaultSelectionError(f"Missing/invalid '{key}'")
        return value.strip()
