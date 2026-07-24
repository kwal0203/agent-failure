# Evaluator Model

Agent Failure evaluates lab traces with deterministic constraints inspired by
constraint-based modeling (CBM). The evaluator is deliberately a small,
project-specific kernel rather than a general tutoring framework.

## Why deterministic constraints

The labs assess security-sensitive, observable behavior. A trace either
contains evidence such as a tool call, an untrusted artifact entering model
context, or a payment reaching a noncanonical account, or it does not.
Deterministic assessment provides:

- reproducible results for the same rule bundle and trace;
- exact trace evidence for every emitted finding;
- reviewable failure conditions and regression tests;
- stable idempotency and historical provenance;
- fail-closed behavior for unsupported lab or rule-bundle versions.

An LLM-as-judge would make these core outcomes probabilistic, harder to audit,
and dependent on model and prompt changes outside the recorded rule-bundle
version. It is therefore not used to decide trace facts or constraint status.

The Prompt Injection lab does use a schema-constrained classifier for learner
explanations and as a fallback when a direct-disclosure prompt cannot be
recognized deterministically. Those annotations are inputs to the constraint
model; they do not replace trace-based evaluation. Invalid or unavailable
classifier output falls back conservatively.

## Evaluation pipeline

1. `TraceIndex` creates immutable indexes over the ordered trace window.
2. A lab-specific solution-state builder converts indexed events into typed,
   normalized observations.
3. Each CBM constraint evaluates relevance and, only when relevant,
   satisfaction.
4. Constraint evidence records trace indexes and normalized facts without
   learner-facing text.
5. A versioned pedagogical policy decides which satisfied or violated outcomes
   are visible and maps them to the stable finding contract.
6. The feedback catalog selects learner-facing text from the resulting reason
   code.

This separation keeps factual assessment independent from instructional
presentation. Changing wording does not change scoring, and changing a
constraint does not require embedding prose in rule code.

## Constraint semantics

Relevance and satisfaction have separate meanings:

- Relevance asks whether an obligation or prohibition applies to the current
  typed lab solution state.
- Satisfaction asks whether the applicable obligation was met or the
  applicable prohibition was respected.
- Evidence records the normalized trace facts that support the assessed
  outcome. It does not decide how that outcome is presented.

The V1 bundles contain lab-wide behavioral constraints, so their relevance
predicates validate the expected typed solution state and then hold for the
duration of that lab. Their satisfaction predicates are dynamic:

- an obligation is satisfied when its required safe observation exists;
- a prohibition is satisfied while its unsafe observation is absent and is
  violated when that observation exists.

An absent safe observation therefore produces a real violated assessment, and
an absent unsafe observation produces a real satisfied assessment. The
pedagogical policy intentionally suppresses those opposite outcomes when V1
did not historically emit a learner-facing finding. This preserves the
published finding contract without confusing presentation policy with factual
assessment.

Rules with repeatable evidence assess one constraint status and project that
status once for each normalized evidence occurrence. This retains exact trace
indexes and repeated-finding behavior without placing learner-facing text in
the assessment layer.

## Rule-bundle versioning

`rule_bundle_version` records which scoring logic produced a result. Callers
cannot select it. The evaluator registry derives the bundle from the persisted
lab slug and lab version and rejects unsupported combinations.

Increment the rule-bundle version when relevance, satisfaction, evidence, or
finding behavior changes materially. Retain an earlier bundle when queued work
or historical reproducibility requires it. A behavior-preserving refactor does
not require a version increment.

## Adding or changing a constraint

1. Add the stable constraint ID and exact evidence contract.
2. Extend the lab's typed solution state when a reusable trace interpretation
   is needed.
3. Define when the constraint is relevant to that typed state.
4. Implement a satisfaction predicate for the obligation or prohibition,
   using a normalized evidence observer where trace support is required.
5. Add the constraint's presentation to the versioned pedagogical policy.
6. Add characterization tests for relevant, irrelevant, satisfied, violated,
   temporal, malformed, and repeated-event cases.
7. Update or add learner-facing feedback independently.

Policy coverage and bundle-structure tests fail if a registered constraint
lacks presentation policy or if a bundle returns to handwritten finding
construction.

## Intentional limitations

The regex predicates are conservative and only recognize characterized
phrasing. They should be expanded alongside tests rather than silently
generalized. Multiple relevant constraints may produce multiple findings for
one trace; completion and feedback precedence remain separate policy concerns.
Unsupported labs and versions fail closed rather than falling back to a generic
judge.
