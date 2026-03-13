#!/usr/bin/env python3
"""
List Google calendar events for a given date. Uses absolute token path for OpenClaw exec.

Usage:
  python scripts/check_google_calendar.py           # tomorrow
  python scripts/check_google_calendar.py 2026-03-17  # specific date (YYYY-MM-DD)
"""
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from gerty.openclaw.google_auth import get_creds

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
creds = get_creds(SCOPES)
service = build("calendar", "v3", credentials=creds)

tz = ZoneInfo("Europe/London")
if len(sys.argv) > 1:
    try:
        target = datetime.strptime(sys.argv[1], "%Y-%m-%d").replace(tzinfo=tz)
    except ValueError:
        print(f"Invalid date. Use YYYY-MM-DD (e.g. 2026-03-17)")
        sys.exit(1)
else:
    target = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

time_min = target.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
time_max = target.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()

print(f"=== {target.strftime('%A %d %B %Y')} (primary) ===")
events = service.events().list(
    calendarId="primary",
    timeMin=time_min,
    timeMax=time_max,
    singleEvents=True,
    orderBy="startTime",
).execute()
items = events.get("items", [])
if not items:
    print("No events.")
else:
    for e in items:
        start = e["start"].get("dateTime", e["start"].get("date", "?"))
        print(f"  - {e.get('summary', 'No title')} at {start}")
