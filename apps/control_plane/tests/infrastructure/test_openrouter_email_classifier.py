from apps.control_plane.src.infrastructure.classification.openrouter_email_classifier import (
    _ClassifierOutput,
    _OpenRouterResponse,
    _derive_malicious,
    _parse_classifier_output,
)


def _output(
    *,
    verdict: str,
    malicious: bool,
    override_instruction: bool = False,
    disclosure_request: bool = False,
    secret_exfiltration: bool = False,
    social_engineering: bool = False,
) -> _ClassifierOutput:
    return _ClassifierOutput.model_validate(
        {
            "verdict": verdict,
            "malicious": malicious,
            "confidence": 0.9,
            "reason": "test",
            "signals": {
                "override_instruction": override_instruction,
                "disclosure_request": disclosure_request,
                "secret_exfiltration": secret_exfiltration,
                "social_engineering": social_engineering,
            },
        }
    )


def test_derive_malicious_true_when_verdict_and_high_risk_signal_align() -> None:
    parsed = _output(
        verdict="malicious",
        malicious=True,
        override_instruction=True,
    )

    assert _derive_malicious(parsed) is True


def test_derive_malicious_false_when_verdict_benign_even_if_flag_true() -> None:
    parsed = _output(
        verdict="benign",
        malicious=True,
        override_instruction=True,
    )

    assert _derive_malicious(parsed) is False


def test_derive_malicious_false_when_only_social_engineering_signal_present() -> None:
    parsed = _output(
        verdict="malicious",
        malicious=True,
        social_engineering=True,
    )

    assert _derive_malicious(parsed) is False


def test_urgency_marker_maps_from_social_engineering_signal() -> None:
    parsed = _output(
        verdict="benign",
        malicious=False,
        social_engineering=True,
    )
    assert parsed.signals.social_engineering is True


def test_derive_malicious_false_when_malicious_flag_is_false() -> None:
    parsed = _output(
        verdict="malicious",
        malicious=False,
        disclosure_request=True,
    )

    assert _derive_malicious(parsed) is False


def test_parse_classifier_output_accepts_plain_json() -> None:
    content = (
        '{"verdict":"benign","malicious":false,"confidence":0.92,"reason":"ok",'
        '"signals":{"override_instruction":false,"disclosure_request":false,'
        '"secret_exfiltration":false,"social_engineering":false}}'
    )
    parsed = _parse_classifier_output(content)
    assert parsed.verdict == "benign"
    assert parsed.malicious is False


def test_parse_classifier_output_accepts_fenced_json() -> None:
    content = (
        "```json\n"
        '{"verdict":"malicious","malicious":true,"confidence":0.99,"reason":"inject",'
        '"signals":{"override_instruction":true,"disclosure_request":false,'
        '"secret_exfiltration":false,"social_engineering":false}}\n'
        "```"
    )
    parsed = _parse_classifier_output(content)
    assert parsed.verdict == "malicious"
    assert parsed.signals.override_instruction is True


def test_parse_classifier_output_accepts_wrapped_json() -> None:
    content = (
        "Here is the result:\n"
        '{"verdict":"benign","malicious":false,"confidence":0.88,"reason":"normal",'
        '"signals":{"override_instruction":false,"disclosure_request":false,'
        '"secret_exfiltration":false,"social_engineering":true}}'
        "\nThanks."
    )
    parsed = _parse_classifier_output(content)
    assert parsed.verdict == "benign"
    assert parsed.signals.social_engineering is True


def test_openrouter_envelope_validation_ignores_extra_fields() -> None:
    envelope = _OpenRouterResponse.model_validate(
        {
            "id": "gen-123",
            "object": "chat.completion",
            "created": 1776827338,
            "model": "deepseek/deepseek-v3.2-20251201",
            "provider": "Parasail",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": (
                            '{"verdict":"benign","malicious":false,"confidence":0.95,'
                            '"reason":"simple greeting","signals":{"override_instruction":false,'
                            '"disclosure_request":false,"secret_exfiltration":false,'
                            '"social_engineering":false}}'
                        ),
                        "refusal": None,
                    },
                    "logprobs": None,
                }
            ],
            "usage": {"total_tokens": 10},
        }
    )

    assert len(envelope.choices) == 1
    assert envelope.choices[0].message.content.startswith("{")


def test_parse_classifier_output_accepts_not_malicious_verdict_alias() -> None:
    content = (
        "{"
        '"verdict":"not malicious",'
        '"malicious":false,'
        '"confidence":0.0,'
        '"reason":"No cues of prompt injection intent detected.",'
        '"signals":{'
        '"override_instruction":false,'
        '"disclosure_request":false,'
        '"secret_exfiltration":false,'
        '"social_engineering":false'
        "}"
        "}"
    )

    parsed = _parse_classifier_output(content)
    assert parsed.verdict == "benign"
    assert parsed.malicious is False


def test_parse_classifier_output_accepts_non_malicious_verdict_alias() -> None:
    content = (
        "{"
        '"verdict":"non-malicious",'
        '"malicious":false,'
        '"confidence":0.9,'
        '"reason":"No attack intent.",'
        '"signals":{'
        '"override_instruction":false,'
        '"disclosure_request":false,'
        '"secret_exfiltration":false,'
        '"social_engineering":false'
        "}"
        "}"
    )

    parsed = _parse_classifier_output(content)
    assert parsed.verdict == "benign"
    assert parsed.malicious is False
