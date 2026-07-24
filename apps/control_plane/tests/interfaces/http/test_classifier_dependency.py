import asyncio

import pytest

from apps.control_plane.src.application.prompt_classification.types import (
    AuthorityBulletinClassificationInput,
)
from apps.control_plane.src.interfaces.http.dependencies import (
    get_authority_bulletin_classifier,
    get_email_classifier_config,
)


def test_authority_classifier_is_noop_when_provider_is_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for variable in ("OPENROUTER_API_KEY", "PROVIDER_ENDPOINT", "MODEL_NAME"):
        monkeypatch.delenv(variable, raising=False)
    get_email_classifier_config.cache_clear()

    classifier = get_authority_bulletin_classifier()
    result = asyncio.run(
        classifier.classify_prompt(
            input=AuthorityBulletinClassificationInput(
                prompt_content="Routine learner prompt",
                expected_signer="Operations",
            )
        )
    )

    assert result.is_authority_bulletin is False
    assert result.reason == "classifier_not_configured"
    assert result.provider == "noop"
    assert result.model == "noop"
