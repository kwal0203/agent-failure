from apps.evaluator.src.application.types import (
    EvaluatorLabRuntimeBinding,
    EvaluatorTaskInput,
)

from .types import RuleBundle
from .prompt_injection_v1 import PROMPT_INJECTION_V1_BUNDLE
from .errors import UnsupportedLabBundleError


SUPPORTED_BUNDLE_KEY = ("prompt-injection", "v1", 1)


# def resolve_bundle(task: EvaluatorTaskInput) -> RuleBundle:
def resolve_bundle(
    *, binding: EvaluatorLabRuntimeBinding, task: EvaluatorTaskInput
) -> RuleBundle:
    key = (binding.lab_slug, binding.lab_version, task.evaluator_version)
    if key == SUPPORTED_BUNDLE_KEY:
        return PROMPT_INJECTION_V1_BUNDLE

    raise UnsupportedLabBundleError(
        lab_id=task.lab_id,
        lab_version_id=task.lab_version_id,
        evaluator_version=task.evaluator_version,
        message="UNSUPPORTED_LAB_BUNDLE",
        details={
            "lab_slug": binding.lab_slug,
            "lab_version": binding.lab_version,
            "lab_id": str(task.lab_id),
            "evaluator_version": task.evaluator_version,
            "supported_bundle_key": SUPPORTED_BUNDLE_KEY,
        },
    )
