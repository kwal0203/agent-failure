from apps.evaluator.src.application.types import (
    EvaluatorLabRuntimeBinding,
    EvaluatorTaskInput,
)

from .types import RuleBundle
from .errors import UnsupportedLabBundleError
from .labs.prompt_injection_v1 import PROMPT_INJECTION_V1_BUNDLES_BY_DIFFICULTY
from .labs.tool_misuse_v1 import TOOL_MISUSE_V1_BUNDLE
from .labs.code_execution_v1 import CODE_EXECUTION_V1_BUNDLE
from .labs.memory_poisoning_v1 import MEMORY_POISONING_V1_BUNDLE


SUPPORTED_BUNDLES: dict[tuple[str, str, int], dict[str, RuleBundle]] = {
    ("prompt-injection", "v1", 1): PROMPT_INJECTION_V1_BUNDLES_BY_DIFFICULTY,
    ("agent-prompt-injection", "v1", 1): PROMPT_INJECTION_V1_BUNDLES_BY_DIFFICULTY,
    ("tool-misuse", "v1", 1): {"medium": TOOL_MISUSE_V1_BUNDLE},
    ("agent-tool-misuse", "v1", 1): {"medium": TOOL_MISUSE_V1_BUNDLE},
    ("code-execution", "v1", 1): {"medium": CODE_EXECUTION_V1_BUNDLE},
    ("memory-poisoning", "v1", 1): {"medium": MEMORY_POISONING_V1_BUNDLE},
    ("agent-memory-poisoning", "v1", 1): {"medium": MEMORY_POISONING_V1_BUNDLE},
}


def resolve_bundle(
    *, binding: EvaluatorLabRuntimeBinding, task: EvaluatorTaskInput
) -> RuleBundle:
    key = (binding.lab_slug, binding.lab_version, task.evaluator_version)
    bundles = SUPPORTED_BUNDLES.get(key)
    if bundles is None:
        raise UnsupportedLabBundleError(
            lab_id=task.lab_id,
            lab_version_id=task.lab_version_id,
            lab_difficulty=task.lab_difficulty,
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

    bundle = bundles.get(task.lab_difficulty) or bundles.get("medium")
    if bundle is None:
        raise UnsupportedLabBundleError(
            lab_id=task.lab_id,
            lab_version_id=task.lab_version_id,
            lab_difficulty=task.lab_difficulty,
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

    return bundle
