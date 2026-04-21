BLOCK_REASON_CODES = {"POLICY_DENIED", "SAFETY_BLOCKED", "PROMPT_INJECTION_BLOCKED"}
PROTECTED_RESOURCE_MARKERS = ("/protected", "/secrets", "/var/secure", "flag")
SECRET_MARKERS = ("FLAG{",)
TEXT_PAYLOAD_FIELDS = ("content", "output", "result", "message", "text")
