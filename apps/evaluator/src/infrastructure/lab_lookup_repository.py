from uuid import UUID
from sqlalchemy.orm import Session

from apps.evaluator.src.application.ports import EvaluatorLabLookupPort
from apps.evaluator.src.application.types import EvaluatorLabRuntimeBinding


class SQLAlchemyEvaluatorLabLookupRepository(EvaluatorLabLookupPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_runtime_binding(
        self, lab_id: UUID, lab_version_id: UUID | None
    ) -> EvaluatorLabRuntimeBinding:
        # TODO(P1-E7 follow-up): This static lab_id -> (slug, version) mapping is a
        # temporary hack until lab/lab_version metadata is durably persisted and
        # queryable from DB. Replace with a real SELECT-backed lookup keyed by
        # (lab_id, lab_version_id), and remove hardcoded UUID constants.
        _ = lab_version_id  # until version table exists

        bindings: dict[UUID, EvaluatorLabRuntimeBinding] = {
            UUID("11111111-1111-1111-1111-111111111111"): EvaluatorLabRuntimeBinding(
                lab_slug="prompt-injection",
                lab_version="v1",
            ),
            UUID("22222222-2222-2222-2222-222222222222"): EvaluatorLabRuntimeBinding(
                lab_slug="rag-poisoning",
                lab_version="v1",
            ),
            UUID("33333333-3333-3333-3333-333333333333"): EvaluatorLabRuntimeBinding(
                lab_slug="tool-misuse",
                lab_version="v1",
            ),
        }

        binding = bindings.get(lab_id)
        if binding is None:
            raise ValueError(f"Unsupported lab_id for runtime binding: {lab_id}")

        return binding
