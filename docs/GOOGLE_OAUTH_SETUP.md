# Google OAuth Setup for OpenClaw (Calendar, Gmail, Drive, Sheets, Docs)

OpenClaw can access your Google Calendar, Gmail, Drive, Sheets, and Docs when you complete the OAuth flow. Your `google_client.json` has the **client credentials** (client_id, client_secret)—you also need a **refresh token** from a one-time consent flow.

## The Problem

- **Client credentials** (what you have): Identify your app to Google. Not enough to read your data.
- **Refresh token** (what you need): Proves you granted access. Obtained by signing in once in a browser.

Without the refresh token, OpenClaw either fails or sees empty data (e.g. a service account’s own empty calendar).

**Exec host:** OpenClaw exec defaults to sandbox (Docker), which cannot read `~/.openclaw/credentials/`. Set `tools.exec.host` to `"gateway"` in `~/.openclaw/openclaw.json`. Run `./scripts/check_openclaw.sh` to verify.

## Step 1: Run the OAuth Flow

From the project root:

```bash
cd ~/gerty
./.venv/bin/pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
./.venv/bin/python scripts/google_oauth_flow.py
```

A browser will open. Sign in with your Google account and grant access. The script saves the token to `~/.openclaw/credentials/google-token.json`. If you already have a token and only need Sheets/Docs, re-run the flow to add those scopes.

## Step 2: Credential Layout

Use this layout so OpenClaw can find everything:

```
~/.openclaw/credentials/
├── google-credentials.json   # Copy of your client secrets (from gerty/openclaw/)
└── google-token.json         # Created by the OAuth script (refresh token)
```

Copy your client secrets (from project root; download from Google Cloud Console or copy from `gerty/openclaw/google_client.json.example` and fill in):

```bash
mkdir -p ~/.openclaw/credentials
cp gerty/openclaw/google_client.json ~/.openclaw/credentials/google-credentials.json
```

## Step 3: OpenClaw Calendar Skill

The **gerty-calendar** skill in `skills/calendar/SKILL.md` teaches OpenClaw to run the calendar script via exec. No custom prompt needed for calendar—the skill provides the instructions. For Gmail/Drive/Sheets/Docs, add to your Gerty custom prompt (Settings):

> When using Gmail, Drive, Sheets, or Docs: ALWAYS run the Gerty scripts. NEVER invent or guess data. Use: `cd /path/to/gerty && .venv/bin/python scripts/check_google_gmail.py [N]` (or drive, sheets, docs).

## Step 4: Gerty Scripts (Recommended)

Use these scripts for Google data—they use the correct absolute token path:

| Service | Script | Usage |
|---------|--------|-------|
| Calendar | `scripts/check_google_calendar.py` | Lists calendars and tomorrow's events |
| Gmail | `scripts/check_google_gmail.py` | `check_google_gmail.py [N]` — N recent emails |
| Drive | `scripts/check_google_drive.py` | `check_google_drive.py [N]` — N recent files |
| Sheets | `scripts/check_google_sheets.py` | List sheets, or `check_google_sheets.py <id>` to read |
| Docs | `scripts/check_google_docs.py` | List docs, or `check_google_docs.py <id>` to read |

Run from project root: `./.venv/bin/python scripts/check_google_calendar.py`

## Step 5: gog (Google Workspace CLI)

The **gog** skill provides a unified CLI for Gmail, Calendar, Drive, Contacts, Sheets, Docs. On Linux, install first:

```bash
./scripts/install_gog.sh
```

Then OAuth setup (one-time):

```bash
gog auth credentials gerty/openclaw/google_client.json   # or ~/.openclaw/credentials/google-credentials.json
gog auth add you@gmail.com --services gmail,calendar,drive,contacts,sheets,docs
```

The `gog auth add` step opens a browser for consent. Ensure `gog` is in `~/.openclaw/exec-approvals.json` allowlist.

## Step 6: Install a Google Skill (Optional)

For a dedicated skill instead of ad-hoc scripts:

```bash
clawhub search "google calendar"
clawhub install google-calendar   # or the skill name you find
```

Configure the skill with `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REFRESH_TOKEN` (from the token file) via `openclaw secret set` or the skill’s config.

## Troubleshooting

**"No token yet" when OpenClaw runs**  
OpenClaw's exec may use a different `$HOME`. Set `GOOGLE_TOKEN_PATH` in `.env` to an absolute path (e.g. `$HOME/.openclaw/credentials/google-token.json`, expanded at runtime).

**Token must be JSON, not pickle**  
Our OAuth script saves JSON. If another script uses `pickle.dump()`, it will overwrite the token and break loading. Always use `Credentials.from_authorized_user_file()` with the JSON token—never pickle.

**"Access blocked" or "App not verified"**  
Your app is in Testing mode. Add your Gmail as a test user in [Google Cloud Console → OAuth consent screen → Test users](https://console.cloud.google.com/apis/credentials/consent).

**Redirect URI mismatch**  
The OAuth script uses `http://localhost` and a random port. If your client has different `redirect_uris`, use a Desktop app client with `http://localhost` in the redirect URIs.

**Token expired**  
Refresh tokens from the OAuth flow normally don’t expire. If you see expiry errors, run the OAuth script again to get a new token.
