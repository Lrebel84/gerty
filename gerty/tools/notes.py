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


def get_notes() -> list[str]:
    """Return list of notes for API."""
    return _load_notes()


def add_note(text: str) -> bool:
    """Add a note. Returns True if added."""
    t = text.strip()
    if not t:
        return False
    _append_note(t)
    return True


def clear_notes() -> int:
    """Clear all notes. Returns count removed."""
    notes = _load_notes()
    _clear_notes()
    return len(notes)


def delete_note(index: int) -> bool:
    """Remove note at 0-based index. Returns True if deleted."""
    notes = _load_notes()
    if index < 0 or index >= len(notes):
        return False
    notes.pop(index)
    _ensure_notes()
    NOTES_FILE.write_text("\n".join(notes) + ("\n" if notes else ""), encoding="utf-8")
    return True


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
            notes = get_notes()
            if not notes:
                return "No notes yet. Say 'note: buy milk' to add one."
            lines = [f"• {n}" for n in notes[-20:]]  # Last 20
            return "Your notes:\n" + "\n".join(lines)

        # Clear notes
        if "clear" in lower or "delete" in lower or "remove" in lower:
            count = len(get_notes())
            _clear_notes()
            return f"Cleared {count} note(s)."

        # Add note - extract from various phrasings
        note = _extract_note_from_message(message, lower)
        if note:
            _append_note(note)
            return f"Noted: {note}"

        return "Say 'note: your text', 'remind me to X', or 'remember to X' to add a note."


def _extract_note_from_message(message: str, lower: str) -> str | None:
    """Extract note text from natural phrasings. Returns None if no note found."""
    # "remind me to call mom" -> "call mom"
    if "remind me to" in lower:
        idx = lower.find("remind me to") + len("remind me to")
        rest = message[idx:].strip()
        if rest and len(rest) > 1:
            return rest
    # "remind me call mom" (STT may drop "to")
    if "remind me" in lower:
        idx = lower.find("remind me") + len("remind me")
        rest = message[idx:].strip().lstrip("to").strip()
        if rest and len(rest) > 1:
            return rest

    # "remember to call mom" -> "call mom"
    if "remember to" in lower:
        idx = lower.find("remember to") + len("remember to")
        rest = message[idx:].strip()
        if rest and len(rest) > 1:
            return rest
    # "remember call mom" or "remember X"
    if "remember" in lower:
        idx = lower.find("remember") + len("remember")
        rest = message[idx:].strip().lstrip("to").strip()
        if rest and len(rest) > 2:
            return rest

    # "make a note buy milk" / "make a note: buy milk" / "make note to X"
    for prefix in ("make a note:", "make a note ", "make note:", "make note "):
        if prefix in lower:
            idx = lower.find(prefix) + len(prefix)
            rest = message[idx:].strip().lstrip("to").strip()
            if rest and len(rest) > 1:
                return rest

    # "note: buy milk" / "note buy milk" / "add note X"
    for prefix in ("note:", "note ", "add note "):
        if prefix in lower:
            idx = lower.find(prefix) + len(prefix)
            rest = message[idx:].strip()
            if rest and len(rest) > 1:
                return rest

    return None
