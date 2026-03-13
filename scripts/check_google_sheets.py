#!/usr/bin/env python3
"""
List Google Sheets or read a sheet. Uses absolute token path for OpenClaw exec.
Run:
  ./.venv/bin/python scripts/check_google_sheets.py              # list recent sheets
  ./.venv/bin/python scripts/check_google_sheets.py <sheet_id>   # read first sheet
"""
import sys

from googleapiclient.discovery import build

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from gerty.openclaw.google_auth import get_creds

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]
creds = get_creds(SCOPES)
sheets = build("sheets", "v4", credentials=creds)
drive = build("drive", "v3", credentials=creds)

if len(sys.argv) > 1:
    sheet_id = sys.argv[1]
    result = sheets.spreadsheets().get(spreadsheetId=sheet_id).execute()
    title = result.get("properties", {}).get("title", "?")
    sheets_list = result.get("sheets", [])
    if sheets_list:
        first = sheets_list[0]
        name = first.get("properties", {}).get("title", "Sheet1")
        data = (
            sheets.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range=f"'{name}'!A1:Z100")
            .execute()
        )
        rows = data.get("values", [])
        print(f"=== {title} / {name} ===")
        for row in rows[:20]:
            print(" | ".join(str(c) for c in row))
    else:
        print("No sheets found.")
else:
    results = (
        drive.files()
        .list(
            q="mimeType='application/vnd.google-apps.spreadsheet'",
            pageSize=10,
            fields="files(id, name, modifiedTime)",
            orderBy="modifiedTime desc",
        )
        .execute()
    )
    files = results.get("files", [])
    print("=== Recent Google Sheets ===")
    for f in files:
        modified = f.get("modifiedTime", "?")[:10] if f.get("modifiedTime") else "?"
        print(f"- {f.get('name', '?')} (id={f.get('id', '?')}) modified {modified}")
