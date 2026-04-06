from apps.agent_harness.src.application.session_loop.ports import (
    InboxItem,
    InboxToolPort,
)


class InMemoryInboxTool(InboxToolPort):
    def __init__(self) -> None:
        self._items = [InboxItem("e1", "Team lunch", "hr@corp.com", "Lunch friday", False)]

    def list_inbox(self) -> list[InboxItem]:
        return self._items

    def read_email(self, email_id: str) -> InboxItem | None:
        for x in self._items:
            if x.email_id == email_id:
                return x

        return None

    def receive_email(self, email: InboxItem) -> None:
        if len(self._items) >= 10:
            return None

        self._items.append(email)
