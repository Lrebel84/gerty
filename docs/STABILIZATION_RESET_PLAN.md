# Stabilization Reset Plan

**Goal:** Product simplicity, trust, and natural use. Desktop app as primary runtime. No mixed backends. No phrase dependence.

---

## 1. Desktop App / Runtime Parity

**Rule:** The desktop app is the primary and only supported runtime. Terminal validation is secondary.

### 1.1 Verify app launch

- [x] **Env:** Python `load_dotenv` runs in config.py; `.env` loaded from project root.
- [x] **Code:** `exec python -B -m gerty` runs from project root; `-B` avoids stale `.pyc`. Startup log added with project_root, openclaw, google_native.
- [x] **OpenClaw daemon:** Launch script starts daemon when `GERTY_OPENCLAW_ENABLED=1`; port 18789. `launch_gerty.sh` documents env/restart.

### 1.2 Verify restart and new chat

- [x] **Restart:** Documented in launch script: "Restart Gerty app after code changes."
- [ ] **New chat (+):** Same Router/executor instance. (New chat clears history in UI; backend unchanged.)
- [x] **Parity test:** `/api/runtime-check` returns project_root, openclaw_enabled, google_native_enabled, config_hash.

### 1.3 Stop terminal-only validation

- [ ] Update `--validate` and docs: "Primary validation is via the desktop app. Run a calendar read, a calendar create, and an email send from the app. Terminal checks are supplementary."

---

## 2. Simple Intent-First Routing

**Rule:** Replace keyword-first routing with a lightweight intent pass. Every message gets: what the user wants, domain, backend, confirmation required?, success verification.

### 2.1 Intent router contract

For each user message, the router must output:

| Field | Purpose |
|-------|---------|
| `intent` | What the user wants (e.g. calendar_read, calendar_create, email_send) |
| `domain` | Domain (calendar, email, drive) |
| `backend` | Which backend handles it (openclaw, native, etc.) |
| `requires_confirmation` | True for writes |
| `success_verification` | How to verify (e.g. "gog returns event id") |

### 2.2 Implementation approach

- [ ] **Phase 1:** Add a thin `intent_router` that runs first. Input: message. Output: structured intent (domain, action, backend). Keep existing keyword logic as fallback but deprecate.
- [ ] **Phase 2:** Use a small local model or rule-based pass to map natural language → intent. Prefer: "what have I got on", "what's on", "what am I doing", "check my calendar" → same intent. No phrase whitelist; use semantic equivalence or a small set of patterns.
- [ ] **Phase 3:** Remove keyword-order sensitivity. All calendar-read phrasings must resolve to the same intent.

### 2.3 Exact phrase dependence is a bug

These must all resolve to calendar read:

- what have I got on next week
- what's on next week
- what am I doing next week
- check my calendar for next week
- can you check what ive got on next week
- my schedule next week

Add regression tests for each. Fix any that fail.

---

## 3. Single-Backend Domain Ownership (Stabilization)

**Rule:** During stabilization, no mixed backends for the same domain. All Google Workspace goes through gog/OpenClaw.

### 3.1 Remove native read path for Google Workspace

- [x] **Calendar:** Route all calendar (read + write) to OpenClaw/gog when `GERTY_GOOGLE_NATIVE_ENABLED=0`.
- [x] **Gmail:** Same. All email actions → OpenClaw/gog.
- [x] **Drive:** Same. All drive actions → OpenClaw/gog.
- [x] **Config:** Default `GERTY_GOOGLE_NATIVE_ENABLED=0` for stabilization. Set `GERTY_GOOGLE_NATIVE_ENABLED=1` to restore native read.
- [x] **GoogleWorkspaceTool:** Still registered; router never routes calendar/email/drive to it when single-backend (native disabled).

### 3.2 Restore native read later

- [ ] Only after trust is restored: consider re-adding native read path for speed. Document as explicit phase, not default.

---

## 4. Verification Before Success Messaging

**Rule:** No write action may be reported as successful without verification from the same backend.

### 4.1 Write verification contract

For calendar create, email send, email reply:

- [x] **Calendar create:** gog returns event id or link. `verify_write_response` rejects response without confirmation.
- [x] **Email send:** gog returns message_id. Same verification.
- [x] **Email reply:** Same. Require backend confirmation.

### 4.2 Implementation

- [x] **OpenClaw response handling:** `verify_write_response()` in openclaw/validation.py parses for event id, message_id. If missing, returns WRITE_VERIFICATION_FAILED_MSG.
- [x] **Sync and stream:** Both router paths call verify_write_response before returning/yielding.

---

## 5. Execution Order

```
1. Desktop app parity (1.1–1.3)     ← Verify first
2. Single-backend (3.1)             ← Simplifies routing
3. Intent-first routing (2.1–2.3)  ← Replace keywords
4. Verification (4.1–4.2)          ← Trust
```

---

## 6. Out of Scope (For Now)

- More architecture complexity
- New subsystems
- Terminal as primary validation surface
- Native read path for Google Workspace
- Keyword-order-dependent routing

---

## 7. Success Criteria

- [x] Desktop app launch uses correct env and code; restart loads changes.
- [ ] New chat uses same runtime. (Same backend; UI clears history.)
- [x] All calendar/email/drive go through gog/OpenClaw (when GERTY_GOOGLE_NATIVE_ENABLED=0).
- [x] All six calendar-read phrasings resolve correctly.
- [x] No write success message without backend verification.
- [ ] Validation is app-first, terminal supplementary. (Docs update pending.)
