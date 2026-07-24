"""Compatibility import for the Prompt Injection v1 rule bundle."""

from .prompt_injection import PROMPT_INJECTION_V1_BUNDLE
from .prompt_injection.evidence import matches_manager_disclosure_regex

__all__ = [
    "PROMPT_INJECTION_V1_BUNDLE",
    "matches_manager_disclosure_regex",
]
