import tempfile
from artic.agent import Artic
from artic.core import open_index
from artic.llm import EchoEngine
from artic.vault import Vault


def test_never_forgets_and_never_overwrites():
    with tempfile.TemporaryDirectory() as d:
        v = Vault(d); v.init()
        ix = open_index(d)
        a = Artic(v, EchoEngine(), ix)
        a.chat("Quantum entanglement relates to cryptography protocols")
        a.chat("Cryptography protocols need entanglement verification")
        assert ix.stats()["notes"] >= 2
        hits = ix.search("cryptography entanglement", 3)
        assert hits, "memory recall failed"
        p = v.write_note("Same Title", "first"); v.write_note("Same Title", "second")
        t = p.read_text()
        assert "first" in t and "second" in t, "append-only law violated"
        assert a.dream() is not None
