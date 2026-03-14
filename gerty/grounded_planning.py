"""Grounded Planning Mode v2 — relevance extraction and planning-state refinement.

For strategic/system-improvement requests, injects a bounded planning context
from relevant docs so the model answers from actual state instead of generic prompts.

v2: Improved detection (phrase + keyword scoring), section-aware relevance extraction,
planning state assembly (current state, bottlenecks, backlog, next upgrades).

See docs/GROUNDED_PLANNING_MODE.md.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import NamedTuple

from gerty.utils.markdown_sections import parse_markdown_sections, section_relevance_score

logger = logging.getLogger(__name__)

# Workspace root (parent of gerty package)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Exact phrases — immediate trigger (high confidence)
PLANNING_TRIGGER_PHRASES = (
    "create a plan to improve gerty",
    "what should we build next",
    "what is gerty missing right now",
    "review the current system and recommend",
    "what should we prioritise next",
    "what should we prioritize next",
    "design the next upgrade",
    "architecture advice",
    "system improvement",
    "improve the system",
    "next improvement",
    "what to build next",
    "prioritise next",
    "prioritize next",
)

# Keyword scoring: (word, score). Combinations can reach threshold.
PLANNING_KEYWORDS = {
    "plan": 2,
    "build": 2,
    "upgrade": 2,
    "improve": 2,
    "next": 2,
    "prioritise": 2,
    "prioritize": 2,
    "architecture": 2,
    "system": 2,
    "missing": 2,
    "recommend": 2,
    "design": 2,
    "bottleneck": 1,
    "limitation": 1,
    "weakness": 1,
}
PLANNING_SCORE_THRESHOLD = 3

# Casual phrases that suppress planning mode even if keywords match
CASUAL_SUPPRESSORS = (
    "hello", "hi", "hey", "what's up", "how are you", "good morning", "good evening",
    "thanks", "thank you", "ok", "okay", "yes", "no", "cool", "nice",
)

# Sources: (relative_path, extraction_strategy). Order matters.
PLANNING_SOURCES = [
    "docs/BUILD_PLAN_PROGRESS.md",
    "docs/IMPROVEMENT_BACKLOG.md",
    "docs/GERTY_OVERVIEW.md",
    "docs/GERTY_VISION.md",
]

# Relevance keywords for section scoring (section heading + content)
RELEVANCE_KEYWORDS = (
    "completed", "status", "done", "backlog", "limitation", "bottleneck",
    "next", "weakness", "open", "upgrade", "improvement", "phase",
    "development", "capability", "sprint", "progress",
)

# Total cap for planning context block
PLANNING_CONTEXT_MAX_CHARS = 3500

# Instruction block prepended when planning mode is active
PLANNING_INSTRUCTION = (
    "Use the Grounded Planning Context below. Identify the main bottleneck, "
    "recommend ONE prioritized improvement with rationale, then optionally list follow-ups. "
    "Avoid generic checklists."
)


class PlanningContextResult(NamedTuple):
    """Result of building grounded planning context."""

    context: str
    sources_used: list[str]
    total_chars: int
    triggered: bool
    trigger_reason: str
    sources_considered: list[str] = ()
    extracted_headings: list[tuple[str, str]] = ()


def _planning_keyword_score(text: str) -> int:
    """Score text by planning keywords. Returns sum of keyword scores."""
    lower = text.lower()
    return sum(score for word, score in PLANNING_KEYWORDS.items() if word in lower)


def should_use_grounded_planning_mode(message: str) -> tuple[bool, str]:
    """
    Detect if message is a strategic planning/architecture/improvement request.

    Uses: (1) exact phrase match, (2) keyword scoring. Protects casual chat.
    Returns (triggered, reason). Reason is empty when not triggered.
    """
    if not message or not isinstance(message, str):
        return False, ""
    lower = message.lower().strip()
    if len(lower) < 12:
        return False, ""
    # Suppress casual chat
    for casual in CASUAL_SUPPRESSORS:
        if lower == casual or lower.startswith(casual + " ") or lower.endswith(" " + casual):
            if _planning_keyword_score(lower) < 5:  # Allow "thanks, what should we build next"
                return False, ""
    # Exact phrase match
    for phrase in PLANNING_TRIGGER_PHRASES:
        if phrase in lower:
            return True, f"phrase:{phrase}"
    # Keyword scoring
    score = _planning_keyword_score(lower)
    if score >= PLANNING_SCORE_THRESHOLD:
        return True, f"score:{score}"
    return False, ""


def _section_relevance(heading: str, content: str) -> int:
    """Score a section by relevance to planning. Higher = more relevant."""
    return section_relevance_score(heading, content, RELEVANCE_KEYWORDS)


def _extract_from_build_plan(text: str, max_chars: int) -> str:
    """Extract planning-relevant content from BUILD_PLAN_PROGRESS.md."""
    sections = parse_markdown_sections(text)
    # Prioritize: Quick status, Completed work, How to pick up
    priority_headings = ("quick status", "completed work", "how to pick up", "completed work (summary)")
    parts = []
    for heading, content in sections:
        h_lower = heading.lower()
        if any(p in h_lower for p in priority_headings) or _section_relevance(heading, content) >= 2:
            if content:
                excerpt = content[:max_chars // 2] if len(content) > max_chars // 2 else content
                parts.append(f"### {heading}\n{excerpt}")
    return "\n\n".join(parts)[:max_chars] if parts else text[:max_chars]


def _extract_from_improvement_backlog(text: str, max_chars: int) -> str:
    """Extract open backlog items (limitations, bottlenecks) from IMPROVEMENT_BACKLOG.md."""
    sections = parse_markdown_sections(text)
    # Extract ### IB-XXX blocks where status is open
    open_items = []
    for heading, content in sections:
        if re.match(r"^IB-\d+$", heading.strip()):
            if "**status** | open" in content or "| open |" in content:
                # Extract title
                title_match = re.search(r"\*\*title\*\* \| ([^\n|]+)", content)
                title = title_match.group(1).strip() if title_match else heading
                open_items.append(f"- {title} ({heading})")
    if open_items:
        return "## Open Backlog Items (top signals)\n\n" + "\n".join(open_items[:12])[:max_chars]
    # Fallback: first part of file
    return text[:max_chars]


def _extract_from_overview(text: str, max_chars: int) -> str:
    """Extract planning-relevant content from GERTY_OVERVIEW.md."""
    sections = parse_markdown_sections(text)
    priority_headings = ("what is gerty", "key components", "request flow")
    parts = []
    for heading, content in sections:
        h_lower = heading.lower()
        if any(p in h_lower for p in priority_headings) or _section_relevance(heading, content) >= 1:
            if content:
                excerpt = content[:400] if len(content) > 400 else content
                parts.append(f"### {heading}\n{excerpt}")
    return "\n\n".join(parts)[:max_chars] if parts else text[:max_chars]


def _extract_from_vision(text: str, max_chars: int) -> str:
    """Extract planning-relevant content from GERTY_VISION.md."""
    sections = parse_markdown_sections(text)
    priority_headings = ("development phases", "project purpose", "summary", "core design principles")
    parts = []
    for heading, content in sections:
        h_lower = heading.lower()
        if any(p in h_lower for p in priority_headings):
            if content:
                excerpt = content[:500] if len(content) > 500 else content
                parts.append(f"### {heading}\n{excerpt}")
    return "\n\n".join(parts)[:max_chars] if parts else text[:max_chars]


_EXTRACTORS = {
    "docs/BUILD_PLAN_PROGRESS.md": _extract_from_build_plan,
    "docs/IMPROVEMENT_BACKLOG.md": _extract_from_improvement_backlog,
    "docs/GERTY_OVERVIEW.md": _extract_from_overview,
    "docs/GERTY_VISION.md": _extract_from_vision,
}

# Max chars per source in v2 (relevance extraction yields denser content)
_SOURCE_MAX_CHARS = {
    "docs/BUILD_PLAN_PROGRESS.md": 900,
    "docs/IMPROVEMENT_BACKLOG.md": 800,
    "docs/GERTY_OVERVIEW.md": 500,
    "docs/GERTY_VISION.md": 500,
}


def _read_file(path: Path) -> str:
    """Read file content. Returns empty string on error."""
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError as e:
        logger.debug("Grounded planning: could not read %s: %s", path, e)
        return ""


def build_grounded_planning_context() -> PlanningContextResult:
    """
    Build a bounded planning context from relevant project-state sources.

    v2: Uses section-aware relevance extraction instead of first-N-chars.
    Returns PlanningContextResult with context string, sources used, and metadata.
    """
    parts = []
    sources_used = []
    sources_considered = []
    extracted_headings = []
    total = 0
    separator = "\n\n---\n\n"

    for rel_path in PLANNING_SOURCES:
        if total >= PLANNING_CONTEXT_MAX_CHARS:
            break
        path = PROJECT_ROOT / rel_path
        sources_considered.append(rel_path)
        raw = _read_file(path)
        if not raw:
            continue
        extractor = _EXTRACTORS.get(rel_path)
        max_chars = _SOURCE_MAX_CHARS.get(rel_path, 600)
        if extractor:
            excerpt = extractor(raw, max_chars)
        else:
            excerpt = raw[:max_chars]
        if not excerpt:
            continue
        remaining = PLANNING_CONTEXT_MAX_CHARS - total - len(separator) - len(f"[Source: {rel_path}]\n")
        if len(excerpt) > remaining:
            excerpt = excerpt[:remaining] + "\n\n[... truncated ...]"
        header = f"[Source: {rel_path}]\n"
        block = header + excerpt
        parts.append(block)
        sources_used.append(rel_path)
        # Record key headings for observability
        for h, _ in parse_markdown_sections(excerpt)[:5]:
            if h:
                extracted_headings.append((rel_path, h))
        total += len(block) + len(separator)

    context = separator.join(parts) if parts else ""
    if len(context) > PLANNING_CONTEXT_MAX_CHARS:
        context = context[:PLANNING_CONTEXT_MAX_CHARS] + "\n\n[... truncated ...]"

    return PlanningContextResult(
        context=context,
        sources_used=sources_used,
        total_chars=len(context),
        triggered=True,
        trigger_reason="",
        sources_considered=sources_considered,
        extracted_headings=tuple(extracted_headings[:15]),
    )


def get_planning_block_for_message(message: str) -> PlanningContextResult | None:
    """
    If message triggers planning mode, build and return the planning block.
    Otherwise return None.
    """
    triggered, reason = should_use_grounded_planning_mode(message)
    if not triggered:
        return None
    result = build_grounded_planning_context()
    return PlanningContextResult(
        context=result.context,
        sources_used=result.sources_used,
        total_chars=result.total_chars,
        triggered=True,
        trigger_reason=reason,
        sources_considered=result.sources_considered,
        extracted_headings=result.extracted_headings,
    )


def build_planning_injection(result: PlanningContextResult) -> str:
    """
    Build the full injection block: instruction + context.

    This is prepended to the user message when planning mode is active.
    """
    if not result.context:
        return ""
    return (
        f"## Grounded Planning Context\n\n{PLANNING_INSTRUCTION}\n\n"
        f"---\n\n{result.context}\n\n---\n\n"
    )


# Backward compatibility: expose PLANNING_SOURCES as list of (path, max_chars) for tests
PLANNING_SOURCES_LEGACY = [(p, _SOURCE_MAX_CHARS.get(p, 600)) for p in PLANNING_SOURCES]
