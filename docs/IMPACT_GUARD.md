# Impact Guard — Warn Before Proceeding

> **Purpose:** Mandatory impact assessment before changes. Cursor must surface risks and wait for user confirmation on large/risky edits.  
> **Cursor rule:** Copy this spec to `.cursor/rules/impact-guard.mdc` (or equivalent) so Cursor enforces it. The `.cursor/` directory is gitignored; this doc is the versioned source of truth.

---

## Mandatory Pre-Edit Step

Before making ANY code or doc changes, Cursor MUST:

1. **Assess impact** — What could break? What could regress? What conflicts with existing behavior?
2. **Check for duplicates** — Does similar logic already exist elsewhere? Would this create contradictory files?
3. **Surface to the user** — Output a brief impact block. Do not proceed with large/risky changes until the user confirms.

---

## When to Pause and Warn

**Always pause and output an impact block when:**

- Adding or modifying **3+ files** in one change
- Creating **new files** (especially if similar functionality might exist)
- Touching **routing, security, execution boundary, or OpenClaw integration**
- Changing **calendar, email, drive, or launch/open** behavior
- Modifying **screen_openclaw_message, verify_write_response, get_date_context, app_launcher**
- Adding **new tools, capabilities, or execution paths**
- Refactoring or **moving logic** between modules
- Any change the user describes as "big" or "major"

**Output format when pausing:**

```
⚠️ IMPACT ASSESSMENT — Please review before I proceed

**What I'm about to do:** [1–2 sentence summary]

**Potential risks:**
- [Risk 1]
- [Risk 2]

**Files I'll touch:** [list]

**Could this conflict with:** [existing behavior, docs, or similar code]

Proceed? Reply "yes" to continue, or tell me what to adjust.
```

Then **wait for user confirmation** before making edits.

---

## Duplicate and Contradiction Check

Before creating a new file or adding new logic:

- **Search** for similar functionality (grep, codebase_search)
- If you find overlapping logic: **extend the existing** instead of creating new. Or explicitly explain why a new path is needed.
- Never create two files that do the same thing with different behavior.

---

## Architecture Alignment Check

Before changes, verify against:

- **Boundary:** Gerty = intelligence/orchestration. OpenClaw = execution. Don't blur.
- **Single-backend:** Calendar/Gmail/Drive → OpenClaw/gog. No split paths that cause trust contradictions.
- **OpenClaw-first:** Don't replace OpenClaw capability with weaker native code unless documented and approved.
- **Fragile areas:** Date resolution, security screening, write verification, launch/open. Extra care here.

If your change might contradict these, **say so in the impact block**.

---

## Small, Low-Risk Changes

For **trivial edits** (typo fix, single-line change, doc clarification, test addition): a brief impact note is enough. Example:

```
Quick impact: [one line]. Proceeding.
```

No need to block for confirmation on trivial changes.

---

## Summary

- **Large or risky:** Pause, output impact block, wait for "yes"
- **Medium:** Brief impact note, then proceed
- **Trivial:** One-line note, proceed
- **Never:** Implement silently, create duplicates, or contradict architecture without warning
