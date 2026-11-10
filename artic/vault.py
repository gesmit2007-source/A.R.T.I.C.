"""Obsidian vault access. LAW: append-only. Nothing is ever deleted or overwritten."""
from __future__ import annotations
import datetime as dt
import re
from pathlib import Path

_BAD = re.compile(r'[\\/:*?"<>|#^\[\]]')


def slug(title: str) -> str:
    return _BAD.sub("", title).strip()[:80] or "Untitled"


class Vault:
    FOLDERS = ("Journal", "Notes", "Hubs", "Reflections")

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()

    @staticmethod
    def now() -> dt.datetime:
        return dt.datetime.now()

    def init(self) -> None:
        for f in self.FOLDERS:
            (self.root / f).mkdir(parents=True, exist_ok=True)
        home = self.root / "Home.md"
        if not home.exists():
            home.write_text(
                "# A.R.T.I.C. Home\n\n"
                "The Law: **never forget, every thought leaves a trace.**\n\n"
                "- Journals live in `Journal/`, distilled knowledge in `Notes/`.\n"
                "- Topic hubs live in `Hubs/`, cross-domain syntheses in `Reflections/`.\n",
                encoding="utf-8",
            )

    def _append(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)

    def journal(self, text: str) -> Path:
        n = self.now()
        p = self.root / "Journal" / f"{n:%Y-%m-%d}.md"
        if not p.exists():
            self._append(p, f"# Journal {n:%Y-%m-%d}\n")
        self._append(p, f"\n## {n:%H:%M}\n{text.rstrip()}\n")
        return p

    def write_note(self, title: str, body: str, tags=(), links=(), folder="Notes") -> Path:
        """Create a note; if it exists, APPEND an addendum instead of overwriting."""
        n = self.now()
        p = self.root / folder / f"{slug(title)}.md"
        link_line = " ".join(f"[[{l}]]" for l in dict.fromkeys(links))
        tag_line = " ".join(f"#{t.lstrip('#')}" for t in dict.fromkeys(tags))
        if p.exists():
            self._append(p, f"\n\n## Addendum {n:%Y-%m-%d %H:%M}\n{body.strip()}\n")
            if link_line:
                self._append(p, f"\nRelated: {link_line}\n")
            if tag_line:
                self._append(p, f"\n{tag_line}\n")
        else:
            fm = f"---\ncreated: {n:%Y-%m-%d %H:%M}\nsource: artic\n---\n"
            out = f"{fm}# {title}\n\n{body.strip()}\n"
            if link_line:
                out += f"\nRelated: {link_line}\n"
            if tag_line:
                out += f"\n{tag_line}\n"
            self._append(p, out)
        return p

    def hub(self, tag: str, note_title: str) -> Path:
        name = slug(tag).title()
        p = self.root / "Hubs" / f"{name}.md"
        entry = f"- [[{note_title}]]"
        if not p.exists():
            self._append(p, f"# {name}\n\nTopic hub. Every note tagged #{tag} is listed here.\n\n")
        if entry not in p.read_text(encoding="utf-8"):
            self._append(p, entry + "\n")
        return p

    def recent_notes(self, n: int = 5) -> list[Path]:
        files = sorted((self.root / "Notes").glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        return files[:n]
