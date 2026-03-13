#!/usr/bin/env python3
"""
Run Google OAuth flow to obtain a refresh token for Calendar, Gmail, Drive.
Saves token to ~/.openclaw/credentials/google-token.json.

Usage:
  python scripts/google_oauth_flow.py [path/to/credentials.json]

Defaults to gerty/openclaw/google_client.json or ~/.openclaw/credentials/google-credentials.json
"""

import json
import os
import sys
from pathlib import Path

# Resolve credentials path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_PATHS = [
    PROJECT_ROOT / "gerty" / "openclaw" / "google_client.json",
    Path.home() / ".openclaw" / "credentials" / "google-credentials.json",
]
TOKEN_PATH = Path.home() / ".openclaw" / "credentials" / "google-token.json"

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]


def main():
    creds_path = sys.argv[1] if len(sys.argv) > 1 else None
    if creds_path:
        creds_path = Path(creds_path)
    else:
        for p in DEFAULT_PATHS:
            if p.exists():
                creds_path = p
                break
        else:
            print("No credentials file found. Tried:")
            for p in DEFAULT_PATHS:
                print(f"  - {p}")
            print("\nUsage: python scripts/google_oauth_flow.py /path/to/google_client.json")
            sys.exit(1)

    if not creds_path.exists():
        print(f"Credentials file not found: {creds_path}")
        sys.exit(1)

    # Check format - must be OAuth "installed" type, not service account
    with open(creds_path) as f:
        data = json.load(f)
    if "installed" in data:
        client_config = data["installed"]
    elif "web" in data:
        client_config = data["web"]
        # Desktop flow needs redirect_uris with localhost
        if "redirect_uris" not in client_config or not any("localhost" in u for u in client_config.get("redirect_uris", [])):
            print("Warning: Web client may need 'http://localhost' in redirect_uris for run_local_server.")
    elif "client_email" in data or "type" in data and data.get("type") == "service_account":
        print(
            "This file is a SERVICE ACCOUNT key, not OAuth credentials.\n"
            "For personal Gmail/Calendar, use OAuth:\n"
            "  1. Google Cloud Console → Credentials → Create → OAuth client ID\n"
            "  2. Application type: Desktop app\n"
            "  3. Download the JSON (has 'installed' with client_id, client_secret)\n"
            "  4. Run this script again with that file"
        )
        sys.exit(1)
    else:
        print("Unknown credentials format. Expected 'installed' or 'web' with client_id, client_secret.")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Install required packages:")
        print("  pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        sys.exit(1)

    print(f"Using credentials from: {creds_path}")
    print("Opening browser for Google sign-in...")
    print("Scopes: calendar, gmail, drive, sheets, docs")

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Save as JSON (google-auth can load this)
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }
    with open(TOKEN_PATH, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"\nToken saved to: {TOKEN_PATH}")
    print("You can now ask Gerty about your calendar, emails, or Drive.")
    print("\nCopy credentials to OpenClaw if needed:")
    print(f"  cp {creds_path} ~/.openclaw/credentials/google-credentials.json")


if __name__ == "__main__":
    main()
