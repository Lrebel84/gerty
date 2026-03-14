"""Inspection-First Planning Mode v3.1 — require inspection before advice.

For system-analysis and improvement requests that ask to review, audit,
analyze, or inspect the current implementation, Gerty must inspect relevant
local docs and the capability registry before answering. Reduces generic
or guessed answers.

v3.1: Backlog reference validation, invented-metric suppression, recommendation
diversity, health-check triggers, audit/review tone. See docs/INSPECTION_FIRST_MODE.md.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import NamedTuple

from gerty.utils.markdown_sections import parse_markdown_sections, section_relevance_score

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Exact phrases — immediate trigger (v1 + v2 + v3 strategic)
# v3: Strategic improvement prompts route here; checked BEFORE planning suppressors
INSPECTION_FIRST_PHRASES = (
    "look into the existing structure",
    "look into the existing",
    "review the current system",
    "review the current implementation",
    "audit gerty",
    "audit the system",
    "inspect the current implementation",
    "inspect the current",
    "review what we've built",
    "review what we have built",
    "suggest improvements based on",
    "suggest improvements from",
    "what's missing based on",
    "what is missing based on",
    # v2: natural phrasing
    "analyze our setup",
    "what should we fix first",
    "what are the weak spots",
    "review what we have now",
    "where is gerty still weak",
    "what should we tighten up next",
    "look over the current implementation",
    "weak spots in gerty",
    "gaps in the current",
    # v3: strategic improvement prompts (take precedence over grounded planning)
    "create a plan to improve gerty",
    "suggest improvements to gerty",
    "evaluate the current architecture",
    "look over the setup",
    # v3.1: health-check and audit coverage (IB-047)
    "health check",
    "system health",
    "sanity check",
    "system audit",
    "architecture review",
)

# Cues for cue+context path (expanded v2)
INSPECTION_CUES = (
    "look into", "review", "audit", "inspect", "existing structure",
    "current system", "current implementation", "what we've built",
    "skills", "tools", "suggest improvements",
    "analyze", "fix first", "weak spots", "tighten up", "look over",
    "what we have now", "gaps", "weaknesses", "improve",
)
SYSTEM_CONTEXT_CUES = (
    "gerty", "system", "implementation", "structure", "built",
    "skills", "tools", "capabilities", "architecture",
    "setup", "weak", "gaps", "codebase",
)

# v2: Keyword scoring for broader detection (word -> score)
# v3.1: health, sanity, audit for trigger coverage
INSPECTION_KEYWORDS = {
    "analyze": 2, "audit": 2, "review": 2, "inspect": 2,
    "weak": 2, "gaps": 2, "fix": 2, "tighten": 2, "improve": 2,
    "setup": 1, "first": 1, "spots": 1, "gerty": 1,
    "implementation": 1, "structure": 1, "built": 1,
    "health": 2, "sanity": 2,
}
INSPECTION_SCORE_THRESHOLD = 3

# Casual phrases that suppress inspection (avoid false positives)
CASUAL_SUPPRESSORS = (
    "hello", "hi", "hey", "thanks", "thank you", "ok", "okay",
    "good morning", "good evening", "how are you", "what's up",
)

# Planning-only phrases: trigger grounded planning, not inspection-first
# v3: Narrowed — "create a plan to improve gerty" now in INSPECTION_FIRST_PHRASES (checked first)
PLANNING_SUPPRESSORS = (
    "what should we build next",
    "design the next upgrade",
    "next improvement",
    "what to build next",
)

# Minimum message length (bypassed when exact phrase matches)
INSPECTION_MIN_LENGTH = 20

# Sources: extended beyond grounded planning
# v3: LIVE_VALIDATION_FINDINGS.md optional — included when present
INSPECTION_SOURCES = [
    "docs/BUILD_PLAN_PROGRESS.md",
    "docs/IMPROVEMENT_BACKLOG.md",
    "docs/GERTY_OVERVIEW.md",
    "docs/GERTY_VISION.md",
    "docs/MODEL_ROUTING.md",
    "docs/EXECUTION_BOUNDARY.md",
    "docs/GROUNDED_PLANNING_MODE.md",
    "docs/CAPABILITY_REGISTRY.md",
]
LIVE_VALIDATION_SOURCE = "docs/LIVE_VALIDATION_FINDINGS.md"

# Relevance keywords for section scoring
RELEVANCE_KEYWORDS = (
    "completed", "status", "done", "backlog", "limitation", "bottleneck",
    "next", "weakness", "open", "upgrade", "improvement", "phase",
    "capability", "execution", "routing", "planning", "source",
)

# Total cap for inspection context
INSPECTION_CONTEXT_MAX_CHARS = 4500

# Base instruction — v3.1: backlog refs, invented metrics, tone, recommendation diversity
INSPECTION_INSTRUCTION_BASE = (
    "**Inspection-First Mode:** Answer ONLY from the inspected context below. "
    "Do NOT guess, invent, or speculate about tools, capabilities, architecture, or metrics.\n\n"
    "**Observed facts** — Must come directly from inspected sources. "
    "If something is not in the sources, say so rather than guess.\n\n"
    "**Inferred conclusions** — Must be clearly grounded in observed facts. "
    "Do not present guesses as facts.\n\n"
    "**Avoid speculative filler:** No guessed frameworks, architecture components, "
    "implementation details, performance metrics, percentages, or reliability estimates. "
    "Prefer stricter factual discipline over expansive analysis.\n\n"
    "**Do NOT invent:** scores (e.g. 8/10), percentages, timelines (e.g. 1-sprint fix), "
    "risk levels, readiness grades, sprint estimates. If not in sources, omit.\n\n"
    "**Tone:** Use professional report-style. No emojis. No casual sign-offs. "
    "No conversational closings (e.g. 'Ready to code?', 'What's our next move?').\n\n"
    "Structure your response as:\n\n"
    "1. **Current state observed** — Facts from inspected sources only (no invented details).\n"
    "2. **Main bottleneck** — Single biggest limitation from observed state.\n"
    "3. **Best next improvement** — ONE prioritized recommendation.\n"
    "4. **Why it's the best next step** — Brief justification tied to open limitations, "
    "recent validated weaknesses, or architectural reliability gaps from inspected state.\n"
    "5. **Optional follow-ups** — 1–2 items if relevant.\n\n"
    "**Recommendation quality:** Tie to current open limitations, recent validated weaknesses, "
    "repeated drift risks, or actual inspected project state. "
    "Vary the recommendation by prompt focus: fix-first → reliability; audit → risk/architecture; "
    "health-check → stability. Do not default to the same recommendation for every prompt.\n\n"
    "**IB reference:** When citing backlog items, use the exact IB-ID from the inspected backlog. "
    "IB-015 = Agent memory growth management. IB-016 = Agent tool capability enforcement (when tool dispatch enabled). "
    "Never conflate these. If unsure, reference the concept without an IB number.\n\n"
    "If uncertain from sources, say so."
)
# Backward compat
INSPECTION_INSTRUCTION = INSPECTION_INSTRUCTION_BASE


class InspectionResult(NamedTuple):
    """Result of inspection-first mode (v3: extended observability)."""

    context: str
    factual_summary: str
    sources_used: list[str]
    total_chars: int
    triggered: bool
    trigger_reason: str
    sources_considered: list[str] = ()
    extracted_headings: list[tuple[str, str]] = ()
    capability_registry_used: bool = False
    # v2 observability
    summary_signals_used: tuple[str, ...] = ()
    recommendation_basis: str = ""
    backlog_signals_influenced: bool = False
    # v3 observability
    live_validation_signals_influenced: bool = False


def _section_relevance(heading: str, content: str) -> int:
    """Score a section by relevance to inspection."""
    return section_relevance_score(heading, content, RELEVANCE_KEYWORDS)


def _extract_relevant(text: str, max_chars: int, priority_headings: tuple[str, ...]) -> str:
    """Extract relevant sections by heading or relevance score."""
    sections = parse_markdown_sections(text)
    parts = []
    for heading, content in sections:
        h_lower = heading.lower()
        if any(p in h_lower for p in priority_headings) or _section_relevance(heading, content) >= 1:
            if content:
                excerpt = content[:max_chars // 2] if len(content) > max_chars // 2 else content
                parts.append(f"### {heading}\n{excerpt}")
    return "\n\n".join(parts)[:max_chars] if parts else text[:max_chars]


def _extract_from_build_plan(text: str, max_chars: int) -> str:
    """Extract from BUILD_PLAN_PROGRESS.md."""
    return _extract_relevant(text, max_chars, ("quick status", "completed work", "how to pick up"))


def _extract_from_backlog(text: str, max_chars: int) -> str:
    """Extract open backlog items."""
    sections = parse_markdown_sections(text)
    open_items = []
    for heading, content in sections:
        if re.match(r"^IB-\d+$", heading.strip()):
            if "**status** | open" in content or "| open |" in content:
                title_match = re.search(r"\*\*title\*\* \| ([^\n|]+)", content)
                title = title_match.group(1).strip() if title_match else heading
                open_items.append(f"- {title} ({heading})")
    if open_items:
        return "## Open Backlog Items\n\n" + "\n".join(open_items[:12])[:max_chars]
    return text[:max_chars]


def _build_ib_reference_card(backlog_raw: str) -> str:
    """
    Extract IB-ID → title mapping from backlog for correct attribution (v3.1).
    Prevents IB-015/IB-016 conflation.     Returns compact reference block.
    """
    sections = parse_markdown_sections(backlog_raw)
    mappings = []
    for heading, content in sections:
        if re.match(r"^IB-\d+$", heading.strip()):
            title_match = re.search(r"\*\*title\*\* \| ([^\n|]+)", content)
            title = title_match.group(1).strip() if title_match else heading
            mappings.append(f"{heading} = {title}")
    if not mappings:
        return ""
    return "## IB Reference (verify before citing)\n\n" + "\n".join(mappings[:25])




def _extract_from_overview(text: str, max_chars: int) -> str:
    """Extract from GERTY_OVERVIEW.md."""
    return _extract_relevant(text, max_chars, ("what is gerty", "key components", "request flow"))


def _extract_from_vision(text: str, max_chars: int) -> str:
    """Extract from GERTY_VISION.md."""
    return _extract_relevant(text, max_chars, ("development phases", "project purpose", "summary"))


def _extract_from_doc(text: str, max_chars: int) -> str:
    """Generic extractor: first N chars of relevant sections."""
    return _extract_relevant(text, max_chars, ("what it is", "when", "sources", "limitations", "schema"))


_EXTRACTORS = {
    "docs/BUILD_PLAN_PROGRESS.md": _extract_from_build_plan,
    "docs/IMPROVEMENT_BACKLOG.md": _extract_from_backlog,
    "docs/GERTY_OVERVIEW.md": _extract_from_overview,
    "docs/GERTY_VISION.md": _extract_from_vision,
}

_SOURCE_MAX_CHARS = {
    "docs/BUILD_PLAN_PROGRESS.md": 900,
    "docs/IMPROVEMENT_BACKLOG.md": 800,
    "docs/GERTY_OVERVIEW.md": 500,
    "docs/GERTY_VISION.md": 500,
    "docs/MODEL_ROUTING.md": 400,
    "docs/EXECUTION_BOUNDARY.md": 400,
    "docs/GROUNDED_PLANNING_MODE.md": 400,
    "docs/CAPABILITY_REGISTRY.md": 400,
    LIVE_VALIDATION_SOURCE: 600,
}


def _read_file(path: Path) -> str:
    """Read file content. Returns empty string on error."""
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError as e:
        logger.debug("Inspection-first: could not read %s: %s", path, e)
        return ""


def _build_factual_summary_v3(
    sources_used: list[str],
    capability_registry_used: bool,
    build_plan_raw: str,
    backlog_raw: str,
    live_validation_raw: str,
) -> tuple[str, list[str], str, bool, bool]:
    """
    Build synthesized factual summary (v3). Prioritizes: current architecture,
    recent upgrades, live validation findings, active limitations, backlog.
    Returns (summary, signals_used, recommendation_basis, backlog_influenced, live_validation_influenced).
    """
    signals: list[str] = []
    parts: list[str] = []
    backlog_influenced = False
    live_validation_influenced = False

    # 1. Current architecture state
    if "docs/BUILD_PLAN_PROGRESS.md" in str(sources_used) and build_plan_raw:
        signals.append("build_plan")
        if "Build plan complete" in build_plan_raw or "Sprints 0" in build_plan_raw:
            parts.append("Build plan: complete (Sprints 0–10a).")
        if "Hardening Sprint v1" in build_plan_raw:
            parts.append("Hardening Sprint v1 done (tests, HEARTBEAT, inspection-first boundary).")
        if "Execution Boundary" in build_plan_raw:
            parts.append("Execution Boundary v1: native vs OpenClaw path selection.")
        if "Model Routing" in build_plan_raw:
            parts.append("Model routing v1: task-type-based model selection.")

    # 2. Recent live validation findings (prioritized over older backlog when present)
    if LIVE_VALIDATION_SOURCE in str(sources_used) and live_validation_raw:
        signals.append("live_validation")
        live_validation_influenced = True
        parts.append("Live validation findings present (recent real-world testing results).")

    # 3. Active limitations and backlog
    if "docs/IMPROVEMENT_BACKLOG.md" in str(sources_used) and backlog_raw:
        signals.append("backlog")
        open_count = len(re.findall(r"\*\*status\*\* \| open|\| open \|", backlog_raw))
        if open_count > 0:
            parts.append(f"Improvement backlog: {open_count} open items.")
            high_medium = len(re.findall(r"severity \| (?:high|medium)", backlog_raw, re.I))
            backlog_influenced = high_medium > 0

    if capability_registry_used:
        signals.append("capability_registry")
        parts.append("Capability registry: native vs OpenClaw ownership (gog for Google Workspace).")

    if "docs/GERTY_OVERVIEW.md" in str(sources_used):
        signals.append("overview")
        parts.append("Architecture: router, policy, execution boundary, capability registry.")

    factual_summary = " ".join(parts) if parts else "Inspected project state."
    recommendation_basis = "backlog_and_architecture" if "backlog" in signals else "architecture_state"
    if live_validation_influenced:
        recommendation_basis = "live_validation_and_architecture"
    return factual_summary, signals, recommendation_basis, backlog_influenced, live_validation_influenced


def _inspection_keyword_score(text: str) -> int:
    """Score text by inspection keywords. Deterministic, inspectable."""
    lower = text.lower()
    return sum(score for word, score in INSPECTION_KEYWORDS.items() if word in lower)


def should_use_inspection_first_mode(message: str) -> tuple[bool, str]:
    """
    Detect if message requires inspection before advice (v3.1: health-check triggers, phrase bypass).

    Uses: (1) exact phrase match (checked first; bypasses min length for matched phrases),
    (2) planning suppressors, (3) cue + system context, (4) keyword scoring.
    Returns (triggered, reason). Reason includes detection_reason for observability.
    """
    if not message or not isinstance(message, str):
        return False, ""
    lower = message.lower().strip()

    # v3.1: Exact phrase match FIRST — bypasses min length for matched phrases (e.g. "audit the system")
    for phrase in INSPECTION_FIRST_PHRASES:
        if phrase in lower:
            return True, f"phrase:{phrase}"

    # Min length for non-phrase paths
    if len(lower) < INSPECTION_MIN_LENGTH:
        return False, ""

    # Suppress casual chat
    for casual in CASUAL_SUPPRESSORS:
        if lower == casual or lower.startswith(casual + " ") or lower.endswith(" " + casual):
            if _inspection_keyword_score(lower) < 4:
                return False, ""

    # Planning-only: grounded planning, not inspection-first (narrowed in v3)
    for phrase in PLANNING_SUPPRESSORS:
        if phrase in lower:
            return False, ""

    # Cue + system context (v1 path)
    has_cue = any(c in lower for c in INSPECTION_CUES)
    has_context = any(c in lower for c in SYSTEM_CONTEXT_CUES)
    if has_cue and has_context:
        return True, "cue_and_context"

    # v2: Keyword scoring for natural phrasing
    score = _inspection_keyword_score(lower)
    if score >= INSPECTION_SCORE_THRESHOLD and has_context:
        return True, f"score:{score}"
    return False, ""


def inspect_project_state() -> InspectionResult:
    """
    Inspect relevant docs and build factual state summary.

    Uses section-aware extraction. Includes capability registry summary.
    v3: Optional LIVE_VALIDATION_FINDINGS.md when present.
    """
    parts = []
    sources_used = []
    sources_considered = []
    extracted_headings = []
    total = 0
    separator = "\n\n---\n\n"

    # Core sources
    all_sources = list(INSPECTION_SOURCES)
    # v3: Add live validation if file exists (bounded, no runtime break)
    live_val_path = PROJECT_ROOT / LIVE_VALIDATION_SOURCE
    if live_val_path.exists():
        all_sources = list(INSPECTION_SOURCES) + [LIVE_VALIDATION_SOURCE]

    for rel_path in all_sources:
        if total >= INSPECTION_CONTEXT_MAX_CHARS:
            break
        path = PROJECT_ROOT / rel_path
        sources_considered.append(rel_path)
        raw = _read_file(path)
        if not raw:
            continue
        extractor = _EXTRACTORS.get(rel_path, _extract_from_doc)
        max_chars = _SOURCE_MAX_CHARS.get(rel_path, 400)
        excerpt = extractor(raw, max_chars)
        if not excerpt:
            continue
        remaining = INSPECTION_CONTEXT_MAX_CHARS - total - len(separator) - len(f"[Source: {rel_path}]\n")
        if len(excerpt) > remaining:
            excerpt = excerpt[:remaining] + "\n\n[... truncated ...]"
        header = f"[Source: {rel_path}]\n"
        block = header + excerpt
        parts.append(block)
        sources_used.append(rel_path)
        for h, _ in parse_markdown_sections(excerpt)[:5]:
            if h:
                extracted_headings.append((rel_path, h))
        total += len(block) + len(separator)

    # Add capability registry summary
    capability_block = ""
    capability_registry_used = False
    try:
        from gerty.capability_registry import summarize_capabilities
        cap_summary = summarize_capabilities()
        if cap_summary:
            capability_block = f"[Source: capability_registry]\n\n## Capability Registry (current)\n\n{cap_summary}"
            capability_registry_used = True
            remaining = INSPECTION_CONTEXT_MAX_CHARS - total - len(separator) - len(capability_block)
            if remaining > 100:
                parts.append(capability_block)
                sources_used.append("capability_registry")
                total += len(capability_block) + len(separator)
    except Exception as e:
        logger.debug("Inspection-first: capability registry unavailable: %s", e)

    context = separator.join(parts) if parts else ""
    # v3.1: Prepend IB reference card when backlog present (prevents IB-015/016 conflation)
    backlog_raw_for_card = _read_file(PROJECT_ROOT / "docs/IMPROVEMENT_BACKLOG.md")
    if backlog_raw_for_card:
        card = _build_ib_reference_card(backlog_raw_for_card)
        if card:
            remaining = INSPECTION_CONTEXT_MAX_CHARS - len(context) - len(separator) - len(card)
            if remaining > 50:
                context = f"[Source: IB Reference]\n\n{card}\n\n{separator}\n\n{context}"

    if len(context) > INSPECTION_CONTEXT_MAX_CHARS:
        context = context[:INSPECTION_CONTEXT_MAX_CHARS] + "\n\n[... truncated ...]"

    # v3: Build synthesized factual summary with prioritization
    build_plan_raw = _read_file(PROJECT_ROOT / "docs/BUILD_PLAN_PROGRESS.md") if "docs/BUILD_PLAN_PROGRESS.md" in sources_used else ""
    backlog_raw = _read_file(PROJECT_ROOT / "docs/IMPROVEMENT_BACKLOG.md") if "docs/IMPROVEMENT_BACKLOG.md" in sources_used else ""
    live_validation_raw = _read_file(PROJECT_ROOT / LIVE_VALIDATION_SOURCE) if LIVE_VALIDATION_SOURCE in sources_used else ""
    factual_summary, summary_signals, recommendation_basis, backlog_influenced, live_validation_influenced = _build_factual_summary_v3(
        sources_used=sources_used,
        capability_registry_used=capability_registry_used,
        build_plan_raw=build_plan_raw,
        backlog_raw=backlog_raw,
        live_validation_raw=live_validation_raw,
    )

    return InspectionResult(
        context=context,
        factual_summary=factual_summary,
        sources_used=sources_used,
        total_chars=len(context),
        triggered=True,
        trigger_reason="",
        sources_considered=sources_considered,
        extracted_headings=tuple(extracted_headings[:15]),
        capability_registry_used=capability_registry_used,
        summary_signals_used=tuple(summary_signals),
        recommendation_basis=recommendation_basis,
        backlog_signals_influenced=backlog_influenced,
        live_validation_signals_influenced=live_validation_influenced,
    )


def get_inspection_block_for_message(message: str) -> InspectionResult | None:
    """
    If message triggers inspection-first mode, inspect and return block.
    Otherwise return None.
    """
    triggered, reason = should_use_inspection_first_mode(message)
    if not triggered:
        return None
    result = inspect_project_state()
    return InspectionResult(
        context=result.context,
        factual_summary=result.factual_summary,
        sources_used=result.sources_used,
        total_chars=result.total_chars,
        triggered=True,
        trigger_reason=reason,
        sources_considered=result.sources_considered,
        extracted_headings=result.extracted_headings,
        capability_registry_used=result.capability_registry_used,
        summary_signals_used=getattr(result, "summary_signals_used", ()),
        recommendation_basis=getattr(result, "recommendation_basis", ""),
        backlog_signals_influenced=getattr(result, "backlog_signals_influenced", False),
        live_validation_signals_influenced=getattr(result, "live_validation_signals_influenced", False),
    )


def build_inspection_first_injection(result: InspectionResult) -> str:
    """
    Build the full injection block: instruction + context.

    Prepended to the user message when inspection-first mode is active.
    """
    if not result.context:
        return ""
    return (
        f"## Inspection-First Planning Context\n\n{INSPECTION_INSTRUCTION}\n\n"
        f"---\n\n{result.context}\n\n---\n\n"
    )
