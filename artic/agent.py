"""The A.R.T.I.C. loop: recall -> think -> answer -> reflect -> remember -> link."""
from __future__ import annotations
import json
import re

from .llm import Engine
from .vault import Vault
from .load_core import load_core

LAWS = """You are A.R.T.I.C., a long-term cognitive partner.
LAW 1: You never forget. Your memory is an Obsidian vault; relevant notes are provided below.
LAW 2: Every thought leaves a permanent trace; what you learn will be written back to the vault.
LAW 3: Prefer connecting ideas across domains. Cite notes you rely on as [[Note Title]].
If recalled notes conflict with a user claim, say so. Never invent memories that are not provided."""

REFLECT = """You are the memory-writer of A.R.T.I.C. Distill what is durable from this exchange.
Return ONLY JSON: {"title": str (short, specific noun phrase), "summary": str (2-5 sentences of
durable knowledge, in third person), "tags": [1-4 lowercase single words], "links": [titles of
related notes or concepts; prefer titles from the recalled list]}"""

DREAM = """You are the dreaming process of A.R.T.I.C. Below are clusters of related notes.
Find non-obvious cross-domain connections, open questions, and contradictions.
Return ONLY JSON: {"title": str, "insight": str (markdown, cite notes as [[Title]]), "tags": [..], "links": [..]}"""


def _json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


class Artic:
    def __init__(self, vault: Vault, engine: Engine, index, k: int = 5):
        self.vault, self.engine, self.index, self.k = vault, engine, index, k
        self.history: list[dict] = []
        vault.init()
        index.rebuild()

    def recall(self, query: str) -> list[dict]:
        return self.index.search(query, self.k)

    def _system(self, recalled: list[dict]) -> str:
        identity = "\n\n".join(load_core())
        base = (
            "You are A.R.T.I.C., a long-term cognitive partner.\n"
            "Your memory is an Obsidian vault; relevant notes are provided below.\n"
            "Keep every reply under 200 words unless the user asks for depth.\n"
            "You live by these founding principles:\n\n" + identity
        )
        if not recalled:
            return base + "\n\n(No relevant memories yet.)"
        mem = "\n\n".join(f"### [[{r['title']}]]\n{r['excerpt'][:500]}" for r in recalled)
        return f"{base}\n\nRECALLED MEMORIES:\n{mem}"

    def chat(self, user_text: str) -> str:
        recalled = self.recall(user_text)
        self.history.append({"role": "user", "content": user_text})
        reply = self.engine.complete(self._system(recalled), self.history[-8:])
        self.history.append({"role": "assistant", "content": reply})
        note_title = self.remember(user_text, reply, recalled)
        return reply if not note_title else f"{reply}\n\n[remembered as [[{note_title}]]]"

    def remember(self, user_text: str, reply: str, recalled: list[dict]) -> str | None:
        titles = [r["title"] for r in recalled]
        raw = self.engine.complete(
            REFLECT + f"\nRecalled titles: {titles}",
            [{"role": "user", "content": f"USER: {user_text}\n\nA.R.T.I.C.: {reply}"}])
        data = _json(raw) or {"title": user_text[:50], "summary": f"Q: {user_text}\nA: {reply[:500]}",
                              "tags": ["unsorted"], "links": []}
        title = data.get("title") or user_text[:50]
        tags = [t for t in data.get("tags", []) if isinstance(t, str)] or ["unsorted"]
        links = [l for l in data.get("links", []) if isinstance(l, str)]
        self.vault.write_note(title, data.get("summary", ""), tags, links)
        for t in tags:
            self.vault.hub(t, title)
        self.vault.journal(f"**You:** {user_text}\n\n**A.R.T.I.C.:** {reply}\n\nDistilled into [[{title}]]")
        self.index.rebuild()
        return title

    def dream(self, n: int = 5) -> str | None:
        """Consolidation: link recent notes with their neighbours and write a synthesis."""
        recent = self.vault.recent_notes(n)
        if not recent:
            return None
        clusters = []
        for p in recent:
            hits = [h for h in self.index.search(p.stem, 4) if h["title"] != p.stem]
            clusters.append({"note": p.stem, "excerpt": p.read_text(encoding="utf-8")[:500],
                             "neighbours": [h["title"] for h in hits]})
        raw = self.engine.complete(DREAM, [{"role": "user", "content": json.dumps(clusters)}])
        data = _json(raw)
        if not data:
            return None
        n_ = self.vault.now()
        title = f"Dream {n_:%Y-%m-%d %H%M} - {data.get('title', 'Synthesis')}"
        links = [p.stem for p in recent] + [l for l in data.get("links", []) if isinstance(l, str)]
        self.vault.write_note(title, data.get("insight", ""), data.get("tags", ["dream"]), links, "Reflections")
        self.index.rebuild()
        return title
