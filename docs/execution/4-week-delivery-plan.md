# 4-Week Delivery Plan (Submission + Product Goal)

## Context
You have 4 weeks to submit the project. For course success, the must-have outcome is:

- 3 runnable labs
- constraint-based modeling detecting learner progress/outcomes for each lab

A stretch outcome is deploying the system to the internet as a product.

## Scope Strategy
Split work into two tracks:

1. Course-critical (must ship): 3 labs + evaluator feedback detection + demo evidence
2. Productization (stretch): internet deployment + operational reliability

## Explicit Deferrals (Post-MVP)
- P1-E6-T2 strict concurrent event-index guarantee (keep current MVP behavior)
- P1-E6-T6 full replay pagination semantics
- P1-E7-T6 terminal-outcome handoff automation
- Auth hardening seed tickets (P2-E2-T10, P2-E2-T11, P2-E0-T1, P2-E0-T2) unless internet launch risk requires them

## Weekly Milestones
- End Week 1: 3-lab evaluator plumbing works
- End Week 2: 3-lab learning detection demoable end-to-end
- End Week 3: internet deployment live and smoke tested
- End Week 4: submission package finalized, only bugfixes/polish

---

## Week 1: Multi-Lab Evaluator Foundation

1. `P1-E6-T5` Learner-visible event filtering
- DoD: centralized allowlist projection, retrieval path uses it, allow/deny tests

2. `P1-E6-T7` Trace schema validation tests (MVP-complete)
- DoD: positive fixtures for emitted families, negative fixtures for malformed payload/context, runs in CI

3. `NEW-E7-LAB-BINDINGS` Add 3-lab binding support
- DoD: registry resolves 3 `(lab_slug, lab_version, evaluator_version)` bundles; unsupported lab/version explicitly rejected

4. `NEW-E7-RULE-CONTRACT` Standardize rule IDs/evidence contract
- DoD: stable rule IDs, deterministic rule order, evidence payload keys documented and tested

## Week 2: Labs 2 and 3 + Detection

1. `NEW-LAB2-RUNTIME` Implement lab 2 runtime behavior
- DoD: launchable + interactive; emits required trace fields for evaluator

2. `NEW-LAB2-EVAL` Implement lab 2 constraint bundle
- DoD: 2-3 rule families with pass/fail tests and evidence snippets

3. `NEW-LAB3-RUNTIME` Implement lab 3 runtime behavior
- DoD: launchable + interactive; emits required trace fields for evaluator

4. `NEW-LAB3-EVAL` Implement lab 3 constraint bundle
- DoD: 2-3 rule families with pass/fail tests and evidence snippets

5. `NEW-DEMO-SCENARIOS` Deterministic trigger scripts
- DoD: scripted/manual steps reliably produce learned/no-progress outcomes for all 3 labs

## Week 3: Internet Deployment

1. `NEW-DEPLOY-INFRA` Deploy API + evaluator + workers + DB + websocket publicly
- DoD: reachable URL, migrations/workers running, restart-safe

2. `NEW-DEPLOY-RUNBOOK` Ops runbook for demo reliability
- DoD: startup order, health checks, failure recovery, required processes documented

3. `NEW-PROD-SMOKE` Public E2E smoke suite
- DoD: create session -> provision -> prompt -> evaluator insert -> learner feedback stream for all 3 labs

## Week 4: Buffer + Submission Pack

1. `NEW-STABILIZATION` Fix only P0/P1 blockers from production tests
- DoD: no critical demo blockers open

2. `NEW-SUBMISSION-EVIDENCE` Build submission artifacts
- DoD: screenshots/log excerpts/tests proving 3 labs + learning detection

3. `NEW-DOC-FINAL` Final architecture + limitations writeup
- DoD: clear constraint-model explanation, known tradeoffs, post-MVP backlog

---

## Working Rules

- If a task does not improve "3 labs + learning detection + reliable demo", defer it.
- Keep one demo branch always green and deployable.
- Any task expected to exceed 1 day should be split into sub-tasks.

## Daily Cadence

1. Build implementation in the morning
2. Run tests and smoke checks in the afternoon
3. End day with a green, demoable state

## Tracking Note

`NEW-*` tasks are execution tasks for deadline delivery where no official backlog ticket currently exists. They can be:

- tracked as sprint subtasks under existing official tickets, or
- promoted into formal tickets in a backlog doc (e.g. P2/P3) for cleaner reporting
