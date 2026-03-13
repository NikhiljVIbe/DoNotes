#!/usr/bin/env python3
"""One-time Google OAuth setup script.

Run this to authorize DoNotes with your Google account:
    python scripts/setup_google_oauth.py

This will open a browser for you to authorize Gmail and Calendar access.
The token will be saved for future use.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from src.integrations.google_auth import GoogleAuth


def main():
    print("DoNotes Google OAuth Setup")
    print("=" * 40)
    print(f"Credentials file: {settings.abs_google_credentials_path}")
    print(f"Token will be saved to: {settings.abs_google_token_path}")
    print()

    if not settings.abs_google_credentials_path.exists():
        print("ERROR: credentials.json not found!")
        print(f"Please download it from Google Cloud Console and place it at:")
        print(f"  {settings.abs_google_credentials_path}")
        sys.exit(1)

    auth = GoogleAuth(
        settings.abs_google_credentials_path,
        settings.abs_google_token_path,
    )

    print("Opening browser for Google authorization...")
    creds = auth.get_credentials()

    if creds and creds.valid:
        print("\nSuccess! Google OAuth setup complete.")
        print(f"Token saved to: {settings.abs_google_token_path}")
    else:
        print("\nFailed to obtain valid credentials.")
        sys.exit(1)


if __name__ == "__main__":
    main()
