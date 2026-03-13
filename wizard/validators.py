"""Credential validation for the setup wizard."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    valid: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

async def validate_telegram(bot_token: str, user_id: int) -> ValidationResult:
    """Validate a Telegram bot token via the getMe API."""
    import httpx

    if not bot_token or ":" not in bot_token:
        return ValidationResult(False, "Token format should be like 123456789:ABCdef...")

    if user_id <= 0:
        return ValidationResult(False, "User ID must be a positive integer")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://api.telegram.org/bot{bot_token}/getMe"
            )
            data = resp.json()

            if not data.get("ok"):
                return ValidationResult(
                    False,
                    data.get("description", "Invalid bot token"),
                )

            bot = data["result"]
            return ValidationResult(
                True,
                f"Bot @{bot.get('username', '?')} ({bot.get('first_name', '?')}) is valid!",
                {
                    "bot_name": bot.get("first_name", ""),
                    "bot_username": bot.get("username", ""),
                },
            )
    except httpx.TimeoutException:
        return ValidationResult(False, "Request timed out — check your internet connection")
    except Exception as exc:
        log.exception("Telegram validation error")
        return ValidationResult(False, f"Connection error: {exc}")


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

async def validate_openai(api_key: str) -> ValidationResult:
    """Validate an OpenAI API key by listing models."""
    if not api_key or not api_key.startswith("sk-"):
        return ValidationResult(False, "API key should start with 'sk-'")

    try:
        from openai import AsyncOpenAI, AuthenticationError, APIConnectionError

        client = AsyncOpenAI(api_key=api_key)
        models = await client.models.list()
        model_ids = [m.id for m in models.data[:5]]
        return ValidationResult(
            True,
            "API key is valid!",
            {"models_sample": model_ids},
        )
    except AuthenticationError:
        return ValidationResult(False, "Invalid API key — authentication failed")
    except APIConnectionError:
        return ValidationResult(False, "Cannot reach OpenAI — check your internet connection")
    except ImportError:
        return ValidationResult(False, "OpenAI package not installed")
    except Exception as exc:
        log.exception("OpenAI validation error")
        return ValidationResult(False, f"Error: {exc}")


# ---------------------------------------------------------------------------
# Google credentials.json
# ---------------------------------------------------------------------------

def validate_google_credentials(file_bytes: bytes) -> ValidationResult:
    """Validate a Google OAuth credentials.json file."""
    try:
        data = json.loads(file_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return ValidationResult(False, "File is not valid JSON")

    # Google credentials can be "installed" (desktop) or "web" type
    if "installed" in data:
        client_info = data["installed"]
        client_type = "Desktop app"
    elif "web" in data:
        client_info = data["web"]
        client_type = "Web app"
    else:
        return ValidationResult(
            False,
            "Not a valid OAuth credentials file. "
            "Expected a file with 'installed' or 'web' key. "
            "Make sure you downloaded the OAuth 2.0 Client ID JSON.",
        )

    required = ["client_id", "client_secret", "auth_uri", "token_uri"]
    missing = [k for k in required if k not in client_info]
    if missing:
        return ValidationResult(False, f"Credentials file missing keys: {', '.join(missing)}")

    return ValidationResult(
        True,
        f"Valid {client_type} OAuth credentials!",
        {"client_type": client_type, "client_id": client_info["client_id"][:30] + "..."},
    )
