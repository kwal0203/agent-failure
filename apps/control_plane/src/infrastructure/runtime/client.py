from apps.control_plane.src.application.runtime.types import (
    RunTurnInput,
    RuntimeClientConfig,
    InjectEmailInput,
    ReadRuntimeFileInput,
    ReadRuntimeFileOutput,
)
from apps.control_plane.src.application.runtime.errors import RuntimeClientError
from apps.control_plane.src.application.runtime.ports import RuntimeClientPort
from apps.contracts.src.schemas import (
    RuntimeStreamEvent,
    RunTurnStreamRequest,
    EmailArtifact,
    ApiErrorEnvelope,
)
from collections.abc import AsyncIterator
from typing import cast

import httpx


from pydantic import BaseModel, TypeAdapter, ValidationError

_event_adapter = cast(TypeAdapter[RuntimeStreamEvent], TypeAdapter(RuntimeStreamEvent))


class _ReadRuntimeFileResponse(BaseModel):
    path: str
    content: str | None = None


def _parse_runtime_stream_event(line: str) -> RuntimeStreamEvent:
    return _event_adapter.validate_json(line)


class RuntimeHttpClient(RuntimeClientPort):
    def __init__(self, config: RuntimeClientConfig) -> None:
        self._config = config

    async def run_turn_stream(
        self, input: RunTurnInput
    ) -> AsyncIterator[RuntimeStreamEvent]:
        request = RunTurnStreamRequest(
            session_id=input.session_id,
            lab_id=input.lab_id,
            lab_version_id=input.lab_version_id,
            turn_id=input.turn_id,
            prompt=input.prompt,
            idempotency_key=input.idempotency_key,
            authority_bulletin_passed=input.authority_bulletin_passed,
        )

        headers: dict[str, str] = {"Accept": "application/x-ndjson"}
        if self._config.auth_token:
            headers["Authorization"] = f"Bearer {self._config.auth_token}"

        try:
            async with httpx.AsyncClient(
                timeout=self._config.timeout_seconds
            ) as client:
                async with client.stream(
                    "POST",
                    f"{self._config.base_url}/runtime/v1/turns/stream",
                    json=request.model_dump(mode="json"),
                    headers=headers,
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line:
                            continue

                        event = _parse_runtime_stream_event(line=line)
                        yield event

        except httpx.TimeoutException as exc:
            raise RuntimeClientError(
                code="RUNTIME_TIMEOUT",
                message="Runtime request timed out",
                retryable=True,
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeClientError(
                code="RUNTIME_UNREACHABLE",
                message="Runtime unreachable",
                retryable=True,
            ) from exc

    async def inject_email(self, input: InjectEmailInput) -> None:
        request = EmailArtifact(
            email_from=input.email_from,
            email_subject=input.email_subject,
            email_body=input.email_body,
            email_preview=input.email_preview,
            email_id=input.email_id,
            malicious=input.malicious,
            urgency_marker=input.urgency_marker,
            source=input.source,
        )

        headers: dict[str, str] = {"Accept": "application/json"}
        if self._config.auth_token:
            headers["Authorization"] = f"Bearer {self._config.auth_token}"

        try:
            async with httpx.AsyncClient(
                timeout=self._config.timeout_seconds
            ) as client:
                resp = await client.post(
                    f"{self._config.base_url}/runtime/v1/sessions/{input.session_id}/inbox/email",
                    json=request.model_dump(mode="json"),
                    headers=headers,
                )

            if 200 <= resp.status_code < 300:
                return

            try:
                err = ApiErrorEnvelope.model_validate(resp.json())
                raise RuntimeClientError(
                    code=err.error.code,
                    message=err.error.message,
                    retryable=err.error.retryable,
                )

            except RuntimeClientError:
                raise

            except Exception as exc:
                raise RuntimeClientError(
                    code="RUNTIME_BAD_RESPONSE",
                    message=f"Unexpected runtime response status: {resp.status_code}",
                    retryable=True,
                ) from exc

        except httpx.TimeoutException as exc:
            raise RuntimeClientError(
                code="RUNTIME_TIMEOUT",
                message="Runtime request timed out",
                retryable=True,
            ) from exc

        except httpx.HTTPError as exc:
            raise RuntimeClientError(
                code="RUNTIME_UNREACHABLE",
                message="Runtime unreachable",
                retryable=True,
            ) from exc

    async def read_runtime_file(
        self, input: ReadRuntimeFileInput
    ) -> ReadRuntimeFileOutput:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._config.auth_token:
            headers["Authorization"] = f"Bearer {self._config.auth_token}"

        try:
            async with httpx.AsyncClient(
                timeout=self._config.timeout_seconds
            ) as client:
                resp = await client.get(
                    f"{self._config.base_url}/runtime/v1/sessions/{input.session_id}/files/read",
                    params={"path": input.path},
                    headers=headers,
                )
        except httpx.TimeoutException as exc:
            raise RuntimeClientError(
                code="RUNTIME_TIMEOUT",
                message="Runtime request timed out",
                retryable=True,
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeClientError(
                code="RUNTIME_UNREACHABLE",
                message="Runtime unreachable",
                retryable=True,
            ) from exc

        if 200 <= resp.status_code < 300:
            try:
                data = _ReadRuntimeFileResponse.model_validate(resp.json())
            except ValidationError as exc:
                raise RuntimeClientError(
                    code="RUNTIME_BAD_RESPONSE",
                    message=f"Invalid runtime file response: {exc}",
                    retryable=True,
                )
            return ReadRuntimeFileOutput(path=data.path, content=data.content)

        raise RuntimeClientError(
            code="RUNTIME_BAD_RESPONSE",
            message=f"Unexpected runtime response status: {resp.status_code}",
            retryable=True,
        )
