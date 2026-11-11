import tempfile
from pathlib import Path

import artic.agent
from artic.agent import Artic
from artic.core import open_index
from artic.llm import EchoEngine, Engine
from artic.vault import Vault


class BrokenJSONEngine(Engine):
    name = "broken"

    def complete(self, system, messages):
        if "Return ONLY JSON" in system:
            return '{"title": "Broken", "summary": }'
        return "Entropy always increases."


def test_identity_comes_from_the_active_vault():
    with tempfile.TemporaryDirectory() as d:
        v = Vault(d)
        v.init()
        (Path(d) / "Notes" / "Principles.md").write_text(
            "# Principles #core\nNever forget the vault.", encoding="utf-8")
        (Path(d) / "Notes" / "Other.md").write_text(
            "# Other\nthis is not a core note", encoding="utf-8")
        a = Artic(v, EchoEngine(), open_index(d))

        system = a._system([])

        assert "Never forget the vault." in system
        assert "this is not a core note" not in system


def test_identity_is_read_once_per_session(monkeypatch):
    calls = []
    real = artic.agent.load_core

    def counting(*args):
        calls.append(args)
        return real(*args)

    monkeypatch.setattr(artic.agent, "load_core", counting)
    with tempfile.TemporaryDirectory() as d:
        v = Vault(d)
        v.init()
        a = Artic(v, EchoEngine(), open_index(d))

        a._system([])
        a._system([])

        assert len(calls) == 1


def test_chat_indexes_new_note_without_full_rebuild():
    with tempfile.TemporaryDirectory() as d:
        v = Vault(d)
        v.init()
        ix = open_index(d)
        a = Artic(v, BrokenJSONEngine(), ix)

        def boom():
            raise AssertionError("chat triggered a full index rebuild")

        ix.rebuild = boom

        out = a.chat("Tell me about tectonic plates")

        assert "[[Tell me about tectonic plates]]" in out
        assert "Tell me about tectonic plates" in {
            h["title"] for h in ix.search("tectonic plates", 5)}


def test_dream_indexes_synthesis_without_full_rebuild():
    with tempfile.TemporaryDirectory() as d:
        v = Vault(d)
        v.init()
        v.write_note("Entropy", "entropy always grows in closed systems")
        ix = open_index(d)
        a = Artic(v, EchoEngine(), ix)

        def boom():
            raise AssertionError("dream triggered a full index rebuild")

        ix.rebuild = boom

        title = a.dream()

        assert title is not None
        assert title in {h["title"] for h in ix.search("synthesis", 5)}


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
