"""Parse markdown tables from research responses and save as CSV."""

import csv
import re
from datetime import datetime
from pathlib import Path

from gerty.config import RESEARCH_OUTPUT_DIR


def _parse_markdown_table(text: str) -> list[list[str]]:
    """
    Extract markdown table rows from text. Returns list of rows (each row is list of cell strings).
    Handles format: | col1 | col2 |\\n|---|---|\\n| a | b |
    """
    # Find table blocks: lines that start with | and contain |
    lines = text.split("\n")
    rows: list[list[str]] = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            in_table = False
            continue
        # Split by | and strip cells, skip empty first/last from leading/trailing |
        cells = [c.strip() for c in stripped.split("|")[1:-1]]
        if not cells:
            continue
        # Skip separator row (|---|---|)
        if all(re.match(r"^[-:]+$", c) for c in cells):
            continue
        rows.append(cells)
        in_table = True

    return rows


def _parse_json_table(text: str) -> list[list[str]] | None:
    """Try to extract a JSON array of objects as table. Returns headers + rows or None."""
    import json

    # Look for ```json ... ``` block first
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            data = json.loads(m.group(1).strip())
            if isinstance(data, list) and data and isinstance(data[0], dict):
                headers = list(data[0].keys())
                rows = [headers]
                for row in data:
                    rows.append([str(row.get(h, "")) for h in headers])
                return rows
        except json.JSONDecodeError:
            pass

    # Look for raw JSON array in text
    m = re.search(r"\[\s*\{[\s\S]+\}\s*\]", text)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, list) and data and isinstance(data[0], dict):
                headers = list(data[0].keys())
                rows = [headers]
                for row in data:
                    rows.append([str(row.get(h, "")) for h in headers])
                return rows
        except json.JSONDecodeError:
            pass
    return None


def parse_and_save_tables(response: str, output_dir: Path | None = None) -> str | None:
    """
    Parse markdown tables or JSON from response, save as CSV to RESEARCH_OUTPUT_DIR.
    Returns path to saved file if any table was saved, else None.
    """
    output_dir = output_dir or RESEARCH_OUTPUT_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Try JSON first (structured output)
    json_rows = _parse_json_table(response)
    if json_rows:
        path = output_dir / f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(json_rows)
        return str(path)

    # Fall back to markdown table
    rows = _parse_markdown_table(response)
    if rows:
        path = output_dir / f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        return str(path)

    return None
