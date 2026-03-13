#!/usr/bin/env python3
"""
List Google Docs or read a doc. Uses absolute token path for OpenClaw exec.
Run:
  ./.venv/bin/python scripts/check_google_docs.py              # list recent docs
  ./.venv/bin/python scripts/check_google_docs.py <doc_id>     # read doc content
"""
import sys

from googleapiclient.discovery import build

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from gerty.openclaw.google_auth import get_creds

SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]
creds = get_creds(SCOPES)
docs = build("docs", "v1", credentials=creds)
drive = build("drive", "v3", credentials=creds)


def _extract_text(content: list) -> str:
    """Extract plain text from Docs API content."""
    parts = []
    for elem in content:
        if "paragraph" in elem:
            for e in elem["paragraph"].get("elements", []):
                if "textRun" in e:
                    parts.append(e["textRun"].get("content", ""))
        else:
            parts.append(str(elem))
    return "".join(parts).strip()


if len(sys.argv) > 1:
    doc_id = sys.argv[1]
    doc = docs.documents().get(documentId=doc_id).execute()
    title = doc.get("title", "?")
    content = doc.get("body", {}).get("content", [])
    text = _extract_text(content)
    print(f"=== {title} ===")
    print(text[:2000] + ("..." if len(text) > 2000 else ""))
else:
    results = (
        drive.files()
        .list(
            q="mimeType='application/vnd.google-apps.document'",
            pageSize=10,
            fields="files(id, name, modifiedTime)",
            orderBy="modifiedTime desc",
        )
        .execute()
    )
    files = results.get("files", [])
    print("=== Recent Google Docs ===")
    for f in files:
        modified = f.get("modifiedTime", "?")[:10] if f.get("modifiedTime") else "?"
        print(f"- {f.get('name', '?')} (id={f.get('id', '?')}) modified {modified}")
