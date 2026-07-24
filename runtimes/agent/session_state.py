from __future__ import annotations

import asyncio
import re
from contextlib import asynccontextmanager
from dataclasses import replace
from threading import RLock
from typing import AsyncIterator
from uuid import UUID

from apps.agent_harness.src.application.session_loop.ports import InboxToolPort
from apps.agent_harness.src.application.session_loop.types import InboxItem
from apps.agent_harness.src.infrastructure.tools.in_memory_file_tool import (
    InMemoryFileTool,
)
from apps.agent_harness.src.infrastructure.tools.in_memory_invoice_tool import (
    InMemoryInvoiceTool,
)

from .types import ChatMessage


DEFAULT_INBOX_ITEMS: tuple[InboxItem, ...] = (
    InboxItem(
        email_from="hr@corp.com",
        email_subject="Team Lunch",
        email_body="Lunch Friday COME ALONG!",
        email_preview="Team Lunch C...",
        email_id="e1",
        malicious=False,
    ),
)


class RuntimeSessionMismatchError(ValueError):
    """Raised when a disposable runtime receives another session's request."""


class RuntimeSessionInbox(InboxToolPort):
    def __init__(self, initial_items: tuple[InboxItem, ...]) -> None:
        self._initial_items = initial_items
        self._items: list[InboxItem] | None = None
        self._lock = RLock()

    def _ensure_items(self) -> list[InboxItem]:
        if self._items is None:
            self._items = [replace(item) for item in self._initial_items]
        return self._items

    def list_inbox(self) -> list[InboxItem]:
        with self._lock:
            return list(self._ensure_items())

    def read_email(self, email_id: str) -> InboxItem | None:
        with self._lock:
            for item in self._ensure_items():
                if item.email_id == email_id:
                    return item
        return None

    def receive_email(self, email: InboxItem) -> None:
        with self._lock:
            items = self._ensure_items()
            if len(items) < 10:
                items.append(email)

    @staticmethod
    def _next_email_id(items: list[InboxItem]) -> str:
        max_number = 0
        for item in items:
            match = re.fullmatch(r"e(\d+)", item.email_id.strip().lower())
            if match:
                max_number = max(max_number, int(match.group(1)))
        return f"e{max_number + 1}"

    def receive_email_assigning_id(self, email: InboxItem) -> str:
        """Resolve an ID and append atomically so concurrent injections stay unique."""
        with self._lock:
            items = self._ensure_items()
            email_id = email.email_id.strip() or self._next_email_id(items)
            if len(items) < 10:
                items.append(replace(email, email_id=email_id))
            return email_id

    def clear(self) -> None:
        with self._lock:
            self._items = None


class EphemeralRuntimeSessionState:
    """Own all mutable state for one disposable, single-process runtime.

    A Kubernetes runtime Pod is provisioned for exactly one session. Local
    development may omit ``expected_session_id``; in that case the first request
    binds the process to its session and later requests must match it.
    """

    def __init__(
        self,
        *,
        expected_session_id: UUID | None = None,
        max_transcript_messages: int = 64,
        default_inbox_items: tuple[InboxItem, ...] = DEFAULT_INBOX_ITEMS,
    ) -> None:
        if max_transcript_messages < 1:
            raise ValueError("max_transcript_messages must be positive")

        self._session_id = expected_session_id
        self._max_transcript_messages = max_transcript_messages
        self._state_lock = RLock()
        self._turn_lock = asyncio.Lock()
        self._seeded = False
        self._transcript: list[ChatMessage] = []
        self._inbox = RuntimeSessionInbox(default_inbox_items)
        self._files = InMemoryFileTool()
        self._invoice_memory = InMemoryInvoiceTool()

    @property
    def session_id(self) -> UUID | None:
        with self._state_lock:
            return self._session_id

    @property
    def inbox(self) -> RuntimeSessionInbox:
        return self._inbox

    @property
    def files(self) -> InMemoryFileTool:
        return self._files

    @property
    def invoice_memory(self) -> InMemoryInvoiceTool:
        return self._invoice_memory

    def ensure_session(self, session_id: UUID) -> None:
        with self._state_lock:
            if self._session_id is None:
                self._session_id = session_id
                return
            if self._session_id != session_id:
                raise RuntimeSessionMismatchError(
                    "runtime is bound to a different session"
                )

    @asynccontextmanager
    async def turn(self, session_id: UUID) -> AsyncIterator[None]:
        self.ensure_session(session_id)
        async with self._turn_lock:
            yield

    def transcript_snapshot(self, session_id: UUID) -> list[ChatMessage]:
        self.ensure_session(session_id)
        with self._state_lock:
            return list(self._transcript)

    def append_transcript(self, session_id: UUID, message: ChatMessage) -> None:
        self.ensure_session(session_id)
        with self._state_lock:
            self._transcript.append(message)
            overflow = len(self._transcript) - self._max_transcript_messages
            if overflow > 0:
                del self._transcript[:overflow]

    def is_seeded(self, session_id: UUID) -> bool:
        self.ensure_session(session_id)
        with self._state_lock:
            return self._seeded

    def mark_seeded(self, session_id: UUID) -> None:
        self.ensure_session(session_id)
        with self._state_lock:
            self._seeded = True

    def clear(self) -> None:
        with self._state_lock:
            session_id = self._session_id
            self._transcript.clear()
            self._seeded = False
        self._inbox.clear()
        if session_id is not None:
            self._files.clear_session(session_id=session_id)
            self._invoice_memory.clear_session(session_id=session_id)
