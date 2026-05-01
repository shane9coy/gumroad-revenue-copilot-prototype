from __future__ import annotations

from dataclasses import dataclass

from gumroad_merchant.settings import Settings


@dataclass(frozen=True)
class VoiceStatus:
    enabled: bool
    configured: bool
    reason: str | None = None


def voice_status(settings: Settings) -> VoiceStatus:
    if not settings.xai_voice_enabled:
        return VoiceStatus(enabled=False, configured=False, reason="XAI_VOICE_ENABLED is false")
    if not settings.xai_api_key_present:
        return VoiceStatus(enabled=True, configured=False, reason="XAI_API_KEY is missing")
    return VoiceStatus(enabled=True, configured=True)


def create_voice_client_secret(settings: Settings) -> dict[str, str | bool | None]:
    status = voice_status(settings)
    if not status.configured:
        return {"enabled": status.enabled, "configured": False, "reason": status.reason, "client_secret": None}
    # Placeholder adapter: keep voice behind a flag until the browser-side realtime flow is implemented.
    return {
        "enabled": True,
        "configured": True,
        "reason": "Voice adapter is scaffolded; client secret exchange is not implemented in this demo slice.",
        "client_secret": None,
    }
