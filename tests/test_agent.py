import tempfile
from pathlib import Path

from artic.agent import Artic
from artic.core import open_index
from artic.llm import Engine
from artic.tools import Repo
from artic.vault import Vault


class BrokenJSONEngine(Engine):
    name = "broken"

    def complete(self, system, messages):
        if "Return ONLY JSON" in system:
            return '{"title": "Broken", "summary": }'
        return "Entropy always increases."


class ToolEngine(Engine):
    name = "tool"

    def __init__(self):
        self.step = 0

    def complete(self, system, messages):
        if "Return ONLY JSON" in system:
            return '{"title": "Act Result", "summary": "Read the module.", "tags": ["act"], "links": []}'
        self.step += 1
        if self.step == 1:
            return '```tool\n{"tool": "read_file", "path": "pkg/mod.py"}\n```'
        assert "x = 1" in messages[-1]["content"]
        return "The module sets x to 1."


def test_malformed_reflection_json_still_saves_note():
    with tempfile.TemporaryDirectory() as d:
        v = Vault(d)
        v.init()
        ix = open_index(d)
        a = Artic(v, BrokenJSONEngine(), ix)

        out = a.chat("Tell me about entropy")

        assert "Entropy always increases." in out
        assert "[[Tell me about entropy]]" in out
        note = Path(d) / "Notes" / "Tell me about entropy.md"
        assert note.exists()
        text = note.read_text(encoding="utf-8")
        assert "Q: Tell me about entropy" in text
        assert "#unsorted" in text
        assert (Path(d) / "Hubs" / "Unsorted.md").exists()
        assert any(
            "Entropy always increases." in p.read_text(encoding="utf-8")
            for p in (Path(d) / "Journal").glob("*.md")
        )
        assert ix.search("entropy", 5)[0]["title"] == "Tell me about entropy"


def test_act_reads_repo_and_journals():
    with tempfile.TemporaryDirectory() as d:
        v = Vault(d)
        v.init()
        pkg = Path(d) / "pkg"
        pkg.mkdir()
        (pkg / "mod.py").write_text("x = 1\n", encoding="utf-8")
        ix = open_index(d)
        a = Artic(v, ToolEngine(), ix, tools=Repo(d))

        out = a.act("read the module", approve=lambda c: True, max_steps=3)

        assert "The module sets x to 1." in out
        assert "[[Act Result]]" in out
        journal = "\n".join(p.read_text(encoding="utf-8") for p in (Path(d) / "Journal").glob("*.md"))
        assert "**Tool:** read_file" in journal
        assert "x = 1" in journal
