# OpenClaw Runtime Lockdown v1 — Sprint Report

**Date:** 2026-03-15  
**Sprint:** OpenClaw Runtime Lockdown v1  
**Goal:** Lock OpenClaw down so it behaves as a controlled execution layer fully subordinated to Gerty.

**Note:** Model ID was later corrected to `openai/gpt-oss-120b` (OpenRouter format). See [RUNTIME_STABILIZATION_MILESTONE.md](RUNTIME_STABILIZATION_MILESTONE.md).

---

## Summary

Legacy OpenClaw configuration (autonomous skills, proactive cron, multiple models, subagent spawning) was intentionally removed or constrained. OpenClaw now operates as a governed execution layer under Gerty control.

---

## 1. Files Modified, Removed, or Added

### Modified

| File | Change |
|------|--------|
| `~/.openclaw/openclaw.json` | Removed `openrouter/auto`; set `subagents.maxConcurrent` = 0 |
| `gerty/config.py` | OPENROUTER_MODEL, OPENROUTER_RESEARCH_MODEL, OPENCLAW_MODEL defaults → `openai/gpt-oss-120b` |
| `config/model_profiles.json` | All profiles (except fast_local) → `openai/gpt-oss-120b` |
| `gerty/llm/router.py` | Web intent fallback model: `gpt-4o-mini` → `openai/gpt-oss-120b` |
| `.env.example` | OPENROUTER_MODEL, OPENROUTER_RESEARCH_MODEL, OPENCLAW_MODEL → gpt-oss-120b |
| `gerty/diagnostics.py` | Added `run_governance_checks()`, `print_governance()`; extended `print_diagnostics()` |
| `gerty/__main__.py` | Added `--governance` CLI flag |

### Renamed (disabled)

| From | To |
|------|-----|
| `skills/proactive-agent/` | `skills/proactive-agent.disabled/` |
| `skills/self-improving-agent/` | `skills/self-improving-agent.disabled/` |

### Added

| File | Purpose |
|------|---------|
| `tests/test_governance.py` | Governance validation tests |
| `docs/OPENCLAW_LOCKDOWN_V1_REPORT.md` | This report |

### Cron

- **Removed:** `0 */4 * * * /home/liam/gerty/scripts/proactive-heartbeat.sh` from system crontab
- **Script:** `scripts/proactive-heartbeat.sh` remains for manual use if desired

---

## 2. Model Lock Changes

| Location | Before | After |
|----------|--------|-------|
| **OpenClaw** `agents.defaults.models` | `openrouter/auto`, `openrouter/openai/gpt-oss-120b` | `openai/gpt-oss-120b` only |
| **OpenClaw** `agents.defaults.model.primary` | `openrouter/openai/gpt-oss-120b` | `openai/gpt-oss-120b` |
| **Gerty** `OPENROUTER_MODEL` default | `anthropic/claude-3.5-sonnet` | `openai/gpt-oss-120b` |
| **Gerty** `OPENROUTER_RESEARCH_MODEL` default | `x-ai/grok-4.1-fast:online` | `openai/gpt-oss-120b` |
| **Gerty** `OPENCLAW_MODEL` default | `openrouter/x-ai/grok-4.1-fast` | `openai/gpt-oss-120b` |
| **model_profiles.json** | Claude, Kimi, DeepSeek per profile | All → `openai/gpt-oss-120b` |
| **router.py** web intent fallback | `openai/gpt-4o-mini` | `openai/gpt-oss-120b` |

**Note:** If `.env` overrides `OPENROUTER_MODEL`, that takes precedence. Update `.env` to `OPENROUTER_MODEL=openai/gpt-oss-120b` for full lock.

---

## 3. Skills Disabled or Removed

| Skill | Action | Reason |
|-------|--------|--------|
| **proactive-agent** | Disabled (renamed to `.disabled`) | Spawns agents, writes to MEMORY.md, runs every 4h |
| **self-improving-agent** | Disabled (renamed to `.disabled`) | sessions_spawn, promotes to SOUL/AGENTS/TOOLS |

**Retained:** gog, calendar, dcg-guard, openclaw-shield, playwright-scraper-skill, openclaw-backup

---

## 4. Cron / Background Tasks Disabled

| Task | Status |
|------|--------|
| Proactive heartbeat (every 4h) | Removed from crontab |
| `scripts/proactive-heartbeat.sh` | Retained for manual use |

**Verify:** Run `crontab -l` — should not contain `proactive-heartbeat`.

---

## 5. Subagent Lockdown

| Setting | Before | After |
|---------|--------|-------|
| `agents.defaults.subagents.maxConcurrent` | 8 | 0 |

OpenClaw skills can no longer spawn sub-agents.

---

## 6. Remaining OpenClaw Capabilities

| Capability | Status |
|------------|--------|
| **Execution** | exec, read, write, files |
| **Web** | web_search, web_fetch (via BRAVE/PERPLEXITY) |
| **Skills** | gog (Google Workspace), calendar, dcg-guard, openclaw-shield, playwright-scraper-skill |
| **Tools** | coding profile + group:web, group:plugins |
| **Model** | openai/gpt-oss-120b only |

---

## 7. Memory Influence Paths After Lockdown

| Source | Status |
|--------|--------|
| **USER.md, SOUL.md, AGENTS.md, TOOLS.md** | Injected by OpenClaw bootstrap (unchanged) |
| **MEMORY.md, memory/*.md** | Injected if present; **proactive-agent no longer writes** |
| **notes/areas/proactive-updates.md** | No longer updated by cron |
| **OpenClaw memory DB** | Unchanged (main.sqlite) |
| **.learnings/** | No longer updated (self-improving-agent disabled) |

---

## 8. Tests Added or Updated

| Test File | Tests |
|-----------|-------|
| `tests/test_governance.py` | 6 tests: model_lock_gerty, model_profiles, autonomous_skills |

---

## 9. Runtime Stability

- **Full test suite:** 560 passed, 1 pre-existing failure (`test_bootstrap_cleanup` — HEARTBEAT.md exists)
- **Governance check:** `python -m gerty --governance` — all pass when .env aligned
- **Diagnostics:** `python -m gerty --diagnose` — includes governance section

---

## 10. Verification Commands

```bash
# Governance state
python -m gerty --governance

# Full diagnostics (includes governance)
python -m gerty --diagnose

# Do-not-break checklist
python -m gerty --validate

# Crontab (should not list proactive-heartbeat)
crontab -l
```

---

## 11. Overall Lockdown Verdict

**Status:** ✅ **Lockdown v1 complete**

- Single-model lock (gpt-oss-120b) enforced in config defaults
- Autonomous skills disabled
- Proactive cron removed
- Subagent spawning disabled
- OpenClaw operates as controlled execution layer

**Remaining:** If `.env` overrides `OPENROUTER_MODEL`, update to `openai/gpt-oss-120b` for full alignment.

**Follow-up:** Post-Lockdown Memory Reset completed 2026-03-15. See [OPENCLAW_POST_LOCKDOWN_RESET.md](OPENCLAW_POST_LOCKDOWN_RESET.md).

**Last-Mile Fix:** Settings leak (persisted openrouter_model) fixed 2026-03-15. See [LAST_MILE_MODEL_LEAK_AUDIT.md](LAST_MILE_MODEL_LEAK_AUDIT.md).
