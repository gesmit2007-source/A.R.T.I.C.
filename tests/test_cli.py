import subprocess
import sys
from pathlib import Path

import artic.__main__ as cli
from artic.__main__ import main
from artic.vault import Vault

ROOT = Path(__file__).resolve().parents[1]


def run_cli(capsys, monkeypatch, vault, *argv):
    monkeypatch.setattr(sys, "argv", ["artic", *argv, "--vault", str(vault)])
    assert main() is None
    return capsys.readouterr().out


def feed(monkeypatch, lines):
    it = iter(lines)

    def fake_input(prompt=""):
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    monkeypatch.setattr("builtins.input", fake_input)


def test_init_creates_vault(capsys, monkeypatch, tmp_path):
    out = run_cli(capsys, monkeypatch, tmp_path, "init")

    assert "Vault ready" in out
    assert "backend:" in out
    for folder in Vault.FOLDERS:
        assert (tmp_path / folder).is_dir()
    assert (tmp_path / "Home.md").exists()


def test_init_does_not_build_the_index(capsys, monkeypatch, tmp_path):
    calls = []
    real_open_index = cli.open_index

    class CountingIndex:
        def __init__(self, inner):
            self._inner = inner
            self.backend = inner.backend

        def rebuild(self):
            calls.append(True)
            return self._inner.rebuild()

        def __getattr__(self, name):
            return getattr(self._inner, name)

    monkeypatch.setattr(cli, "open_index",
                        lambda root: CountingIndex(real_open_index(root)))

    out = run_cli(capsys, monkeypatch, tmp_path, "init")

    assert "Vault ready" in out
    assert "backend:" in out
    assert calls == []


def test_stats_counts_only_notes(capsys, monkeypatch, tmp_path):
    v = Vault(tmp_path)
    v.init()
    v.write_note("Entropy", "entropy grows")

    out = run_cli(capsys, monkeypatch, tmp_path, "stats")

    assert "'notes': 1" in out
    assert "backend:" in out


def test_search_prints_hits(capsys, monkeypatch, tmp_path):
    v = Vault(tmp_path)
    v.init()
    v.write_note("Entropy", "entropy always grows")

    out = run_cli(capsys, monkeypatch, tmp_path, "search", "entropy")

    assert "[[Entropy]]" in out


def test_chat_remembers_and_exits_on_eof(capsys, monkeypatch, tmp_path):
    feed(monkeypatch, ["hello there"])

    out = run_cli(capsys, monkeypatch, tmp_path, "chat", "--engine", "echo")

    assert "engine=echo" in out
    assert "(echo engine) I heard: hello there" in out
    assert "[remembered as [[" in out
    assert "Everything is saved. Nothing is forgotten." in out
    assert list((tmp_path / "Notes").glob("*.md"))
    assert list((tmp_path / "Journal").glob("*.md"))


def test_dream_writes_reflection(capsys, monkeypatch, tmp_path):
    v = Vault(tmp_path)
    v.init()
    v.write_note("Entropy", "entropy always grows")

    out = run_cli(capsys, monkeypatch, tmp_path, "dream", "--engine", "echo")

    assert out.startswith("Wrote:")
    assert "Synthesis" in out
    assert len(list((tmp_path / "Reflections").glob("*.md"))) == 1


def test_module_entrypoint(tmp_path):
    def run(*args):
        return subprocess.run(
            [sys.executable, "-m", "artic", *args, "--vault", str(tmp_path)],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
        )

    init = run("init")
    assert init.returncode == 0
    assert "Vault ready" in init.stdout

    stats = run("stats")
    assert stats.returncode == 0
    assert "backend:" in stats.stdout
