"""The A.R.T.I.C. loop: recall -> think -> answer -> reflect -> remember -> link."""
from __future__ import annotations
import json
import re
from pathlib import Path

from .llm import Engine
from .vault import Vault
from .load_core import load_core
from .tools import Repo, ToolError

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

ACT = """You are extending your own codebase. Work one step at a time.

Reply with ONE tool call in this exact form when you need information or want to change a file:
```tool
{"tool": "read_file", "path": "artic/agent.py"}
```

Tools:
- read_file {"path": str}
- list_files {"dir": str}
- propose_write {"path": str, "content": str}  # shows a diff, asks the user, then runs tests
- run_tests {}

Rules: read a file before proposing changes to it. A write only counts when the tool result says it succeeded.
Never claim a change the tool rejected. When you are done, reply with a short summary and no tool block.

Repository files:
"""


def _json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _tool_call(text: str) -> dict | None:
    m = re.search(r"```tool\s*(\{.*?\})\s*```", text, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return {"tool": "_invalid"}
    return data if isinstance(data, dict) else {"tool": "_invalid"}


class Artic:
    def __init__(self, vault: Vault, engine: Engine, index, k: int = 5, tools: Repo | None = None):
        self.vault, self.engine, self.index, self.k = vault, engine, index, k
        self.tools = tools or Repo(Path(__file__).resolve().parents[1])
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

    def _tool_system(self, recalled: list[dict]) -> str:
        identity = "\n\n".join(load_core())
        base = (
            "You are A.R.T.I.C., a long-term cognitive partner working on your own source code.\n"
            "Your memory is an Obsidian vault; relevant notes are provided below.\n"
            "You live by these founding principles:\n\n" + identity
        )
        if recalled:
            mem = "\n\n".join(f"### [[{r['title']}]]\n{r['excerpt'][:500]}" for r in recalled)
            base += f"\n\nRECALLED MEMORIES:\n{mem}"
        files = "\n".join(f"- {p}" for p in self.tools.list_files())
        return f"{base}\n\n{ACT}{files}"

    @staticmethod
    def _confirm(change) -> bool:
        print("\n" + change.diff())
        try:
            return input("Apply this change? [y/N] ").strip().lower() in {"y", "yes"}
        except EOFError:
            return False

    def _run_tool(self, call: dict, approve) -> str:
        name = call.get("tool")
        if name == "_invalid":
            return "ERROR: invalid tool JSON. Reply with one JSON object in a ```tool block."
        try:
            if name == "read_file":
                return self.tools.read(str(call["path"]))
            if name == "list_files":
                return "\n".join(self.tools.list_files(str(call.get("dir", "."))))
            if name == "run_tests":
                r = self.tools.run_tests()
                return ("PASS\n" if r.ok else "FAIL\n") + r.output
            if name == "propose_write":
                change = self.tools.propose(str(call["path"]), str(call["content"]))
                return change.apply(approve)
        except ToolError as e:
            return f"ERROR: {e}"
        except KeyError as e:
            return f"ERROR: missing argument {e}"
        return f"ERROR: unknown tool {name}"

    def act(self, goal: str, approve=None, max_steps: int = 8) -> str:
        """Let the model read, test, and (with approval) change the codebase."""
        approve = approve or self._confirm
        recalled = self.recall(goal)
        system = self._tool_system(recalled)
        messages = [{"role": "user", "content": f"GOAL: {goal}"}]
        self.vault.journal(f"**Act goal:** {goal}")
        for _ in range(max_steps):
            reply = self.engine.complete(system, messages)
            messages.append({"role": "assistant", "content": reply})
            call = _tool_call(reply)
            if call is None:
                self.vault.journal(f"**Act answer:** {reply}")
                note = self.remember(goal, reply, recalled)
                return reply + f"\n\n[remembered as [[{note}]]]"
            label = call.get("tool", "?")
            result = self._run_tool(call, approve)
            self.vault.journal(f"**Tool:** {label}\n\n{result[:1200]}")
            messages.append({"role": "user", "content": f"TOOL RESULT ({label}):\n{result}"})
        self.vault.journal("**Act stopped:** step limit reached")
        return "Stopped: step limit reached without a final answer."
