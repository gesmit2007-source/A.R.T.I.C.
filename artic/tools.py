"""Path-scoped tools that let A.R.T.I.C. read and change its own code."""
from __future__ import annotations

import difflib
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

MAX_READ = 20_000
MAX_DIFF = 4_000
DENY_PARTS = {".git", "__pycache__", ".pytest_cache", ".venv"}
DENY_PREFIXES = ("core/build", "core/build-win", "build", "build_tmp")


class ToolError(Exception):
    pass


@dataclass
class SuiteResult:
    ok: bool
    output: str


class Repo:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()

    def _resolve(self, path: str) -> Path:
        p = (self.root / path).resolve()
        try:
            rel = p.relative_to(self.root)
        except ValueError:
            raise ToolError(f"outside the repository: {path}") from None
        if self._blocked(rel):
            raise ToolError(f"blocked path: {path}")
        return p

    @staticmethod
    def _blocked(rel: Path) -> bool:
        if any(part in DENY_PARTS for part in rel.parts):
            return True
        s = rel.as_posix()
        if any(s == p or s.startswith(p + "/") for p in DENY_PREFIXES):
            return True
        return rel.name.startswith(".env")

    def read(self, path: str) -> str:
        p = self._resolve(path)
        if not p.is_file():
            raise ToolError(f"not a file: {path}")
        if p.stat().st_size > MAX_READ * 4:
            raise ToolError(f"too large: {path}")
        return p.read_text(encoding="utf-8", errors="replace")[:MAX_READ]

    def list_files(self, directory: str = ".") -> list[str]:
        base = self._resolve(directory)
        if not base.is_dir():
            raise ToolError(f"not a directory: {directory}")
        out = []
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(self.root)
            if self._blocked(rel):
                continue
            if p.suffix in {".py", ".md", ".toml", ".bat", ".cpp", ".txt"} or p.name == ".gitignore":
                out.append(rel.as_posix())
        return out[:200]

    def propose(self, path: str, content: str) -> "Change":
        p = self._resolve(path)
        old = p.read_text(encoding="utf-8") if p.exists() else None
        return Change(self, p, old, content)

    def run_tests(self) -> SuiteResult:
        cmd = os.environ.get("ARTIC_TEST_CMD")
        args = cmd.split() if cmd else _default_test_cmd()
        try:
            r = subprocess.run(args, cwd=self.root, capture_output=True, text=True, timeout=600)
        except (OSError, subprocess.TimeoutExpired) as e:
            return SuiteResult(False, str(e))
        out = f"{r.stdout}\n{r.stderr}".strip()
        return SuiteResult(r.returncode == 0, out[-2000:])


def _default_test_cmd() -> list[str]:
    uv = shutil.which("uv")
    if uv:
        return [uv, "run", "--no-project", "--with", "pytest", "python", "-m", "pytest", "-q"]
    return [sys.executable, "-m", "pytest", "-q"]


@dataclass
class Change:
    repo: Repo
    path: Path
    old: str | None
    new: str

    @property
    def rel(self) -> str:
        return self.path.relative_to(self.repo.root).as_posix()

    def diff(self) -> str:
        before = (self.old or "").splitlines(keepends=True)
        after = self.new.splitlines(keepends=True)
        d = "".join(difflib.unified_diff(before, after, f"a/{self.rel}", f"b/{self.rel}"))
        return d if len(d) <= MAX_DIFF else d[:MAX_DIFF] + "\n[truncated]"

    def apply(self, approve: Callable[["Change"], bool], run_tests: bool = True) -> str:
        """Write only after approval; roll back if the test suite fails."""
        if not approve(self):
            return "rejected by user; nothing written"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self.new, encoding="utf-8")
        if not run_tests:
            return f"wrote {self.rel}"
        result = self.repo.run_tests()
        if result.ok:
            return f"wrote {self.rel}; tests passed"
        if self.old is None:
            self.path.unlink(missing_ok=True)
        else:
            self.path.write_text(self.old, encoding="utf-8")
        return f"tests failed; rolled back {self.rel}\n{result.output}"
