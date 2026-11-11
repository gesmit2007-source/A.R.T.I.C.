import tempfile
from pathlib import Path

import pytest

from artic.core import PyIndex, open_index
from artic.vault import Vault


@pytest.mark.parametrize("index_factory", [open_index, PyIndex], ids=["auto", "python"])
def test_index_includes_only_notes_and_reflections(index_factory):
    with tempfile.TemporaryDirectory() as d:
        v = Vault(d)
        v.init()
        v.write_note("Real Note", "durable knowledge about widgets")
        v.write_note("Synthesis", "a cross-domain insight", folder="Reflections")
        v.hub("widget", "Real Note")
        v.journal("raw exchange about widgets")

        ix = index_factory(d)
        ix.rebuild()

        assert ix.stats()["notes"] == 2
        assert "Home" not in {h["title"] for h in ix.search("distilled knowledge", 10)}
        assert "Widget" not in {h["title"] for h in ix.search("topic hub tagged", 10)}
        hits = ix.search("widgets", 10)
        assert "Real Note" in {h["title"] for h in hits}
        root = Path(d).resolve()
        assert all(
            Path(h["path"]).resolve().relative_to(root).parts[0] in ("Notes", "Reflections")
            for h in hits
        )


@pytest.mark.parametrize("index_factory", [open_index, PyIndex], ids=["auto", "python"])
def test_add_indexes_new_and_appended_notes(index_factory):
    with tempfile.TemporaryDirectory() as d:
        v = Vault(d)
        v.init()
        v.write_note("Alpha", "alpha knowledge about widgets")
        ix = index_factory(d)
        ix.rebuild()
        assert ix.stats()["notes"] == 1

        beta = v.write_note("Beta", "beta knowledge about cryptography")
        ix.add(str(beta))
        assert ix.stats()["notes"] == 2
        assert "Beta" in {h["title"] for h in ix.search("cryptography", 5)}

        v.write_note("Beta", "addendum about entanglement")
        ix.add(str(beta))
        assert ix.stats()["notes"] == 2
        assert "Beta" in {h["title"] for h in ix.search("entanglement", 5)}

        fresh = index_factory(d)
        fresh.rebuild()
        assert ix.stats() == fresh.stats()
        assert ix.search("entanglement", 5)[0]["title"] == fresh.search("entanglement", 5)[0]["title"]
