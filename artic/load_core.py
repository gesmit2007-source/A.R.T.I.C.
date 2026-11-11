"""Founding-principle notes: markdown notes in the active vault tagged #core."""
from pathlib import Path


def load_core(root: str | Path) -> list[str]:
    notes_dir = Path(root).expanduser() / "Notes"
    if not notes_dir.is_dir():
        return []
    core_notes = []
    for path in notes_dir.glob("*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "#core" in text:
            core_notes.append(text)
    return core_notes


if __name__ == "__main__":
    import sys

    identity = "\n\n".join(load_core(sys.argv[1] if len(sys.argv) > 1 else "~/ArticVault"))
    print("IDENTITY BLOCK:", len(identity), "characters")
    print(identity)
