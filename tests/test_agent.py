import tempfile
from pathlib import Path

from artic.agent import Artic
from artic.core import open_index
from artic.llm import Engine
from artic.vault import Vault


class BrokenJSONEngine(Engine):
    name = "broken"

    def complete(self, system, messages):
        if "Return ONLY JSON" in system:
            return '{"title": "Broken", "summary": }'
        return "Entropy always increases."


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
