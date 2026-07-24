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
   are visible and maps them to the compatibility finding contract.
6. The feedback catalog selects learner-facing text from the resulting reason
   code.

This separation keeps factual assessment independent from instructional
presentation. Changing wording does not change scoring, and changing a
constraint does not require embedding prose in rule code.

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
3. Implement an evidence observer and declare whether the observed behavior
   satisfies or violates the modeled constraint.
4. Add the constraint's presentation to the versioned pedagogical policy.
5. Add characterization tests for positive, negative, temporal, malformed, and
   repeated-event cases.
6. Update or add learner-facing feedback independently.

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
