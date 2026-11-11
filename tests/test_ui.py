from artic.core import open_index
from artic.llm import EchoEngine
from artic.ui import splash
from artic.vault import Vault


class ModelEngine(EchoEngine):
    name = "openai"
    model = "qwen3.5:4b"


def make_vault(tmp_path):
    v = Vault(tmp_path)
    v.init()
    v.write_note("Alpha", "alpha sees [[Beta]]")
    v.write_note("Beta", "beta stands alone")
    return v


def test_splash_reports_vault_engine_and_memory(tmp_path):
    v = make_vault(tmp_path)
    ix = open_index(str(tmp_path))
    ix.rebuild()

    out = splash(v, EchoEngine(), ix)

    assert "A . R . T . I . C ." in out
    assert str(tmp_path)[-20:] in out
    assert "echo" in out
    assert f"2 notes" in out
    assert f"({ix.backend})" in out
    assert "never forget" in out
    assert "\x1b[" not in out


def test_splash_shows_engine_model_when_present(tmp_path):
    v = make_vault(tmp_path)
    ix = open_index(str(tmp_path))
    ix.rebuild()

    out = splash(v, ModelEngine(), ix)

    assert "openai" in out
    assert "qwen3.5:4b" in out


def test_splash_uses_singular_counts(tmp_path):
    v = Vault(tmp_path)
    v.init()
    v.write_note("Only", "just one note")
    ix = open_index(str(tmp_path))
    ix.rebuild()

    out = splash(v, EchoEngine(), ix)

    assert "1 note " in out
    assert "1 notes" not in out


def test_splash_colors_only_when_requested(tmp_path):
    v = make_vault(tmp_path)
    ix = open_index(str(tmp_path))
    ix.rebuild()

    assert "\x1b[" in splash(v, EchoEngine(), ix, color=True)
    assert "\x1b[" not in splash(v, EchoEngine(), ix, color=False)


def test_splash_uses_ice_white_charcoal_and_pastel_blue(tmp_path):
    v = make_vault(tmp_path)
    ix = open_index(str(tmp_path))
    ix.rebuild()

    out = splash(v, EchoEngine(), ix, color=True)

    assert "\x1b[38;2;234;246;255m" in out
    assert "\x1b[48;2;35;35;35m" in out
    assert "\x1b[38;2;167;199;231m" in out


def test_splash_falls_back_to_ascii(tmp_path):
    v = make_vault(tmp_path)
    ix = open_index(str(tmp_path))
    ix.rebuild()

    out = splash(v, EchoEngine(), ix, unicode=False)

    assert out.isascii()
    assert "+---" in out
    assert "A . R . T . I . C ." in out


def test_splash_avoids_glyphs_the_console_cannot_encode(tmp_path, monkeypatch):
    class Cp1252Stdout:
        encoding = "cp1252"

        def isatty(self):
            return False

    monkeypatch.setattr("artic.ui.sys.stdout", Cp1252Stdout())
    v = make_vault(tmp_path)
    ix = open_index(str(tmp_path))
    ix.rebuild()

    out = splash(v, EchoEngine(), ix)

    assert out.isascii()


def test_splash_keeps_long_paths_inside_the_box(tmp_path):
    v = Vault(tmp_path / ("deeply_nested_" * 4))
    v.init()
    ix = open_index(str(v.root))
    ix.rebuild()

    out = splash(v, EchoEngine(), ix)

    assert "…" in out
    assert max(len(line) for line in out.splitlines()) <= 64
