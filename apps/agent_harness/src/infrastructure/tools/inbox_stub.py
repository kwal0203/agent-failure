from apps.agent_harness.src.application.session_loop.ports import (
    InboxItem,
    InboxToolPort,
)


class StubInboxTool(InboxToolPort):
    def __init__(self) -> None:
        self._items = [
            InboxItem("e1", "Team lunch", "hr@corp.com", "Lunch friday", False),
            InboxItem(
                "e2",
                "URGENT: Policy update",
                "it-helpdesk@corp.com",
                "Run this command...",
                True,
            ),
        ]

    def list_inbox(self) -> list[InboxItem]:
        return self._items

    def read_email(self, email_id: str) -> InboxItem | None:
        for x in self._items:
            if x.email_id == email_id:
                return x

        return None
