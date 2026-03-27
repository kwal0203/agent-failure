from .ports import EvaluatorPort, EvaluatorLabLookupPort
from .types import (
    EvaluatorTaskInput,
    EvaluatorRunResult,
    EvaluatorFinding,
)  # , EvaluatorOnceResult
from apps.evaluator.src.application.rules.registry import resolve_bundle

import logging

logger = logging.getLogger(__name__)


def build_result_idempotency_key(
    task: EvaluatorTaskInput, finding: EvaluatorFinding
) -> str:
    trigger_ref = (
        str(finding.trigger_event_index)
        if finding.trigger_event_index is not None
        else f"{finding.trigger_start_event_index}:{finding.trigger_end_event_index}"
    )
    return f"eval:{task.session_id}:{task.lab_version_id}:{task.evaluator_version}:{finding.code}:{trigger_ref}"


def evaluate_trace_window_once(
    task: EvaluatorTaskInput,
    repo: EvaluatorPort,
    lab_lookup_repo: EvaluatorLabLookupPort,
) -> EvaluatorRunResult:

    inserted_count = 0
    deduped_count = 0

    try:
        start_event_index = task.start_event_index
        end_event_index = task.end_event_index

        if start_event_index < 0 or end_event_index < start_event_index:
            raise ValueError("Invalid event window")

        events = repo.load_events(input=task)
        if any(
            event.lab_id is not None and event.lab_id != task.lab_id for event in events
        ):
            raise ValueError("Trace event lab_id does not match evaluator task lab_id")

        if any(
            event.lab_version_id is not None
            and event.lab_version_id != task.lab_version_id
            for event in events
        ):
            raise ValueError(
                "Trace event lab_version_id does not match evaluator task lab_version_id"
            )

        if any(event.session_id != task.session_id for event in events):
            raise ValueError(
                "Trace event session_id does not match evaluator task session_id"
            )

        lab_binding = lab_lookup_repo.get_runtime_binding(
            lab_id=task.lab_id, lab_version_id=task.lab_version_id
        )
        constraint_bundle = resolve_bundle(binding=lab_binding, task=task)

        findings: tuple[EvaluatorFinding, ...] = constraint_bundle.run(events=events)
        for finding in findings:
            idempo_key = build_result_idempotency_key(task=task, finding=finding)
            inserted = repo.persist_result_if_new(
                idempo_key=idempo_key,
                session_id=task.session_id,
                lab_id=task.lab_id,
                lab_version_id=task.lab_version_id,
                evaluator_version=task.evaluator_version,
                finding=finding,
            )

            if inserted:
                inserted_count += 1
            else:
                deduped_count += 1

        logger.info(
            "evaluator.results.persisted session_id=%s lab_id=%s lab_version_id=%s evaluator_version=%s findings_count=%s inserted_count=%s deduped_count=%s",
            task.session_id,
            task.lab_id,
            task.lab_version_id,
            task.evaluator_version,
            len(findings),
            inserted_count,
            deduped_count,
        )

        logger.info(
            "evaluator.run.completed session_id=%s lab_id=%s lab_version_id=%s evaluator_version=%s start_event_index=%s end_event_index=%s evaluated_event_count=%s findings_count=%s no_op=%s",
            task.session_id,
            task.lab_id,
            task.lab_version_id,
            task.evaluator_version,
            task.start_event_index,
            task.end_event_index,
            len(events),
            len(findings),
            len(findings) == 0,
        )

        return EvaluatorRunResult(
            session_id=task.session_id,
            lab_id=task.lab_id,
            lab_version_id=task.lab_version_id,
            evaluator_version=task.evaluator_version,
            start_event_index=task.start_event_index,
            end_event_index=task.end_event_index,
            evaluated_event_count=len(events),
            findings_count=len(findings),
            no_op=len(findings) == 0,
            findings=findings,
        )
    except Exception:
        logger.exception(
            "evaluator.run.failed session_id=%s lab_id=%s lab_version_id=%s evaluator_version=%s start_event_index=%s end_event_index=%s",
            task.session_id,
            task.lab_id,
            task.lab_version_id,
            task.evaluator_version,
            task.start_event_index,
            task.end_event_index,
        )
        raise
