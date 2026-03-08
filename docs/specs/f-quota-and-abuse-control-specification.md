# Quota and Abuse Control Specification

## Purpose

This document defines the quota model, abuse-detection boundaries, enforcement points, and operator controls for the AI agent security lab platform. Its purpose is to make the public system resilient against denial-of-wallet attacks, scripted session spam, excessive model usage, and destabilizing user behavior while keeping the learner experience predictable and auditable.

This specification is lower-level than the PRD and TDD. It describes what usage must be limited, where limits are enforced, how quota state is tracked, how suspicious activity is detected, how denials are surfaced to users, and what administrative controls are available when the platform is under stress or abuse.

## Scope

This specification covers:

- quota goals and design principles  
- resource classes subject to quota or rate limiting  
- per-user, per-session, and platform-level limits  
- abuse-detection signals  
- enforcement points in REST and WebSocket flows  
- user-visible denial behavior  
- operator-visible signals and controls  
- degraded-mode policies  
- audit requirements for administrative interventions  
- testing requirements

This specification does not define:

- payment or billing systems  
- fraud scoring beyond what is needed for V1 operational protection  
- advanced account reputation models  
- legal abuse-report workflows outside the product control plane

## Core principles

- Public usage must be bounded before it becomes expensive or destabilizing.  
- Quota enforcement is part of product correctness, not only infrastructure hygiene.  
- Enforcement must happen before costly work is performed where feasible.  
- Denials must be explicit, typed, and safe for client handling.  
- Abuse detection may be probabilistic, but hard quota enforcement must be deterministic.  
- Operator controls must be available to contain incidents without requiring full platform shutdown.  
- Quota and abuse controls must fail closed when critical supporting systems are unavailable.  
- Administrative interventions must be auditable.

## Goals

- prevent session-launch spam  
- prevent excessive concurrent runtime creation  
- prevent runaway prompt volume within a session  
- reduce exposure to denial-of-wallet behavior against model providers  
- preserve fair access for normal learners during load or attack  
- provide a graded set of defenses before full degraded mode is necessary  
- give operators visibility into abnormal usage and clear containment levers

## Protected resource classes

The platform must protect at least the following resource classes.

### Session-launch capacity

Launching a session consumes orchestrator work, compute capacity, and often model-backed interaction potential.

### Active runtime capacity

Too many concurrent live sessions can exhaust cluster capacity or degrade latency.

### Learner-turn and prompt volume

Repeated prompt submission can create disproportionate provider spend and evaluator load.

### Model usage budget

Model calls are a direct cost and latency dependency.

### Evaluation-pipeline capacity

A flood of trace activity can overwhelm asynchronous evaluators and degrade feedback timeliness.

### Administrative stability

Admin endpoints and operational controls must remain usable even during attack conditions.

## Resource-control types

The platform uses several distinct control types.

### Hard quotas

Hard quotas are deterministic and block an action immediately when the limit is exceeded.

Examples:

- max session launches per user per rolling window  
- max concurrently active sessions per user  
- max prompts per session per rolling window  
- max session duration

### Rate limits

Rate limits bound request frequency over short windows.

Examples:

- session-launch requests per minute per user  
- session-launch requests per minute per IP  
- prompt submissions per minute per session  
- WebSocket reconnect attempts per minute

### Budget guards

Budget guards are spend-oriented protections.

Examples:

- estimated token budget per session  
- estimated daily model budget per user  
- platform-wide emergency provider budget ceiling

### Heuristic abuse controls

These controls rely on suspicious-pattern detection rather than only deterministic counts.

Examples:

- repeated launch-fail-relaunch cycles  
- repeated quota-boundary probing  
- bursty sign-in plus launch behavior  
- many accounts from one origin pattern if available to the platform  
- unusual prompt volume with low completion engagement

## Enforcement surfaces

Quota and abuse controls must be enforced at multiple surfaces.

### Edge or API ingress

Used for coarse request-frequency protection, such as per-IP or per-user REST rate limiting.

### Control Plane request handling

Used for deterministic session-launch checks, session concurrency checks, and state-aware prompt admission checks.

### WebSocket prompt path

Used to reject excessive prompt frequency or overlapping turn attempts before the Agent Harness performs expensive work.

### Orchestrator admission path

Used for platform-wide runtime-capacity checks or emergency lab-specific launch blocks.

### Provider-usage guard path

Used to stop or degrade expensive model activity when per-session, per-user, or platform budget thresholds are reached.

## Quota objects and dimensions

Quota state should be attributable to a principal and a resource dimension.

### Principals

- user id  
- session id  
- IP or origin signal where available and policy allows  
- platform-global budget bucket  
- lab-specific bucket for expensive or unstable labs

### Dimensions

- launches  
- active sessions  
- prompts  
- model requests  
- estimated tokens  
- evaluator tasks  
- reconnect attempts

## Recommended V1 quotas

These are initial design targets and may be tuned in implementation.

### Per-user launch quotas

- maximum session launches per rolling hour  
- maximum session launches per rolling day  
- maximum concurrently active sessions

### Per-session interaction quotas

- maximum prompts per minute  
- maximum prompts per rolling session window  
- maximum turn duration  
- maximum total session duration

### Per-user model budget

- estimated daily token or request budget  
- optional per-lab stricter budgets for expensive labs

### Platform protection limits

- maximum total concurrent active runtimes  
- maximum new launches admitted per minute platform-wide under normal mode  
- lower caps under degraded mode

### Admin carve-out

Administrative access to support and containment routes should not be blocked by the same learner-facing quotas, though admin actions may still be rate-limited separately for safety.

## Quota-state semantics

### Source of truth

The Control Plane is authoritative for deterministic quota decisions.

### Counter semantics

Quota counters should be based on durable or at least strongly consistent-enough state for the protected action.

Examples:

- launch quota increments when a session-creation request is accepted into provisioning  
- active-session quota counts sessions in interactive or resumable states according to policy  
- prompt quota increments on prompt acceptance, not on attempted but denied prompt submissions unless the policy explicitly tracks probing

### Window semantics

The system may use rolling windows, fixed windows, or token-bucket style controls, but behavior must be stable and documented for client-facing denial semantics.

### Failure behavior

If the quota store or required counter path is unavailable for a critical decision, the platform should fail closed for expensive actions such as new launches rather than admitting unlimited work.

## Session-launch admission rules

Before admitting a new session launch, the Control Plane must check at least:

- caller is authenticated and authorized  
- account is active  
- lab is launchable  
- per-user launch quota  
- per-user active-session cap  
- per-IP or origin rate limit where applicable  
- platform-wide launch-capacity status  
- lab-specific disable state  
- degraded-mode restrictions

If any of these checks fail, the platform must reject the launch before provisioning begins.

## Prompt-admission rules

Before accepting a learner prompt over the session stream, the Control Plane must check at least:

- caller is authorized for the session  
- session is interactive according to lifecycle rules  
- no overlapping learner turn is already active  
- per-session prompt-rate limit  
- per-session prompt-count quota  
- per-user or per-session model budget guard  
- degraded-mode restrictions for interactive turns if any

Prompt denials must occur before the Agent Harness begins model work where feasible.

## Budget-guard behavior

### Session-level budget guard

The platform may maintain an estimated usage budget per session. When the session reaches its budget ceiling, additional prompts may be denied or the session may be forced into a non-interactive terminal or expired state according to policy.

### User-level budget guard

The platform may maintain a daily or rolling model-usage budget per user. Once exceeded, new prompts or launches may be denied until the window resets or an admin intervention occurs.

### Platform-level budget guard

If platform-wide model usage exceeds a defined emergency threshold, the system may:

- block launches for high-cost labs  
- reduce concurrency  
- disable non-essential feedback paths  
- enter degraded mode

## Abuse-signal detection

The initial system should detect and surface at least the following suspicious patterns.

### Launch spam

- repeated launch attempts over short windows  
- many failed or abandoned launches from the same principal  
- repeated launch attempts against disabled labs

### Prompt flooding

- unusually high prompt frequency in a session  
- repeated prompt submission while prior turns are still active  
- repeated prompt submissions that end quickly without meaningful progression

### Denial probing

- repeated triggering of the same quota or policy denial  
- repetitive attempts to access blocked capabilities

### Resource churn

- many reconnect attempts in a short period  
- repeated create/fail/create loops for the same lab or user

### Population-level anomalies

- sudden spikes in launch volume  
- sudden spike in provider token consumption  
- abrupt increase in evaluator backlog tied to a narrow user or lab cohort

The V1 system does not need a complex ML abuse classifier, but it must surface these patterns operationally.

## User-visible denial behavior

Denials must be explicit and typed.

### REST denial examples

- `RATE_LIMITED`  
- `QUOTA_EXCEEDED`  
- `DEGRADED_MODE_RESTRICTION`  
- `LAB_NOT_AVAILABLE`

### WebSocket denial examples

- `QUOTA_ERROR`  
- `POLICY_DENIAL`  
- `SYSTEM_ERROR` where platform-wide degraded mode or provider ceiling is involved

### Client-display requirements

- denial messages must be understandable without exposing sensitive internal thresholds where disclosure would weaken protection  
- retryable vs non-retryable behavior should be signaled clearly  
- repeated denials must not silently disconnect the learner without explanation unless abuse policy explicitly calls for termination

## Degraded-mode policy

The platform must support operator-triggered and optionally automatic degraded modes.

### Normal mode

All published learner workflows operate subject to standard quotas and rate limits.

### Mild degraded mode

Possible actions:

- lower session-launch throughput  
- lower max active sessions per user  
- lower prompt-frequency ceilings  
- disable selected expensive labs  
- slow or suppress non-essential evaluator feedback while preserving core trace capture

### Severe degraded mode

Possible actions:

- block new learner launches platform-wide  
- allow only existing interactive sessions to drain  
- suspend some or all new prompt acceptance  
- keep admin inspection and containment routes available

### Mode authority

Only authorized admins or explicitly designed automatic controls may enter degraded mode. Any mode change must be auditable.

## Administrative controls

Admins must have access to bounded intervention controls.

### User-level controls

- suspend user  
- cancel active sessions  
- optionally place a user under stricter quota policy if supported later

### Lab-level controls

- disable a lab  
- reduce allowed concurrency for a lab  
- block new launches for a specific lab version

### Platform-level controls

- enable degraded mode  
- disable all new launches  
- apply emergency provider budget caps  
- inspect abuse dashboards and denial rates

## Audit requirements

The following actions must be auditable:

- user suspension  
- session cancellation for abuse or containment reasons  
- lab disable action  
- degraded-mode activation or deactivation  
- changes to emergency budget or concurrency settings where exposed through admin workflows

Audit records should include:

- actor identity  
- actor role  
- action type  
- target resource  
- timestamp  
- reason metadata where applicable  
- result status

## Metrics and observability

The platform should emit at least the following metrics.

### Quota metrics

- launch denials by reason  
- prompt denials by reason  
- active-session cap denials  
- token-budget denials  
- per-lab denial rate

### Abuse metrics

- suspicious launch-spam events  
- suspicious prompt-flood events  
- repeated denial-probing counts  
- reconnect-storm counts

### Capacity metrics

- active runtimes  
- launches per minute  
- provider request rate  
- estimated token consumption rate  
- evaluator backlog depth

### Incident metrics

- degraded-mode activations  
- time spent in degraded mode  
- admin interventions by type

## Security and correctness invariants

- Expensive work must not begin before required quota checks are performed where feasible.  
- A denied launch must not create a new runtime.  
- A denied prompt must not trigger model execution.  
- Quota decisions must be tied to authenticated and authorized principals whenever possible.  
- Admin controls must not bypass audit requirements.  
- Degraded mode must preserve operator access for containment.  
- Learner-facing quotas must never accidentally block core administrative containment paths.

## Testing requirements

### Launch-control tests

- user exceeding launch quota is denied before provisioning  
- per-user active-session cap blocks additional launches  
- disabled labs remain blocked even if quota would otherwise allow launch  
- degraded mode blocks launches according to configured severity

### Prompt-control tests

- per-session prompt-rate limit blocks excess prompts  
- overlapping turn attempts are denied before model work begins  
- session budget guard stops further interaction after ceiling reached  
- denial responses are typed and explicit

### Abuse-path tests

- repeated denial probing increments abuse signals  
- repeated create/fail/create patterns surface an abuse or instability signal  
- reconnect storms trigger rate limiting or operator visibility

### Failure-path tests

- quota-store outage fails closed for launch admission  
- provider emergency budget mode reduces or blocks expensive actions  
- admin intervention writes audit records and changes enforcement behavior immediately or within acceptable propagation bounds

## Open implementation choices

The following implementation details may vary as long as this contract remains true:

- whether quotas are tracked in PostgreSQL, Redis, or a hybrid design  
- whether token usage is exact or estimated for fast-path budget guarding  
- whether some degraded-mode triggers are automatic, manual, or hybrid  
- whether abuse signals are rule-based only in V1 or later supplemented with more advanced scoring

## Summary

This specification ensures that the AI agent security lab platform can bound costly and destabilizing public behavior before it harms reliability, budget, or fair access. Any implementation that launches runtimes before checking admission limits, allows prompt floods to reach the model unchecked, lacks degraded-mode controls, or performs state-changing administrative interventions without auditability is non-compliant with the platform design.  
