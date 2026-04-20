from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuthClaims:
    sub: str
    email: str | None
    roles: tuple[str, ...]
    scopes: tuple[str, ...]
    issued_at: datetime | None
    expires_at: datetime | None
