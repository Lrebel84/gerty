"""
Shared Google OAuth for OpenClaw scripts.
Token path: GOOGLE_TOKEN_PATH env var, or ~/.openclaw/credentials/google-token.json.
"""
import os
from pathlib import Path

from google.oauth2.credentials import Credentials

_DEFAULT_TOKEN_PATH = Path.home() / ".openclaw" / "credentials" / "google-token.json"
_raw = os.environ.get("GOOGLE_TOKEN_PATH")
TOKEN_PATH = Path(os.path.expanduser(_raw)) if _raw else _DEFAULT_TOKEN_PATH


def get_creds(scopes: list[str]) -> Credentials:
    """Load OAuth credentials from the token file."""
    return Credentials.from_authorized_user_file(str(TOKEN_PATH), scopes)
