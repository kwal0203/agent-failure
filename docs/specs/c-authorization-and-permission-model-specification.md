# Authorization and Permission Model Specification

## Purpose

This document defines the authorization model for the AI agent security lab platform. Its purpose is to make access control explicit across learner workflows, administrative workflows, session resources, traces, and operational controls so that the platform can be implemented safely for public deployment.

This specification is lower-level than the PRD and TDD. It describes who may do what, to which resources, under what conditions, and how those decisions must be enforced and audited.

## Scope

This specification covers:

- roles and role semantics
- resources subject to authorization
- permission rules for learner and admin workflows
- ownership rules
- object-level authorization requirements
- administrative boundaries and support access
- authorization decision points in REST and WebSocket flows
- audit requirements for privileged access
- future extensibility for narrower privileged roles

This specification does not define:

- authentication token issuance
- UI copy or product messaging
- exact database schema for roles and permissions
- organization or enterprise tenancy for future B2B use cases

## Core principles

- Authentication proves identity; authorization determines allowed actions.
- The Control Plane is the sole authority for access-control decisions.
- Authorization must be enforced at the resource level, not just at the route level.
- Session IDs, lab IDs, and other identifiers are never themselves proof of access.
- Learners are owner-scoped by default.
- Privileged access is exceptional, role-bound, auditable, and never anonymous.
- Read permissions and write permissions are distinct.
- Administrative capabilities must be narrowly scoped even when implemented under a single `admin` role in V1.
- Authorization decisions must fail closed.

## Authorization model overview

The platform uses role-based access control with owner-scoped access for learner data.

Authorization decisions are based on:

- authenticated user identity
- user account status
- assigned role
- ownership of the target resource where applicable
- current session state or lab state where relevant
- product and incident policy constraints, such as degraded mode

The model is intentionally simple for V1:

- learner
- admin

The implementation should remain extensible so future roles such as instructor, researcher, support-operator, or moderator can be added without changing the core ownership model.

## Roles

### Learner

A learner is a normal end user of the platform.

A learner may:

- view published learner-visible labs
- create sessions for launchable labs, subject to quota and policy
- access only their own sessions, history, traces, and learner-visible feedback
- connect to the live stream for their own sessions
- submit learner prompts to their own interactive sessions

A learner may not:

- access other learners’ sessions, traces, quota state, or history
- invoke administrative actions
- inspect audit logs
- disable labs
- suspend users
- bypass session state or quota restrictions

### Admin

An admin is a privileged platform operator for support, moderation, incident response, and operational control.

An admin may:

- inspect any session, trace, learner-visible history, failure state, or abuse signal for operational purposes
- access admin-only routes and dashboards
- disable labs
- suspend users
- cancel sessions
- inspect audit records according to platform policy
- use degraded-mode controls and other emergency restrictions

An admin may not:

- bypass audit logging for privileged state changes
- impersonate a learner without an explicit, separately designed impersonation mechanism
- access secrets or internal infrastructure through the product API unless separately authorized outside the product authorization model

### Future roles

The V1 design must remain compatible with adding narrower privileged roles later, such as:

- **support operator**: can inspect sessions but not suspend users or disable labs
- **moderator**: can handle abuse-related account or session actions but not broader operational controls
- **instructor/researcher**: may inspect scoped subsets of learner outcomes subject to separate policy

These roles are out of scope for V1 but should not be blocked by the authorization architecture.

## Account status gates

Authorization decisions must consider account status in addition to role.

### Active

The account may act according to its role.

### Suspended

The account may be blocked entirely or limited to non-interactive access according to policy, but must not launch new sessions or submit new prompts.

### Deleted or disabled

The account must be treated as non-operational for product access.

A suspended admin must not retain admin capabilities.

## Resources subject to authorization

Authorization must be enforced at the resource level for at least the following resource classes.

### Lab catalog resources

- published lab metadata
- disabled lab metadata
- lab operational status

### Session resources

- session record
- session state
- session history
- live session stream
- session cancellation action

### Trace and feedback resources

- trace event stream
- persisted trace history
- evaluator outputs
- learner-visible feedback

### User and governance resources

- learner account record
- user suspension action
- quota state
- audit records

### Administrative controls

- lab disable action
- degraded-mode controls
- session termination controls
- support inspection workflows

## Ownership model

Ownership is the default access mechanism for learner-generated resources.

### Ownership rules

- A session is owned by exactly one learner.
- Session history is owned by the same learner who owns the session.
- Trace events are owned by the session owner.
- Learner-visible evaluation results are owned by the session owner.
- A learner may access a resource only if they own it, unless a more privileged role explicitly allows access.

### Ownership inheritance

Resource ownership should be derived whenever possible rather than duplicated arbitrarily. For example:

- access to a trace event should be derived from access to the parent session
- access to learner-visible feedback should be derived from access to the parent session

This reduces drift and authorization bugs.

## Permission matrix

The following matrix describes the intended V1 permissions.

### Labs

| Action | Learner | Admin |
| :---- | :---- | :---- |
| List published labs | Allow | Allow |
| View learner-visible published lab details | Allow | Allow |
| View disabled/internal lab operational details | Deny | Allow |
| Disable a lab | Deny | Allow |

### Sessions

| Action | Learner | Admin |
| :---- | :---- | :---- |
| Create own session | Allow, subject to quota/policy | Allow |
| View own session metadata | Allow | Allow |
| View another learner’s session metadata | Deny | Allow |
| Connect to own live session stream | Allow | Allow |
| Connect to another learner’s live session stream | Deny | Allow |
| Submit prompt to own interactive session | Allow, subject to state/policy | Allow only if future admin-interaction mode is explicitly enabled; otherwise deny |
| Cancel own session | Deny in V1 unless added later | Allow |
| Cancel another learner’s session | Deny | Allow |

### History, traces, and feedback

| Action | Learner | Admin |
| :---- | :---- | :---- |
| View own session history | Allow | Allow |
| View another learner’s session history | Deny | Allow |
| View own trace events | Allow | Allow |
| View another learner’s trace events | Deny | Allow |
| View audit records | Deny | Allow |

### User and operational controls

| Action | Learner | Admin |
| :---- | :---- | :---- |
| View own profile context | Allow | Allow |
| View another user’s account through product API | Deny | Allow where supported |
| Suspend a user | Deny | Allow |
| View quota enforcement on own requests indirectly through errors/status | Allow | Allow |
| Inspect platform abuse signals | Deny | Allow |
| Toggle degraded mode or emergency controls | Deny | Allow |

## Decision rules by resource type

### Lab catalog authorization

- Learners may see only learner-visible labs that are published and not hidden by policy.
- Admins may also see labs that are disabled or internally flagged where an admin interface supports that.
- Lab launchability is a separate decision from lab visibility. A learner might be able to view a lab but be unable to launch it due to degraded mode or policy.

### Session metadata authorization

To authorize access to a session, the Control Plane must verify:

1. the caller is authenticated
2. the target session exists in the product domain
3. the caller either owns the session or holds an admin role
4. account status allows the attempted action

For learners, object-level ownership is mandatory. Route access alone is insufficient.

### Live session stream authorization

To authorize a WebSocket connection for a session stream, the Control Plane must verify:

1. the caller is authenticated
2. the caller either owns the session or is an admin
3. the account is active and not blocked from streaming access
4. the requested stream mode is allowed by role and session state

A successful connection does not grant permission to submit prompts unless the role and session state also allow interactive actions.

### Prompt submission authorization

A learner prompt may be accepted only if:

- caller is authenticated
- caller owns the session
- caller account is active
- session is interactive according to the lifecycle spec
- no session-level concurrency or quota rule blocks the turn
- no incident or degraded-mode restriction blocks learner turns

Admins do not automatically gain permission to send prompts into arbitrary learner sessions. That capability should remain denied in V1 unless explicitly introduced with separate policy and audit semantics.

### Trace authorization

Persisted traces and trace replay endpoints must require ownership or admin privilege.

A learner may not infer another learner’s session existence through trace route behavior. Not-found and forbidden behavior should be designed to minimize unnecessary leakage.

### Audit-log authorization

Audit logs are admin-only resources.

Where possible, audit-log viewers should be separated from ordinary learner-facing APIs even if they share the same Control Plane service.

### User-suspension authorization

Suspending a user is an admin-only action.

The authorization decision must check:

- caller has admin role
- caller account is active
- target user exists
- action is written to the audit log before success is returned

## Administrative-access boundaries

Privileged access exists to support operations, moderation, and incident response. It must still be bounded.

### Allowed reasons for admin inspection

Examples include:

- investigating a failed session
- diagnosing runtime instability
- responding to abuse reports
- handling quota abuse or denial-of-wallet behavior
- reviewing a suspected security incident

### Prohibited assumptions

- Admin access is not “because the role exists”; it is because the operational function requires it.
- Read access does not imply write access to all resources.
- Admin role does not imply permission to act as the learner in session interactions.

### Least-privilege direction

Even if V1 implements a single admin role, internal code paths should distinguish between:

- inspection privileges
- moderation privileges
- operational-control privileges

This makes future role-splitting easier and reduces accidental privilege creep.

## Authorization decision points

Authorization must be enforced at every relevant entry point.

### REST entry points

- before returning lab metadata
- before creating a session
- before returning session metadata
- before returning history or trace data
- before executing admin actions

### WebSocket entry points

- at connect time
- at reconnect time
- before accepting a learner prompt
- before allowing any control-style client message that changes session state

### Background or internal actions

If internal jobs perform actions on behalf of a user or admin workflow, they must do so using explicit service-level authorization rules rather than assuming trust from internal execution alone.

## Failure behavior

Authorization must fail closed.

### Required behavior

- no partial success for unauthorized writes
- unauthorized requests must not mutate resource state
- denied WebSocket prompt submissions must produce explicit denial messages rather than silent drops
- admin actions must not succeed if audit write fails in a way that would undermine required privileged-action logging

### Error behavior

Errors should use stable typed codes such as:

- `UNAUTHENTICATED`
- `FORBIDDEN`
- `RESOURCE_NOT_FOUND`
- `SESSION_NOT_FOUND`
- `SESSION_NOT_INTERACTIVE`

The product may intentionally use `RESOURCE_NOT_FOUND` rather than `FORBIDDEN` in some owner-scoped contexts to reduce object-existence leakage.

## Audit requirements

Authorization-relevant actions must be observable.

### Must be audited

- successful admin session inspection where policy requires inspection logging
- session cancellation by admin
- lab disable action
- user suspension action
- role changes if supported later
- degraded-mode activation or deactivation

### Audit record contents

At minimum:

- actor identity
- actor role
- target resource type
- target resource id
- action type
- timestamp
- reason or metadata where applicable
- result status

### Audit integrity principle

Privileged actions that require audit logging should not report success unless the required audit record has been durably written.

## Security requirements for implementation

- Route-level checks alone are insufficient; object ownership must be checked against the target resource.
- Authorization logic should be centralized in reusable policy functions or middleware plus resource-level checks, not duplicated ad hoc across handlers.
- The frontend must never be trusted to hide or reveal access; the server is authoritative.
- WebSocket connections must undergo the same authorization rigor as REST endpoints.
- Suspended users must not retain cached authorization decisions beyond acceptable revocation windows.

## Extensibility requirements

The authorization model should support future addition of:

- narrower privileged roles
- scoped instructor access
- organization-level tenancy
- delegated support access
- explicit impersonation with separate audit semantics

The V1 implementation should therefore avoid hard-coding assumptions such as “admin can do literally anything” in places where narrower capability checks could be factored cleanly.

## Testing requirements

### Learner ownership tests

- learner can retrieve own session metadata
- learner cannot retrieve another learner’s session metadata
- learner can connect to own session stream
- learner cannot connect to another learner’s session stream
- learner can view own trace history
- learner cannot view another learner’s trace history

### Admin privilege tests

- admin can inspect a learner session
- admin can disable a lab
- admin can suspend a user
- admin action writes an audit record
- admin without active account status cannot perform privileged actions

### Negative tests

- route access without object ownership is rejected
- guessed session identifiers do not bypass ownership checks
- unauthorized WebSocket prompt submissions are denied
- a suspended learner cannot launch new sessions or submit prompts

### Failure-path tests

- admin state-changing action fails safely if required audit persistence fails
- stale cached role data does not allow continued privileged access after suspension beyond allowed revocation windows

## Open implementation choices

The following implementation details may vary provided this authorization contract remains true:

- whether roles are stored directly on the user row or resolved through a separate mapping table
- whether policy checks are implemented with middleware plus resource resolvers, explicit service-layer policy methods, or both
- whether admin inspection reads are themselves fully audit logged in V1 or introduced as a stricter later enhancement

## Summary

This authorization model ensures that learner data is owner-scoped, privileged access is explicit and auditable, administrative controls are bounded, and access decisions are enforced consistently across REST, WebSocket, and operational workflows. Any implementation that relies only on authentication, trusts resource identifiers, or fails to enforce object-level ownership is non-compliant with the platform design.
