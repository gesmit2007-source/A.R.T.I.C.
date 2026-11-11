"""Bridge to the C++ index (ctypes). Falls back to a slow pure-Python index if not built."""
from __future__ import annotations
import ctypes
import json
import os
import re
import sys
from pathlib import Path

NOTE_FOLDERS = ("Notes", "Reflections")


def _in_note_folder(root: Path, path: str) -> bool:
    try:
        return Path(path).resolve().relative_to(root).parts[0] in NOTE_FOLDERS
    except (ValueError, IndexError):
        return False


def _lib_path() -> Path | None:
    env = os.environ.get("ARTIC_CORE_LIB")
    if env and Path(env).exists():
        return Path(env)
    ext = {"darwin": "dylib", "win32": "dll"}.get(sys.platform, "so")
    base = Path(__file__).resolve().parent.parent / "core" / "build"
    for n in (f"libartic_core.{ext}", f"artic_core.{ext}"):
        if (base / n).exists():
            return base / n
    return None


class NativeIndex:
    def __init__(self, root: str, lib: Path):
        L = ctypes.CDLL(str(lib))
        self.root = Path(root).resolve()
        L.artic_index_new.restype = ctypes.c_void_p
        L.artic_index_new.argtypes = [ctypes.c_char_p]
        L.artic_index_free.argtypes = [ctypes.c_void_p]
        L.artic_index_rebuild.argtypes = [ctypes.c_void_p]
        L.artic_index_rebuild.restype = ctypes.c_int
        L.artic_search.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        L.artic_search.restype = ctypes.c_void_p
        L.artic_backlinks.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        L.artic_backlinks.restype = ctypes.c_void_p
        L.artic_stats.argtypes = [ctypes.c_void_p]
        L.artic_stats.restype = ctypes.c_void_p
        L.artic_free.argtypes = [ctypes.c_void_p]
        self.L, self.h = L, L.artic_index_new(root.encode())
        self.backend = "c++"

    def _s(self, ptr) -> str:
        s = ctypes.string_at(ptr).decode("utf-8", "replace")
        self.L.artic_free(ptr)
        return s

    def rebuild(self) -> int:
        return self.L.artic_index_rebuild(self.h)

    def add(self, path: str) -> int:
        if not _in_note_folder(self.root, path):
            return self.stats()["notes"]
        fn = getattr(self.L, "artic_index_add", None)
        if fn is None:
            return self.rebuild()
        fn.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        fn.restype = ctypes.c_int
        return fn(self.h, str(path).encode())

    def search(self, q: str, k: int = 5) -> list[dict]:
        hits = json.loads(self._s(self.L.artic_search(self.h, q.encode(), k * 4)))
        return [h for h in hits if _in_note_folder(self.root, h.get("path", ""))][:k]

    def backlinks(self, title: str) -> list[str]:
        return json.loads(self._s(self.L.artic_backlinks(self.h, title.encode())))

    def stats(self) -> dict:
        return json.loads(self._s(self.L.artic_stats(self.h)))

    def __del__(self):
        try:
            self.L.artic_index_free(self.h)
        except Exception:
            pass


class PyIndex:
    """Fallback with the same API (token overlap instead of BM25)."""
    backend = "python-fallback"

    def __init__(self, root: str):
        self.root, self.docs = Path(root), []

    @staticmethod
    def _tok(s):
        return set(re.findall(r"\w{2,}", s.lower()))

    @staticmethod
    def _load(path: Path) -> dict:
        t = path.read_text(encoding="utf-8", errors="replace")
        links = [l.split("|")[0].split("#")[0] for l in re.findall(r"\[\[([^\]]+)\]\]", t)]
        return dict(title=path.stem, path=str(path), text=t, links=links,
                    toks=PyIndex._tok(t) | PyIndex._tok(path.stem))

    def rebuild(self) -> int:
        self.docs = []
        for folder in NOTE_FOLDERS:
            base = self.root / folder
            if not base.exists():
                continue
            for p in base.rglob("*.md"):
                self.docs.append(self._load(p))
        return len(self.docs)

    def add(self, path: str) -> int:
        p = Path(path)
        if not _in_note_folder(self.root, str(p)):
            return len(self.docs)
        doc = self._load(p)
        for i, d in enumerate(self.docs):
            if Path(d["path"]) == p:
                self.docs[i] = doc
                break
        else:
            self.docs.append(doc)
        return len(self.docs)

    def search(self, q, k=5):
        qt = self._tok(q)
        sc = [(len(qt & d["toks"]) / (1 + len(d["toks"])) ** 0.5, d) for d in self.docs]
        sc = [x for x in sc if x[0] > 0]
        sc.sort(key=lambda x: -x[0])
        return [dict(title=d["title"], path=d["path"], score=s, excerpt=d["text"][:700]) for s, d in sc[:k]]

    def backlinks(self, title):
        return [d["title"] for d in self.docs if title.lower() in (l.lower() for l in d["links"])]

    def stats(self):
        linked = {l.lower() for d in self.docs for l in d["links"]}
        orph = sum(1 for d in self.docs if not d["links"] and d["title"].lower() not in linked)
        return dict(notes=len(self.docs), links=sum(len(d["links"]) for d in self.docs), orphans=orph)


def open_index(root: str):
    lib = _lib_path()
    if lib:
        try:
            return NativeIndex(root, lib)
        except OSError:
            pass
    return PyIndex(root)
