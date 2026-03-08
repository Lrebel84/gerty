"""Tests for research module: table parsing and CSV output."""

import tempfile
from pathlib import Path

import pytest

from gerty.research.output import parse_and_save_tables


class TestParseMarkdownTable:
    def test_markdown_table(self):
        text = """
Here are the results:

| Name | Price | Rating |
|------|-------|--------|
| A    | $100  | 4.5    |
| B    | $200  | 4.8    |

Hope this helps!
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = parse_and_save_tables(text, output_dir=Path(tmp))
            assert path is not None
            content = Path(path).read_text()
            assert "Name" in content
            assert "Price" in content
            assert "A" in content
            assert "100" in content

    def test_json_table(self):
        text = """
```json
[
  {"name": "A", "price": 100},
  {"name": "B", "price": 200}
]
```
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = parse_and_save_tables(text, output_dir=Path(tmp))
            assert path is not None
            content = Path(path).read_text()
            assert "name" in content
            assert "price" in content
            assert "A" in content

    def test_no_table_returns_none(self):
        text = "Just some plain text with no table."
        with tempfile.TemporaryDirectory() as tmp:
            path = parse_and_save_tables(text, output_dir=Path(tmp))
            assert path is None
