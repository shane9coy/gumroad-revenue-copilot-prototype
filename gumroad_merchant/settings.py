from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_SECRET_KEYS = {"OPENAI_API_KEY", "XAI_API_KEY"}
DEFAULT_OPENAI_AGENT_MODEL = "gpt-5.4-nano"
DEFAULT_OPENAI_AGENT_MAX_TURNS = 5


def load_local_env() -> None:
    """Load local env files without printing secrets."""
    for name in (".env", ".env.local"):
        path = PROJECT_ROOT / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if not key:
                continue
            if key not in os.environ or (name == ".env.local" and key in LOCAL_SECRET_KEYS):
                os.environ[key] = value


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        parsed = int(value.strip())
    except ValueError:
        return default
    return max(minimum, min(maximum, parsed))


def env_path(name: str, default: str) -> Path:
    value = os.environ.get(name, default)
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    profile: str
    db_path: Path
    chat_db_path: Path
    redis_url: str
    openai_agent_model: str
    openai_agent_verbosity: str
    openai_agent_max_turns: int
    openai_agent_tracing: bool
    openai_image_model: str
    openai_image_size: str
    openai_image_quality: str
    openai_image_output_max_px: int
    xai_voice_enabled: bool
    xai_api_key_present: bool


def get_settings() -> Settings:
    load_local_env()
    profile = os.environ.get("GUMROAD_MERCHANT_PROFILE", "active").strip().lower() or "active"
    if profile == "test":
        db_default = "data/gumroad_merchant_test.sqlite"
        chat_db_default = "data/gumroad_merchant_test_chat.sqlite"
    elif profile == "demo":
        db_default = "data/gumroad_merchant_demo.sqlite"
        chat_db_default = "data/gumroad_merchant_demo_chat.sqlite"
    else:
        db_default = "data/gumroad_merchant.sqlite"
        chat_db_default = "data/gumroad_merchant_chat.sqlite"
    agent_verbosity = os.environ.get("OPENAI_AGENT_VERBOSITY", "low").strip().lower() or "low"
    if agent_verbosity not in {"low", "medium", "high"}:
        agent_verbosity = "low"
    agent_model = os.environ.get("OPENAI_AGENT_MODEL", DEFAULT_OPENAI_AGENT_MODEL).strip() or DEFAULT_OPENAI_AGENT_MODEL
    return Settings(
        profile=profile,
        db_path=env_path("GUMROAD_MERCHANT_DB", db_default),
        chat_db_path=env_path("GUMROAD_MERCHANT_CHAT_DB", chat_db_default),
        redis_url=os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"),
        openai_agent_model=agent_model,
        openai_agent_verbosity=agent_verbosity,
        openai_agent_max_turns=env_int("OPENAI_AGENT_MAX_TURNS", DEFAULT_OPENAI_AGENT_MAX_TURNS, 3, 12),
        openai_agent_tracing=env_bool("OPENAI_AGENT_TRACING", False),
        openai_image_model=os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1-mini").strip() or "gpt-image-1-mini",
        openai_image_size=os.environ.get("OPENAI_IMAGE_SIZE", "1024x1024").strip() or "1024x1024",
        openai_image_quality=os.environ.get("OPENAI_IMAGE_QUALITY", "low").strip() or "low",
        openai_image_output_max_px=int(os.environ.get("OPENAI_IMAGE_OUTPUT_MAX_PX", "480").strip() or "480"),
        xai_voice_enabled=env_bool("XAI_VOICE_ENABLED", False),
        xai_api_key_present=bool(os.environ.get("XAI_API_KEY", "").strip()),
    )


def openai_key_present() -> bool:
    load_local_env()
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())
