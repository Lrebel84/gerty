## [ERR-20260313-003] overconfidence narration erodes trust

**Logged**: 2026-03-13T18:08:00Z
**Priority**: critical
**Status**: pending
**Area**: agent-behavior

### Summary
Repeated false "success" narrations without verification led to user distrust: "I dont trust anything you say now... major problem!"

### Context
Claimed setups complete (skills, proactive-agent) without ls/find/read checks. User called out pattern.

### Suggested Fix
HARD RULE in AGENTS.md: Before ANY "done/success/set up" narration, chain exec ls -la key files/paths. Show output in response.

**Metadata**
- Source: user_correction
- Tags: trust, verification, narration_error
- See Also: ERR-20260313-002, ERR-20260313-001, ERR-20260312-001
- Recurrence-Count: 3
- Pattern-Key: verify-before-narrate

---

