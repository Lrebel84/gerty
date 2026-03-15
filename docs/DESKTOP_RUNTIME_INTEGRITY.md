# Desktop Runtime Integrity

**Purpose:** Verify the desktop app uses the same working path as the verified terminal backend. Root cause analysis and fix for "check my calendar" returning stale native-tool remediation hints instead of OpenClaw/gog data.

---

## 1. Root Cause

**Symptom:** User asked "check my calendar for next week" in the desktop app and received:

> "I tried to fetch your Google data but got no output. If token missing: run ./.venv/bin/python scripts/google_oauth_flow.py ..."

**Source:** `gerty/openclaw/validation.py` → `_empty_output_message()` when OpenClaw returns empty content. The message referenced **native** Google scripts (`google_oauth_flow.py`, `check_google_workspace.sh`), which are **not used** when the path is OpenClaw/gog.

**Flow:**
1. Router routes calendar to OpenClaw (single-backend mode: `GERTY_GOOGLE_NATIVE_ENABLED=0`)
2. OpenClaw executes; returns **empty** content
3. `validate_openclaw_response()` replaces empty with `_empty_output_message()`
4. Old message gave native OAuth hints — wrong for OpenClaw path

**Why empty?** OpenClaw daemon may be unreachable, gog skill missing, exec not approved, or model skipped tool use. The hint must point to the correct remediation (gog, exec-approvals, daemon).

---

## 2. Fix

### 2.1 OpenClaw-specific empty message

When OpenClaw returns empty for a Google Workspace request, use **OpenClaw/gog** hints instead of native OAuth:

- `openclaw daemon start`
- `clawhub install gog`
- `~/.openclaw/exec-approvals.json` (Python path, ask=off)
- `tools.exec.host` = `gateway` in openclaw.json
- `./scripts/verify_gog_setup.sh`

**File:** `gerty/openclaw/validation.py` — `_empty_output_message(..., from_openclaw=True)` for OpenClaw path.

### 2.2 Runtime integrity report

**Endpoint:** `GET /api/runtime-integrity` (and `/api/runtime-check`)

Returns:
- `project_root`, `config_hash`
- `openclaw_enabled`, `google_native_enabled`
- `daemon_reachable`, `gog_available`, `openclaw_env_exists`
- `google_routing`: `openclaw:gog` | `native` | `app_unavailable`

**File:** `gerty/runtime_integrity.py`, `gerty/ui/server.py`

### 2.3 Trace endpoint

**Endpoint:** `POST /api/trace-route` with `{"message": "check my calendar for next week"}`

Returns:
- `classified_intent`, `primary_intent`
- `provider`, `tool_intent`, `execution_path`, `execution_path_reason`
- `tool_executor_present`, `google_native_enabled`, `openclaw_enabled`

**File:** `gerty/ui/server.py`

### 2.4 Visible runtime check in Settings

Settings → Runtime section shows:
- Config hash
- Google routing (openclaw:gog / native / app_unavailable)
- OpenClaw on/off
- Daemon reachable / unreachable
- gog available / not found
- ~/.openclaw/.env exists / missing

**File:** `frontend/src/components/Settings.tsx`

---

## 3. Verification

### 3.1 Confirm routing

```bash
curl -X POST http://localhost:8765/api/trace-route \
  -H "Content-Type: application/json" \
  -d '{"message": "check my calendar for next week"}'
```

Expected (stabilization mode):
- `classified_intent`: `calendar`
- `provider`: `openclaw`
- `execution_path`: `openclaw:gog`
- `google_native_enabled`: `false`

### 3.2 Confirm runtime integrity

```bash
curl http://localhost:8765/api/runtime-integrity
```

Expected:
- `google_routing`: `openclaw:gog`
- `daemon_reachable`: `true` (when OpenClaw running)
- `gog_available`: `true` (when gog skill installed)

### 3.3 Desktop app E2E

1. **Launch:** Use `gerty.desktop` or `./scripts/launch_gerty.sh` (starts daemon when `GERTY_OPENCLAW_ENABLED=1`)
2. **Settings → Runtime:** Check config hash, Google routing, daemon, gog
3. **Read calendar:** "check my calendar for next week" → should return events via OpenClaw/gog
4. **Create event:** "add meeting tomorrow 3pm" → should create via gog
5. **Read again:** Confirm new event appears

**Evidence:** Screenshot of Settings Runtime section; chat showing calendar read/create/read.

---

## 4. Stale Paths Removed

- **Empty message:** No longer suggests native `google_oauth_flow.py` when path was OpenClaw
- **Router:** Single-backend default (`GERTY_GOOGLE_NATIVE_ENABLED=0`) — calendar/email/drive → OpenClaw only
- **GoogleWorkspaceTool:** Still registered but not routed to when stabilization mode

---

## 5. Launch Requirements

The desktop app **must** be launched via `scripts/launch_gerty.sh` (or `gerty.desktop` which invokes it):

- Ensures OpenClaw daemon is started when `GERTY_OPENCLAW_ENABLED=1`
- Sets `Path=/home/liam/gerty` so cwd is project root
- Python loads `.env` from project root via `load_dotenv` in config.py

**Do not** run `python -m gerty` directly from a different cwd without ensuring the daemon is running.
