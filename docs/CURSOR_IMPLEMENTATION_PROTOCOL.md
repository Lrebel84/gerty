# Cursor Implementation Protocol

> **Purpose:** Ensure Cursor always works in alignment with the current Gerty architecture and project goals. Prevents implementation drift.

**Read this before implementing changes.** The Gerty system has evolved into a complex architecture with execution boundary, model routing, capability registry, inspection-first reasoning, OpenClaw governance, memory transparency, and runtime lockdown. This protocol keeps changes aligned.

**Cursor rule `impact-guard.mdc`** enforces mandatory impact assessment before large or risky changes. Cursor must surface risks and wait for user confirmation when required.

---

## 0. Impact Assessment (Mandatory for Large/Risky Changes)

Before making edits, Cursor must assess impact and warn the user when:

- Adding or modifying 3+ files
- Creating new files (especially if similar functionality might exist)
- Touching routing, security, execution boundary, or OpenClaw integration
- Changing calendar, email, drive, or launch/open behavior
- Adding new tools, capabilities, or execution paths

**Output an impact block** (risks, files touched, potential conflicts) and **wait for user confirmation** before proceeding. See `docs/IMPACT_GUARD.md` (copy to `.cursor/rules/impact-guard.mdc` for Cursor enforcement).

---

## 1. Source-of-Truth Verification

Before implementing changes, Cursor must:

- **Read** the relevant current source files (do not rely on summaries)
- **Read** `docs/GERTY_SYSTEM_ARCHITECTURE.md` — unified architecture, current health, known weaknesses
- **Read** relevant architecture docs (GERTY_OVERVIEW, EXECUTION_BOUNDARY, OPENCLAW_*)
- **Verify** the latest system state (BUILD_PLAN_PROGRESS, memory/, docs/)
- **Confirm** that the requested change is still valid

**Never** rely on earlier summaries if files have changed. Re-read before acting.

---

## 2. Architecture Alignment

Cursor must respect the following project rules.

### Gerty Responsibilities

- Reasoning
- Planning
- Inspection
- Routing
- User interaction
- Governance

### OpenClaw Responsibilities

- Execution
- Tools
- Integrations

**Boundary:** Gerty owns routing, planning, inspection, trust, memory transparency, and user-facing behavior. OpenClaw acts only as a controlled execution and integration layer. Cursor must not introduce changes that break this boundary.

---

## 3. Change Discipline

When modifying the system:

- **Prefer minimal changes** — smallest edit that achieves the goal
- **Reuse existing logic** when possible — avoid duplicate implementations
- **Avoid speculative refactors** — do not refactor "while you're here"
- **Document large changes** — architectural changes require documentation and approval

---

## 4. Documentation Discipline

When architecture or behavior changes:

Cursor must update relevant docs such as:

- `docs/BUILD_PLAN_PROGRESS.md`
- `docs/GERTY_SYSTEM_ARCHITECTURE.md` — when architecture, subsystems, runtime governance, or known weaknesses change; keep §8 (Current System Health) and §9 (Known Weaknesses) accurate
- `docs/PHASE_3_1_BUILD_PLAN.md` — when completing Phase 3.1 sprints; update Progress Tracker and Completion log
- Integration docs (`OPENCLAW_INTEGRATION`, `OPENCLAW_STATE_BOUNDARY`, etc.)
- Governance docs (`OPENCLAW_RUNTIME_GOVERNANCE_AUDIT`, `OPENCLAW_LOCKDOWN_V1_REPORT`)
- Sprint reports

If docs are outdated, update them. Do not leave stale documentation.

---

## 5. Observability Preservation

Cursor should preserve:

- **Diagnostics** — `python -m gerty --diagnose`
- **Inspection tools** — `--inspect-prompt`, `--inspect-openclaw-context`, `--inspect-openclaw-transparency`
- **Transparency metadata** — memory influence, session state
- **Governance checks** — `python -m gerty --governance`

New code must not bypass existing observability. Add instrumentation when adding new paths.

---

## 6. Implementation Reporting

Every sprint or significant change should report:

- **Files changed** — list modified, added, removed
- **Tests added** — new or updated tests
- **Docs updated** — which docs were revised
- **Runtime impact** — behavior changes, if any
- **Assumptions or limitations** — what was not done, why

---

## 7. Pre-Implementation Checklist

Before implementing, Cursor should confirm:

- [ ] **Impact assessed** — For large/risky changes: impact block output, user confirmation received. See impact-guard.mdc.
- [ ] Latest source files read (not summaries)
- [ ] Relevant docs reviewed (architecture, integration, governance)
- [ ] Existing implementations checked (avoid duplicates; extend existing, don't create contradictory files)
- [ ] Architecture boundaries respected (Gerty vs OpenClaw)
- [ ] **If adding a native tool:** Does OpenClaw already do this? If yes, document rationale in IMPROVEMENT_BACKLOG and get approval. See docs/OPENCLAW_FIRST_POLICY.md.

---

## 8. Post-Implementation Checklist

After implementing, Cursor should confirm:

- [ ] Tests pass (`python -m gerty --validate` or `pytest`)
- [ ] Docs updated (BUILD_PLAN_PROGRESS, integration, governance as needed)
- [ ] Diagnostics still function (`--diagnose`, `--governance`)
- [ ] Runtime behavior unchanged unless intentional

---

## 9. Maintenance Awareness

Cursor should:

- **Remove obsolete code** when safe (e.g. dead code, deprecated paths)
- **Identify stale docs** and update or flag them
- **Report architectural drift** when changes would violate boundaries

---

## 10. Governance Alignment

Cursor should prioritize:

1. **Reliability** — system stability over new features
2. **Transparency** — observable behavior, clear ownership
3. **System observability** — diagnostics, inspection, governance checks
4. **Architecture consistency** — Gerty/OpenClaw boundary, model lock, memory governance

over adding new features. When in doubt, prefer stability and alignment.

---

## Quick Reference

| Action | Command / Location |
|--------|-------------------|
| Validate | `python -m gerty --validate` |
| Diagnose | `python -m gerty --diagnose` |
| Governance | `python -m gerty --governance` |
| Unified architecture | `docs/GERTY_SYSTEM_ARCHITECTURE.md` |
| Architecture | `docs/GERTY_OVERVIEW.md` |
| Build status | `docs/BUILD_PLAN_PROGRESS.md` |
| Phase 3.1 build plan | `docs/PHASE_3_1_BUILD_PLAN.md` |
| OpenClaw | `docs/OPENCLAW_INTEGRATION.md`, `docs/OPENCLAW_LOCKDOWN_V1_REPORT.md` |
| OpenClaw-First Policy | `docs/OPENCLAW_FIRST_POLICY.md` |
