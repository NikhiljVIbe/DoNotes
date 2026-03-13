from __future__ import annotations

import logging
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]


class GoogleAuth:
    def __init__(self, credentials_path: str | Path, token_path: str | Path):
        self._credentials_path = Path(credentials_path)
        self._token_path = Path(token_path)
        self._creds: Credentials | None = None

    def get_credentials(self) -> Credentials:
        """Load existing token, refresh if expired, or run OAuth flow."""
        if self._creds and self._creds.valid:
            return self._creds

        if self._token_path.exists():
            self._creds = Credentials.from_authorized_user_file(
                str(self._token_path), SCOPES
            )

        if self._creds and self._creds.expired and self._creds.refresh_token:
            log.info("Refreshing Google OAuth token...")
            try:
                self._creds.refresh(Request())
                self._save_token()
            except RefreshError:
                log.warning(
                    "Refresh token expired or revoked, re-running OAuth flow..."
                )
                self._creds = None
                self._run_oauth_flow()
        elif not self._creds or not self._creds.valid:
            self._run_oauth_flow()

        return self._creds

    def _run_oauth_flow(self) -> None:
        """Run the interactive OAuth flow to get new credentials."""
        log.info("Running Google OAuth flow...")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self._credentials_path), SCOPES
        )
        self._creds = flow.run_local_server(port=0)
        self._save_token()

    def _save_token(self) -> None:
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        self._token_path.write_text(self._creds.to_json())
        log.info("Google OAuth token saved to %s", self._token_path)
