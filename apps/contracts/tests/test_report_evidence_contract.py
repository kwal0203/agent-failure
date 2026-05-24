from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from apps.contracts.src.schemas import (
    GetSessionReportEvidenceResponse,
    ImportSelectedEvidenceResponse,
)


def _item_payload() -> dict[str, object]:
    return {
        "event_id": str(uuid4()),
        "position": 0,
        "title": "Token disclosed",
        "description": "Sensitive token exposed",
        "details": {"channel": "tool"},
        "occurred_at": datetime(2026, 5, 17, 23, 0, 0, tzinfo=timezone.utc).isoformat(),
        "trace_version": 1,
        "event_index": 42,
        "evidence_type": "exploit_outcome",
        "objective_keys": ["lab1.token_disclosed"],
        "why_it_matters": "Direct exploit evidence",
        "default_priority": "high",
        "citation_label": "E1",
        "objective_mapping": [
            {
                "objective_key": "lab1.token_disclosed",
                "label": "Sensitive token disclosure confirmed",
                "rubric_target": "sensitive_data_exposure_outcome",
            }
        ],
        "evidence_strength": "high",
        "student_note": None,
        "report_section": "unassigned",
        "section_position": None,
    }


def test_get_session_report_evidence_response_contract_includes_report_ready_fields() -> (
    None
):
    payload = GetSessionReportEvidenceResponse.model_validate(
        {"items": [_item_payload()]}
    )
    first = payload.items[0]
    assert first.citation_label == "E1"
    assert first.objective_mapping is not None
    assert first.objective_mapping[0].rubric_target == "sensitive_data_exposure_outcome"
    assert first.evidence_strength == "high"


def test_import_selected_evidence_response_contract_includes_report_ready_fields() -> (
    None
):
    payload = ImportSelectedEvidenceResponse.model_validate(
        {"items": [_item_payload()]}
    )
    first = payload.items[0]
    assert first.citation_label == "E1"
    assert first.objective_mapping is not None
    assert first.objective_mapping[0].objective_key == "lab1.token_disclosed"
    assert first.evidence_strength == "high"
