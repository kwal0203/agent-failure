"""Session lifecycle state machine definitions.

This module contains durable lifecycle states, transition triggers, and the
allowed transition table used by the Control Plane.
"""

from pydantic import BaseModel
from enum import Enum


class SessionState(str, Enum):
    """Durable lifecycle states for a session."""

    CREATED = "CREATED"
    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class Trigger(str, Enum):
    """Domain events that can trigger lifecycle transitions."""

    ADMIN_CANCELLED = "ADMIN_CANCELLED"
    LAUNCH_SUCCEEDED = "LAUNCH_SUCCEEDED"
    LAUNCH_FAILED = "LAUNCH_FAILED"
    PROVISIONING_SUCCEEDED = "PROVISIONING_SUCCEEDED"
    PROVISIONING_FAILED = "PROVISIONING_FAILED"
    PROVISIONING_MAX_TIME = "PROVISIONING_MAX_TIME"
    IDLE_MAX_TIME = "IDLE_MAX_TIME"
    SESSION_MAX_TIME = "SESSION_MAX_TIME"
    RECONNECT = "RECONNECT"
    LAB_COMPLETED = "LAB_COMPLETED"
    LAB_FAILED = "LAB_FAILED"
    RUNTIME_FAILED = "RUNTIME_FAILED"


class Rule(BaseModel):
    """Represents one allowed state-transition rule.

    Attributes:
        next_state: The durable state entered after a valid trigger.
    """

    next_state: SessionState


# Terminal states intentionally map to empty dictionaries (no outgoing edges).
TRANSITIONS: dict[SessionState, dict[Trigger, Rule]] = {
    SessionState.CREATED: {
        Trigger.LAUNCH_SUCCEEDED: Rule(next_state=SessionState.PROVISIONING),
        Trigger.LAUNCH_FAILED: Rule(next_state=SessionState.FAILED),
        Trigger.ADMIN_CANCELLED: Rule(next_state=SessionState.CANCELLED),
    },
    SessionState.PROVISIONING: {
        Trigger.PROVISIONING_SUCCEEDED: Rule(next_state=SessionState.ACTIVE),
        Trigger.PROVISIONING_FAILED: Rule(next_state=SessionState.FAILED),
        Trigger.PROVISIONING_MAX_TIME: Rule(next_state=SessionState.EXPIRED),
        Trigger.ADMIN_CANCELLED: Rule(next_state=SessionState.CANCELLED),
    },
    SessionState.ACTIVE: {
        Trigger.IDLE_MAX_TIME: Rule(next_state=SessionState.IDLE),
        Trigger.LAB_COMPLETED: Rule(next_state=SessionState.COMPLETED),
        Trigger.LAB_FAILED: Rule(next_state=SessionState.FAILED),
        Trigger.RUNTIME_FAILED: Rule(next_state=SessionState.FAILED),
        Trigger.SESSION_MAX_TIME: Rule(next_state=SessionState.EXPIRED),
        Trigger.ADMIN_CANCELLED: Rule(next_state=SessionState.CANCELLED),
    },
    SessionState.IDLE: {
        Trigger.RECONNECT: Rule(next_state=SessionState.ACTIVE),
        Trigger.LAB_COMPLETED: Rule(next_state=SessionState.COMPLETED),
        Trigger.LAB_FAILED: Rule(next_state=SessionState.FAILED),
        Trigger.RUNTIME_FAILED: Rule(next_state=SessionState.FAILED),
        Trigger.SESSION_MAX_TIME: Rule(next_state=SessionState.EXPIRED),
        Trigger.ADMIN_CANCELLED: Rule(next_state=SessionState.CANCELLED),
    },
    SessionState.COMPLETED: {},
    SessionState.FAILED: {},
    SessionState.EXPIRED: {},
    SessionState.CANCELLED: {},
}
