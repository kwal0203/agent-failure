from typing import Iterable
from pydantic import ValidationError

from apps.agent_harness.src.application.session_loop.ports import ModelClientPort
from apps.agent_harness.src.application.session_loop.types import (
    HarnessChunk,
    ModelRequest,
)

from apps.agent_harness.src.application.session_loop.errors import (
    SessionLoopProviderFailureError,
)

from .errors import (
    ProviderAuthError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from .types import GatewayConfig
from .schemas import ModelClientRequest, ModelClientChatMessage, StreamChunk

import httpx
import json


class GatewayModelClient(ModelClientPort):
    def __init__(self, config: GatewayConfig) -> None:
        self._config = config

    def stream(self, payload: ModelRequest) -> Iterable[HarnessChunk]:
        request_body = ModelClientRequest(
            model=self._config.model,
            messages=[
                ModelClientChatMessage(role=m.role, content=m.content)
                for m in payload.messages
            ],
        )

        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            try:
                with httpx.Client(timeout=self._config.timeout_seconds) as client:
                    with client.stream(
                        "POST",
                        self._config.endpoint,
                        headers=headers,
                        json=request_body.model_dump(mode="json"),
                    ) as resp:
                        if resp.status_code in (401, 403):
                            raise ProviderAuthError(
                                details={"status_code": str(resp.status_code)}
                            )
                        if resp.status_code >= 400:
                            raise ProviderResponseError(
                                details={"status_code": str(resp.status_code)}
                            )

                        for line in resp.iter_lines():
                            if not line:
                                continue
                            if not line.startswith("data:"):
                                continue

                            data = line.removeprefix("data:").strip()
                            if data == "[DONE]":
                                break

                            try:
                                chunk = StreamChunk.model_validate_json(data)
                            except (ValidationError, json.JSONDecodeError) as exc:
                                raise ProviderResponseError(
                                    message="Malformed provider stream chunk",
                                    details={
                                        "raw_chunk": data[:500],
                                        "error": str(exc),
                                    },
                                ) from exc

                            delta = (
                                chunk.choices[0].delta.content
                                if chunk.choices
                                else None
                            )
                            if delta:
                                yield HarnessChunk(content=delta, final=False)

                yield HarnessChunk(content="", final=True)
            except httpx.TimeoutException as exc:
                raise ProviderTimeoutError(details={"error": str(exc)}) from exc
            except httpx.HTTPError as exc:
                raise ProviderUnavailableError(details={"error": str(exc)}) from exc

        except ProviderTimeoutError as exc:
            raise SessionLoopProviderFailureError(
                message="Provider request timed out", details=exc.details
            ) from exc
        except ProviderUnavailableError as exc:
            raise SessionLoopProviderFailureError(
                message="Provider unavailable", details=exc.details
            ) from exc
        except ProviderAuthError as exc:
            raise SessionLoopProviderFailureError(
                message="Provider authentication failed", details=exc.details
            ) from exc
        except ProviderResponseError as exc:
            raise SessionLoopProviderFailureError(
                message="Provider returned invalid response", details=exc.details
            ) from exc
        except Exception as exc:
            raise SessionLoopProviderFailureError(
                message="Model provider request failed", details={"error": str(exc)}
            ) from exc
