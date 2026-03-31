RULE_ID_PI_SECRET_EXFIL = "pi.secret_exfiltration_success"
RULE_ID_RAG_POISON_DETECTED = "rag.poisoning_signal_detected"
RULE_ID_TM_TOOL_VIOLATION = "tm.protected_tool_access_violation"
RULE_ID_CE_CODE_EXECUTE_VIOLATION = "ce.execution_tool_call_detected"

RULE_IDS_BY_BUNDLE: dict[str, tuple[str, ...]] = {
    "prompt_injection_v1": ("pi.secret_exfiltration_success",),
    "rag_poisoning_v1": ("rag.poisoning_signal_detected",),
    "tool_misuse_v1": ("tm.protected_tool_access_violation",),
    "code_execution_v1": ("ce.execution_tool_call_detected",),
}

REQUIRED_EVIDENCE_KEYS_BY_RULE_ID: dict[str, tuple[str, ...]] = {
    "pi.secret_exfiltration_success": (
        "event_type",
        "event_index",
        "secret_marker",
        "evidence_source",
        "matched_value",
    ),
    "rag.poisoning_signal_detected": (
        "event_type",
        "event_index",
        "marker",
        "evidence_source",
    ),
    "tm.protected_tool_access_violation": (
        "event_type",
        "event_index",
        "tool_name",
        "target_resource",
        "violation_type",
    ),
    "ce.execution_tool_call_detected": (
        "event_type",
        "event_index",
        "tool_name",
    ),
}
