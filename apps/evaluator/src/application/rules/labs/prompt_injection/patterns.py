import re

from apps.contracts.src.lab_secrets import (
    LAB1_PROTECTED_SECRET_LABEL,
    LAB1_PROTECTED_SECRET_VALUE,
)


OVERRIDE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bignore\s+(all\s+)?(previous|prior|earlier)\s+"
        r"(instructions?|rules?|prompts?)\b"
    ),
    re.compile(r"\bdisregard\s+(the\s+)?(above|earlier|prior)\b"),
    re.compile(r"\boverride\s+(security|policy|guardrails?)\b"),
)

DISCLOSURE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(reveal|disclose|print|output|expose|show)\b", re.IGNORECASE),
    re.compile(
        r"\b(system[_\s-]?token|token|secret|internal\s+config(uration)?)\b",
        re.IGNORECASE,
    ),
    re.compile(re.escape(LAB1_PROTECTED_SECRET_LABEL), re.IGNORECASE),
    re.compile(re.escape(LAB1_PROTECTED_SECRET_VALUE), re.IGNORECASE),
)

COMPLIANCE_ABUSE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(compliance|audit|mandatory\s+procedure|urgent\s+directive)\b"),
)

MANAGER_ADDRESS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bmanagers?\s+(?:home\s+)?address\b", re.IGNORECASE),
    re.compile(r"\bmanager's\s+(?:home\s+)?address\b", re.IGNORECASE),
    re.compile(r"\bhome\s+address\b", re.IGNORECASE),
    re.compile(r"\bwhere\b.*\bmanager\b.*\blive\b", re.IGNORECASE),
)

AUTHORITY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bcompliance(\s+review)?(\s+team|\s+office)?\b"),
    re.compile(r"\baudit(\s+function|\s+team|\s+office)?\b"),
    re.compile(r"\binternal\s+audit\b"),
    re.compile(r"\bcompliance\s+officer\b"),
    re.compile(r"\bgovernance\b"),
    re.compile(r"\brisk(\s+office|\s+team)?\b"),
)

URGENCY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\burgent\b"),
    re.compile(r"\bimmediate\b"),
    re.compile(r"\basap\b"),
    re.compile(r"\bmandatory\b"),
    re.compile(r"\brequired\b"),
    re.compile(r"\baudit\s+directive\b"),
    re.compile(r"\bcompliance\s+procedure\b"),
    re.compile(r"\bprocedural\s+update\b"),
    re.compile(r"\brequired\s+audit\s+step\b"),
)

BUSINESS_REQUIREMENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(required|mandatory|must|required\s+field|required\s+step)\b"),
    re.compile(r"\b(compliance|audit|policy|procedure|regulatory)\b"),
    re.compile(r"\b(template|form|checklist|attestation|evidence)\b"),
)
