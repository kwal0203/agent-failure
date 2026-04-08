from apps.evaluator.src.application.types import (
    EvaluatorLabRuntimeBinding,
    EvaluatorTaskInput,
)

from .types import RuleBundle
from .errors import UnsupportedLabBundleError
from .labs.prompt_injection_v1 import PROMPT_INJECTION_V1_BUNDLE
from .labs.rag_poisoning_v1 import RAG_POISONING_V1_BUNDLE
from .labs.tool_misuse_v1 import TOOL_MISUSE_V1_BUNDLE
from .labs.code_execution_v1 import CODE_EXECUTION_V1_BUNDLE


SUPPORTED_BUNDLES = {
    ("prompt-injection", "v1", 1): PROMPT_INJECTION_V1_BUNDLE,
    ("rag-poisoning", "v1", 1): RAG_POISONING_V1_BUNDLE,
    ("tool-misuse", "v1", 1): TOOL_MISUSE_V1_BUNDLE,
    ("code-execution", "v1", 1): CODE_EXECUTION_V1_BUNDLE,
}


def resolve_bundle(
    *, binding: EvaluatorLabRuntimeBinding, task: EvaluatorTaskInput
) -> RuleBundle:
    key = (binding.lab_slug, binding.lab_version, task.evaluator_version)
    bundle = SUPPORTED_BUNDLES.get(key, None)
    if bundle is not None:
        return bundle

    raise UnsupportedLabBundleError(
        lab_id=task.lab_id,
        lab_version_id=task.lab_version_id,
        evaluator_version=task.evaluator_version,
        message="UNSUPPORTED_LAB_BUNDLE",
        details={
            "lab_slug": binding.lab_slug,
            "lab_version": binding.lab_version,
            "lab_id": str(task.lab_id),
            "lab_difficulty": task.lab_difficulty,
            "evaluator_version": task.evaluator_version,
            "supported_bundle_keys": sorted(SUPPORTED_BUNDLES.keys()),
        },
    )
