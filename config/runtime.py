import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


def persistence_mode(environment: str | None = None) -> str:
    """Memory is only available in explicitly selected development/test environments."""
    environment = (environment or os.getenv("APP_ENV", "production")).strip().lower()
    local = environment in {"development", "test"}
    mode = os.getenv("ROOMFLOW_PERSISTENCE", "postgres").strip().lower()
    if mode not in {"memory", "postgres"}:
        raise ValueError("ROOMFLOW_PERSISTENCE deve ser postgres ou memory.")
    if mode == "memory" and not local:
        raise ValueError("Persistência em memória não é permitida em produção.")
    return mode
