"""DoNotes Setup Wizard — FastAPI application."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from wizard.validators import validate_telegram, validate_openai, validate_google_credentials
from wizard.oauth import WizardOAuth
from wizard.file_writer import write_env_file, write_user_profile
from wizard.bot_launcher import launch_bot, is_bot_running

log = logging.getLogger(__name__)

WIZARD_DIR = Path(__file__).parent
PROJECT_ROOT = WIZARD_DIR.parent
GOOGLE_TOKENS_DIR = PROJECT_ROOT / "data" / "google_tokens"
CREDENTIALS_PATH = GOOGLE_TOKENS_DIR / "credentials.json"
TOKEN_PATH = GOOGLE_TOKENS_DIR / "token.json"

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="DoNotes Setup Wizard", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=WIZARD_DIR / "static"), name="static")
templates = Jinja2Templates(directory=WIZARD_DIR / "templates")

# Module-level OAuth state (single-user localhost server, this is fine)
_oauth: WizardOAuth | None = None


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def wizard_page(request: Request):
    """Serve the main wizard page."""
    return templates.TemplateResponse("wizard.html", {"request": request})


# ---------------------------------------------------------------------------
# Validation endpoints
# ---------------------------------------------------------------------------

class TelegramInput(BaseModel):
    bot_token: str
    user_id: int

class OpenAIInput(BaseModel):
    api_key: str


@app.post("/api/validate/telegram")
async def api_validate_telegram(data: TelegramInput):
    result = await validate_telegram(data.bot_token, data.user_id)
    return {"valid": result.valid, "message": result.message, "details": result.details}


@app.post("/api/validate/openai")
async def api_validate_openai(data: OpenAIInput):
    result = await validate_openai(data.api_key)
    return {"valid": result.valid, "message": result.message, "details": result.details}


@app.post("/api/upload/google-credentials")
async def api_upload_credentials(file: UploadFile):
    """Upload and validate a Google OAuth credentials.json file."""
    contents = await file.read()
    result = validate_google_credentials(contents)

    if not result.valid:
        return JSONResponse(
            {"valid": False, "message": result.message},
            status_code=400,
        )

    # Save the file
    GOOGLE_TOKENS_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_PATH.write_bytes(contents)

    return {"valid": True, "message": result.message, "details": result.details}


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------

@app.get("/api/oauth/start")
async def api_oauth_start():
    """Redirect the user to Google's consent screen."""
    global _oauth

    if not CREDENTIALS_PATH.exists():
        return JSONResponse(
            {"error": "Upload credentials.json first (Step 5)"},
            status_code=400,
        )

    _oauth = WizardOAuth(CREDENTIALS_PATH, TOKEN_PATH)
    auth_url = _oauth.get_authorization_url()
    return RedirectResponse(auth_url)


@app.get("/api/oauth/callback")
async def api_oauth_callback(request: Request):
    """Handle the redirect back from Google after authorization."""
    global _oauth

    if not _oauth:
        return RedirectResponse("/?step=6&oauth=error&message=OAuth+flow+not+started")

    try:
        full_url = str(request.url)
        _oauth.handle_callback(full_url)
        return RedirectResponse("/?step=6&oauth=success")
    except Exception as exc:
        log.exception("OAuth callback error")
        msg = str(exc).replace(" ", "+")[:200]
        return RedirectResponse(f"/?step=6&oauth=error&message={msg}")


@app.get("/api/oauth/status")
async def api_oauth_status():
    """Check if Google OAuth token exists and is valid."""
    if _oauth and _oauth.has_valid_token():
        return {"authorized": True}

    # Fallback: check file directly
    if TOKEN_PATH.exists():
        try:
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH))
            if creds.valid or (creds.expired and creds.refresh_token):
                return {"authorized": True}
        except Exception:
            pass

    return {"authorized": False}


# ---------------------------------------------------------------------------
# Timezones
# ---------------------------------------------------------------------------

@app.get("/api/timezones")
async def api_timezones():
    """Return list of IANA timezone names."""
    common = [
        "America/New_York", "America/Chicago", "America/Denver",
        "America/Los_Angeles", "America/Toronto", "America/Sao_Paulo",
        "Europe/London", "Europe/Paris", "Europe/Berlin",
        "Asia/Kolkata", "Asia/Tokyo", "Asia/Shanghai", "Asia/Dubai",
        "Australia/Sydney", "Pacific/Auckland", "UTC",
    ]

    try:
        from zoneinfo import available_timezones
        all_zones = sorted(available_timezones())
    except ImportError:
        all_zones = common  # Fallback

    return {"common": common, "all": all_zones}


# ---------------------------------------------------------------------------
# Setup status
# ---------------------------------------------------------------------------

@app.get("/api/status")
async def api_status():
    """Check which setup steps are already complete."""
    env_path = PROJECT_ROOT / ".env"
    profile_path = PROJECT_ROOT / "config" / "user_profile.py"
    bot_status = is_bot_running()

    return {
        "env_exists": env_path.exists(),
        "credentials_uploaded": CREDENTIALS_PATH.exists(),
        "google_authorized": TOKEN_PATH.exists(),
        "profile_exists": profile_path.exists(),
        "bot_running": bot_status.get("running", False),
        "bot_pid": bot_status.get("pid"),
    }


# ---------------------------------------------------------------------------
# Save configuration
# ---------------------------------------------------------------------------

class SaveConfig(BaseModel):
    # Telegram
    telegram_bot_token: str
    telegram_user_id: int
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o"
    # Google
    gmail_sender_email: str
    gmail_recipient_email: str = ""
    work_calendar_id: str = ""
    personal_calendar_id: str = ""
    # User
    timezone: str = "UTC"
    user_name: str = ""
    # Personalization (optional)
    user_profile_context: str = ""
    self_names: list[str] = []
    known_people: list[str] = []
    whisper_places: list[str] = []
    whisper_companies: list[str] = []


@app.post("/api/save")
async def api_save(config: SaveConfig):
    """Save all configuration to .env and optionally user_profile.py."""
    try:
        data = config.model_dump()

        # Write .env
        env_path = write_env_file(PROJECT_ROOT, data)

        # Write user_profile.py if any personalization data provided
        profile_path = None
        has_personalization = any([
            data.get("user_profile_context"),
            data.get("known_people"),
            data.get("whisper_places"),
            data.get("whisper_companies"),
        ])
        if has_personalization or data.get("user_name"):
            profile_path = write_user_profile(PROJECT_ROOT, data)

        return {
            "success": True,
            "env_path": str(env_path),
            "profile_path": str(profile_path) if profile_path else None,
        }
    except Exception as exc:
        log.exception("Error saving configuration")
        return JSONResponse(
            {"success": False, "error": str(exc)},
            status_code=500,
        )


# ---------------------------------------------------------------------------
# Launch bot
# ---------------------------------------------------------------------------

@app.post("/api/launch")
async def api_launch():
    """Start the DoNotes bot as a background process."""
    result = launch_bot()
    if result["success"]:
        return result
    return JSONResponse(result, status_code=500)
