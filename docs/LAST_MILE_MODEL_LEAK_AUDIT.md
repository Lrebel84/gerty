# Last-Mile Model Leak Audit — Report

**Date:** 2026-03-15  
**Context:** OpenRouter logs still showed Grok despite Lockdown v1. Audit + remediation.

**Model ID fix:** OpenRouter uses `openai/gpt-oss-120b` (not `openrouter/openai/gpt-oss-120b`). Corrected 2026-03-15.

---

## 1. Remaining Non-OSS Model Paths Found

| Path | Location | Status |
|------|----------|--------|
| **data/settings.json** | `openrouter_model`: "x-ai/grok-4.1-fast" | **ACTIVE** — persisted UI selection |
| **.env** | OPENROUTER_MODEL=openai/gpt-oss-120b | Aligned |
| **OpenClaw** | openclaw.json, agents/main/agent/models.json | Already locked |

### Root Cause: Persisted Settings

The UI saves `openrouter_model` to `data/settings.json`. When provider is "openrouter", the router used `settings.get("openrouter_model") or OPENROUTER_MODEL`. The persisted value "x-ai/grok-4.1-fast" overrode config defaults.

---

## 2. Which Path(s) Caused Grok Usage

**Primary:** `data/settings.json` → `openrouter_model: "x-ai/grok-4.1-fast"` with `provider: "openrouter"`.

Flow: Chat API → pipeline → router → `or_m = settings.get("openrouter_model") or OPENROUTER_MODEL` → grok used for all OpenRouter chat.

---

## 3. Files/Configs Changed

| File | Change |
|------|--------|
| `gerty/config.py` | Added `LOCKED_OPENROUTER_MODEL = "openai/gpt-oss-120b"` |
| `gerty/llm/router.py` | Use `LOCKED_OPENROUTER_MODEL` instead of settings/body for OpenRouter |
| `gerty/settings.py` | Load override: always return `LOCKED_OPENROUTER_MODEL` for openrouter_model; save validation: never persist non-OSS |
| `gerty/diagnostics.py` | Added settings_openrouter_model check; use LOCKED_OPENROUTER_MODEL |
| `data/settings.json` | Overridden at load; save validation rejects non-OSS |
| `.env` | OPENROUTER_MODEL=openai/gpt-oss-120b |

---

## 4. What Was Removed or Aligned

- **Removed:** Settings/body ability to select non-OSS models for OpenRouter
- **Aligned:** Router always uses LOCKED_OPENROUTER_MODEL for OpenRouter paths
- **Aligned:** Settings load/save enforce gpt-oss-120b
- **Aligned:** .env OPENROUTER_MODEL format

---

## 5. Validation Results

```bash
python -m gerty --governance
```

Expected: model_lock_gerty pass, settings_openrouter_model pass.

---

## 6. GPT-OSS-Only Enforcement Status

**Complete** for Gerty native paths:

- Router: hardcoded LOCKED_OPENROUTER_MODEL
- Settings: load override + save validation
- Config defaults: gpt-oss-120b
- model_profiles.json: all gpt-oss-120b
- OpenClaw: openclaw.json already locked

**OpenClaw** uses its own config; no per-session overrides found. OpenClaw and Gerty use different OpenRouter API keys; if Grok still appears, it would be from OpenClaw. Verify OpenClaw openclaw.json has no openrouter/auto and primary is gpt-oss-120b.
