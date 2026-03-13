#!/usr/bin/env python3
"""
List recent Google Drive files. Uses absolute token path for OpenClaw exec.
Run: ./.venv/bin/python scripts/check_google_drive.py [max_results]
"""
import sys

from googleapiclient.discovery import build

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from gerty.openclaw.google_auth import get_creds

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
creds = get_creds(SCOPES)
service = build("drive", "v3", credentials=creds)

max_results = int(sys.argv[1]) if len(sys.argv) > 1 else 10
results = (
    service.files()
    .list(
        pageSize=max_results,
        fields="files(id, name, mimeType, modifiedTime)",
        orderBy="modifiedTime desc",
    )
    .execute()
)
files = results.get("files", [])

print(f"=== Recent Drive files (max {max_results}) ===")
for f in files:
    mime = f.get("mimeType", "?")
    modified = f.get("modifiedTime", "?")[:10] if f.get("modifiedTime") else "?"
    print(f"- {f.get('name', '?')} ({mime}) modified {modified}")
