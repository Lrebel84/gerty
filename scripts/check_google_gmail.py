#!/usr/bin/env python3
"""
List recent Gmail messages. Uses absolute token path for OpenClaw exec.
Run: ./.venv/bin/python scripts/check_google_gmail.py [max_results]
"""
import sys

from googleapiclient.discovery import build

# Add project root for import
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from gerty.openclaw.google_auth import get_creds

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
creds = get_creds(SCOPES)
service = build("gmail", "v1", credentials=creds)

max_results = int(sys.argv[1]) if len(sys.argv) > 1 else 10
results = (
    service.users()
    .messages()
    .list(userId="me", maxResults=max_results)
    .execute()
)
messages = results.get("messages", [])

print(f"=== Recent emails (max {max_results}) ===")
for msg_ref in messages:
    msg = service.users().messages().get(userId="me", id=msg_ref["id"]).execute()
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    subject = headers.get("Subject", "(no subject)")
    from_addr = headers.get("From", "?")
    date = headers.get("Date", "?")
    snippet = (msg.get("snippet", "") or "")[:80]
    print(f"- {subject}")
    print(f"  From: {from_addr} | {date}")
    print(f"  {snippet}...")
    print()
