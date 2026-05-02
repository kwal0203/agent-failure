import os


def get_runtime_shared_token() -> str:
    return os.getenv("RUNTIME_SHARED_TOKEN", "").strip()
