"""Shared markdown section parsing for grounded planning and inspection-first.

Extracted from grounded_planning.py and inspection_first.py (M-002).
"""


def parse_markdown_sections(text: str) -> list[tuple[str, str]]:
    """Parse markdown into (heading, content) sections. Handles ## and ###."""
    sections = []
    current_heading = ""
    current_content = []
    for line in text.split("\n"):
        if line.startswith("## "):
            if current_heading or current_content:
                sections.append((current_heading, "\n".join(current_content).strip()))
            current_heading = line[3:].strip()
            current_content = []
        elif line.startswith("### "):
            if current_heading or current_content:
                sections.append((current_heading, "\n".join(current_content).strip()))
            current_heading = line[4:].strip()
            current_content = []
        else:
            current_content.append(line)
    if current_heading or current_content:
        sections.append((current_heading, "\n".join(current_content).strip()))
    return sections


def section_relevance_score(heading: str, content: str, keywords: tuple[str, ...]) -> int:
    """Score a section by relevance. Higher = more relevant."""
    combined = (heading + " " + content).lower()
    return sum(1 for kw in keywords if kw in combined)
