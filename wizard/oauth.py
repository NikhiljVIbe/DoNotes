"""Google OAuth redirect flow for the setup wizard."""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]

REDIRECT_URI = "http://localhost:8765/api/oauth/callback"


class WizardOAuth:
    """Handles Google OAuth flow with a redirect back to the wizard."""

    def __init__(self, credentials_path: Path, token_path: Path):
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._flow = None

    def get_authorization_url(self) -> str:
        """Generate the Google OAuth consent URL."""
        from google_auth_oauthlib.flow import Flow

        self._flow = Flow.from_client_secrets_file(
            str(self._credentials_path),
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )
        auth_url, _state = self._flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        log.info("Generated OAuth URL: %s", auth_url[:80] + "...")
        return auth_url

    def handle_callback(self, authorization_response_url: str) -> bool:
        """Exchange the auth code for credentials and save the token."""
        if not self._flow:
            raise RuntimeError("OAuth flow was not started — call get_authorization_url first")

        self._flow.fetch_token(authorization_response=authorization_response_url)
        creds = self._flow.credentials

        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        self._token_path.write_text(creds.to_json())
        log.info("Google OAuth token saved to %s", self._token_path)
        return True

    def has_valid_token(self) -> bool:
        """Check if a valid token already exists."""
        if not self._token_path.exists():
            return False

        try:
            from google.oauth2.credentials import Credentials

            creds = Credentials.from_authorized_user_file(
                str(self._token_path), SCOPES
            )
            return creds.valid or (creds.expired and creds.refresh_token is not None)
        except Exception:
            return False
