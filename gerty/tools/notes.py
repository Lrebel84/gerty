"""Quick notes tool: add, list, clear notes."""

from pathlib import Path

from gerty.config import DATA_DIR
from gerty.tools.base import Tool

NOTES_FILE = DATA_DIR / "notes.txt"


def _ensure_notes():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not NOTES_FILE.exists():
        NOTES_FILE.touch()


def _load_notes() -> list[str]:
    _ensure_notes()
    text = NOTES_FILE.read_text(encoding="utf-8", errors="replace")
    return [line.strip() for line in text.splitlines() if line.strip()]


def _append_note(note: str) -> None:
    _ensure_notes()
    with NOTES_FILE.open("a", encoding="utf-8") as f:
        f.write(note.strip() + "\n")


def _clear_notes() -> None:
    _ensure_notes()
    NOTES_FILE.write("")


class NotesTool(Tool):
    """Quick capture: add note, list notes, clear notes."""

    @property
    def name(self) -> str:
        return "notes"

    @property
    def description(self) -> str:
        return "Add, list, or clear quick notes"

    def execute(self, intent: str, message: str) -> str:
        lower = message.lower()

        # List notes
        if "list" in lower or "show" in lower or "what" in lower and "note" in lower:
            notes = _load_notes()
            if not notes:
                return "No notes yet. Say 'note: buy milk' to add one."
            lines = [f"• {n}" for n in notes[-20:]]  # Last 20
            return "Your notes:\n" + "\n".join(lines)

        # Clear notes
        if "clear" in lower or "delete" in lower or "remove" in lower:
            count = len(_load_notes())
            _clear_notes()
            return f"Cleared {count} note(s)."

        # Add note - look for "note:" or "note " prefix
        for prefix in ("note:", "note ", "add note", "remember"):
            if prefix in lower:
                idx = lower.find(prefix) + len(prefix)
                note = message[idx:].strip()
                if note:
                    _append_note(note)
                    return f"Noted: {note}"
                break

        # No prefix but might be "remember to X"
        if "remember" in lower:
            idx = lower.find("remember") + 8
            rest = message[idx:].strip()
            if rest and len(rest) > 2:
                _append_note(rest)
                return f"Noted: {rest}"

        return "Say 'note: your text' to add a note, or 'list notes' to see them."
