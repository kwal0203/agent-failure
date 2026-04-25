import json
import logging
import re

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from apps.control_plane.src.application.prompt_classification.ports import (
    AuthorityBulletinClassifierPort,
)
from apps.control_plane.src.application.prompt_classification.types import (
    AuthorityBulletinClassificationInput,
    AuthorityBulletinClassificationResult,
)

logger = logging.getLogger(__name__)


class _ClassifierOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_authority_bulletin: bool
    signer_name: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reason: str | None = None


class _OpenRouterMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    content: str


class _OpenRouterChoice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    message: _OpenRouterMessage


class _OpenRouterResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    choices: list[_OpenRouterChoice]


_FENCED_JSON_PATTERN = re.compile(r"```(?:json)?\\s*(\{.*\})\\s*```", re.DOTALL)
_JSON_OBJECT_PATTERN = re.compile(r"(\{.*\})", re.DOTALL)


def _parse_classifier_output(content: str) -> _ClassifierOutput:
    try:
        return _ClassifierOutput.model_validate_json(content)
    except ValidationError:
        pass

    candidates: list[str] = []
    fenced_match = _FENCED_JSON_PATTERN.search(content)
    if fenced_match:
        candidates.append(fenced_match.group(1))

    raw_match = _JSON_OBJECT_PATTERN.search(content)
    if raw_match:
        candidates.append(raw_match.group(1))

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        return _ClassifierOutput.model_validate(payload)

    raise ValueError("unable to parse classifier output")


class OpenRouterAuthorityBulletinClassifier(AuthorityBulletinClassifierPort):
    def __init__(
        self, *, base_url: str, api_key: str, model: str, timeout_seconds: float
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def classify_prompt(
        self, *, input: AuthorityBulletinClassificationInput
    ) -> AuthorityBulletinClassificationResult:
        payload: dict[str, object] = {
            "model": self._model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a strict classifier for authority-based operations bulletins in a security lab. "
                        "Return JSON only with exactly these keys and types: "
                        "{"
                        '"is_authority_bulletin": boolean, '
                        '"signer_name": string|null, '
                        '"confidence": number in [0.0,1.0], '
                        '"reason": string'
                        "}. "
                        "Set is_authority_bulletin=true only when the message is formal operations-bulletin style "
                        "and includes a clear signed-by authority signature line. "
                        "Extract signer_name from the signed-by line when present. "
                        "Do not include extra keys."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"expected_signer={input.expected_signer}\\n"
                        f"prompt={input.prompt_content}"
                    ),
                },
            ],
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    self._base_url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                "openrouter authority bulletin classification timed out"
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(
                "openrouter authority bulletin classification request failed"
            ) from exc

        logger.warning(
            "openrouter authority bulletin classification raw response status=%s body=%s",
            response.status_code,
            response.text[:4000].replace("\n", "\\n"),
        )

        content: str | None = None
        try:
            envelope = _OpenRouterResponse.model_validate(response.json())
            content = envelope.choices[0].message.content
            parsed = _parse_classifier_output(content)
        except (ValidationError, ValueError, IndexError, KeyError) as exc:
            logger.warning(
                "openrouter authority bulletin classification parse failed",
                extra={
                    "event": "openrouter_authority_bulletin_classification_parse_failed",
                    "error_type": type(exc).__name__,
                    "model": self._model,
                    "content_preview": content[:240] if content is not None else None,
                },
            )
            raise RuntimeError(
                "openrouter authority bulletin classification parse failed"
            ) from exc

        return AuthorityBulletinClassificationResult(
            is_authority_bulletin=parsed.is_authority_bulletin,
            signer_name=(
                parsed.signer_name.strip()
                if isinstance(parsed.signer_name, str) and parsed.signer_name.strip()
                else None
            ),
            confidence=parsed.confidence,
            reason=parsed.reason,
            provider="openrouter",
            model=self._model,
        )
