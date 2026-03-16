# State of the System

> **Purpose:** Full-picture summary for new sessions. Read this first to understand where we are, what was fixed, what remains fragile, and what to do next.  
> **Last updated:** 2026-03-16

---

## Guardrails (New)

**Impact Guard** — Cursor must assess impact and warn before large/risky changes. See `docs/IMPACT_GUARD.md`. Copy to `.cursor/rules/impact-guard.mdc` for enforcement. Reduces blind edits, duplicates, and regressions.

---

## Big Picture

Gerty should feel like a **real Jarvis-style assistant** — not a chatbot with occasional tools.

Core requirements:

- No command memorization
- No exact keyword dependence
- Desktop app is the real product surface
- Natural language in, correct action out
- OpenClaw used for the power it already has
- Gerty and OpenClaw work as one unified system

Over this stretch of work:

1. **The architecture got much better**
2. **The live user experience was often worse than it should have been**

That tension is the core story.

---

## What the Early Work Achieved

### Runtime governance and stabilization

- Model lock-down
- OpenClaw memory reset / cleanup
- Bootstrap ownership fixes
- Diagnostics and transparency tools
- Clearer execution boundary
- Stronger governance

### Strategic realization

**OpenClaw should not be treated like a side tool.** It should be treated as the **capability engine** inside the Gerty system.

- **Gerty** = intelligence, memory, policy, orchestration
- **OpenClaw** = execution runtime, tools, browser, skills, Google actions, local actions

### Phase 3.0A — OpenClaw audit / recovery

- Audited OpenClaw capability surface
- Restored gog as correct path for Google writes
- Established OpenClaw-first policy

### Phase 3.0B — End-to-end proof

- Calendar create ✓
- Gmail send ✓
- Browser open via xdg-open ✓
- Diagnostics ✓

### Single-backend stabilization

Calendar, Gmail, Drive → all via OpenClaw/gog (no split read/write paths that caused trust contradictions).

### LLM intent router

Specialized intent router infers meaning and routes accordingly — natural language, messy STT tolerated, no exact-phrase dependence.

---

## What Was Broken (and What We Fixed in Pass 4)

### 1. Wrong-layer security screening — **FIXED**

**Problem:** `screen_openclaw_message()` applied shell-command patterns (e.g. `\bpass\s+`) to the raw user message. "send email subject test pass 4" was blocked.

**Fix:** Command-pattern screening only for direct command requests ("run ", "execute ", "exec "). Normal assistant requests pass through.

**File:** `gerty/security.py` — `_is_direct_command_request()`

### 2. Timezone/date-context bug — **FIXED**

**Problem:** `get_date_context()` fell back to UTC when `tz=None`. "Tomorrow" resolved wrong for Europe/London users.

**Fix:** Use `GERTY_TIMEZONE` when `tz` is None.

**File:** `gerty/utils/date_context.py`

### 3. Launch/open execution path — **FIXED**

**Problem:** "launch youtube", "open spotify" — OpenClaw sometimes printed command as text instead of executing; or app_launch failed for known sites.

**Fix:** Known sites (youtube, spotify, netflix, gmail, github) → native `xdg-open` in browser before desktop lookup. Action-first, no link-first.

**Files:** `gerty/utils/app_launcher.py`, `gerty/tools/app_launch.py`

### 4. Write verification — **IMPROVED (Stage B)**

Stage B follow-up verification when Stage A patterns fail. Calendar: `gog calendar events` for target date. Email: `gog gmail search` for subject. Still verify in live runs.

### 5. Speculative internal explanations — **IMPROVED**

`EXECUTION_INTROSPECTION_NOTE` limits answers about "what happened internally" to factual execution statements. No invented architecture.

### 6. User profile resolution — **ADDED**

`config/user_profile.json` — "send email to myself" / "email me" resolve to user's email.

---

## What Is Still Fragile

- **Date/time resolution** — Verify "tomorrow", "next week" in live desktop app
- **Write verification/reporting** — Stage B helps but live consistency needs validation
- **Action-first for launch/open** — Native path helps; OpenClaw path may still print instead of execute in some cases
- **Grounding of internal explanations** — Improvement in place; monitor for drift
- **Consistency between implementation and desktop behavior** — Always validate in the desktop app after changes

---

## Current State (Plain English)

**The system is no longer stupid in the same way it was before.**

**But it is still too inconsistent to trust comfortably.**

We are past the "basic architecture" problem and deep inside the **"refinement / stabilization / trustworthiness"** problem.

### What is solid

- Core architecture is much better
- OpenClaw correctly treated as default execution engine
- Desktop app/runtime is far more inspectable
- Google/OpenClaw routing is much closer to correct
- Intent-router approach is the right direction
- Real calendar reads, writes, Drive reads, diagnostics, and some browser opens have worked in the live system

### What is still fragile

- Date/time resolution
- False-positive security blocking (fixed in code; verify in live)
- Write verification/reporting
- Action-first execution for launch/open
- Grounding of internal explanations
- Consistency between implementation and desktop behavior

---

## Why This Has Felt Painful

The work has mostly moved through this loop:

1. Identify a real issue
2. Add a fix / guard / routing rule
3. That fix introduces a regression elsewhere
4. Patch the regression
5. Another edge case appears

This is common in agent systems, but brutal when building a personal assistant you want to use every day.

**The system often improved "on paper" before it improved "in your hands."**

---

## The Right Direction (Emerging Architecture)

### Gerty

- Intent
- Memory/context
- Orchestration
- Safety
- Final response

### OpenClaw

- Execution
- gog / Google
- Browser
- Local machine
- Skills
- Tools

### Between them

- A bounded LLM router: infer meaning, choose domain/backend, prefer action, require verification

---

## What Still Needs to Happen

**Do not do another broad redesign.**

Focus on **very focused regression repair** around the concrete remaining issues:

- Fix relative-date/timezone handling (done; verify in desktop)
- Fix wrong-layer security screening (done; verify in desktop)
- Fix launch/open execution reliability (done for known sites; verify in desktop)
- Finish robust Stage B verification
- Stop speculative internal explanations (improved; monitor)
- **Validate everything in the desktop app only**

That is the shortest path from "clever but flaky" to "actually usable."

---

## Key Lessons

1. **Original instincts were mostly right** — OpenClaw leaned into, not worked around; no exact phrase dependence; desktop app is real surface; natural language through smart router; one domain through one backend during stabilization.

2. **Complexity has repeatedly hurt trust** — Multiple backends, keyword hacks, fallback layers, speculative output, mismatched runtime contexts all hurt trust.

3. **The right direction is now clear** — Gerty = intelligence/orchestration; OpenClaw = execution; bounded LLM router between them.

---

## Bottom Line

**Gerty is no longer conceptually confused.**

**It is now practically inconsistent.**

That is a much better problem than where we started, but it still needs focused repair.

---

## Session Start Checklist (for Cursor Agent)

When starting a new session:

1. Read `docs/STATE_OF_THE_SYSTEM.md` (this file)
2. Read `docs/GERTY_SYSTEM_ARCHITECTURE.md` §8–9
3. Read `memory/YYYY-MM-DD.md` for today's context
4. Read `docs/BUILD_PLAN_PROGRESS.md` when touching build-plan work
5. Read `docs/PASS_4_REGRESSION_FIX.md` for latest regression fixes and verification steps
6. **Validate in the desktop app** — not just tests
