"""Startup splash for the A.R.T.I.C. chat prompt. No third-party dependencies."""
from __future__ import annotations
import os
import sys
from pathlib import Path

_INNER = 46
_ICE_WHITE = "38;2;234;246;255"
_CHARCOAL = "48;2;35;35;35"
_PASTEL_BLUE = "38;2;167;199;231"
_RESET = "\x1b[0m"
_GLYPHS = {
    True: {"tl": "╭", "tr": "╮", "bl": "╰", "br": "╯", "h": "─", "v": "│", "sep": " · ", "dots": "…"},
    False: {"tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|", "sep": " - ", "dots": "..."},
}


def _use_color(color: bool | None) -> bool:
    if color is not None:
        return color
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _unicode_ok() -> bool:
    enc = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        "╭╮╰╯─│·…".encode(enc)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


def _style(text: str, fg: str | None, bg: str | None, enabled: bool) -> str:
    if not enabled:
        return text
    prefix = (f"\x1b[{fg}m" if fg else "") + (f"\x1b[{bg}m" if bg else "")
    return prefix + text + _RESET


def _fit(value: str, limit: int, dots: str) -> str:
    if len(value) <= limit:
        return value
    return dots + value[-(limit - len(dots)):]


def _short_path(root: Path, limit: int, dots: str) -> str:
    s = str(root)
    home = str(Path.home())
    if s != home and s.startswith(home + os.sep):
        s = "~" + s[len(home):]
    return _fit(s, limit, dots)


def _count(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _row(label: str, value: str, color: bool) -> str:
    return (f"   {_style(f'{label:<9}', _PASTEL_BLUE, None, color)}"
            f"{_style(value, _ICE_WHITE, None, color)}")


def splash(vault, engine, index, color: bool | None = None,
           unicode: bool | None = None) -> str:
    use_color = _use_color(color)
    use_unicode = _unicode_ok() if unicode is None else unicode
    g = _GLYPHS[use_unicode]
    top = _style(f"  {g['tl']}{g['h'] * _INNER}{g['tr']}", _ICE_WHITE, _CHARCOAL, use_color)
    bottom = _style(f"  {g['bl']}{g['h'] * _INNER}{g['br']}", _ICE_WHITE, _CHARCOAL, use_color)
    title = _style(f"  {g['v']}  {'A . R . T . I . C .':<{_INNER - 2}}{g['v']}",
                   _ICE_WHITE, _CHARCOAL, use_color)
    tagline = _style(f"  {g['v']}  {'it never forgets':<{_INNER - 2}}{g['v']}",
                     _ICE_WHITE, _CHARCOAL, use_color)
    stats = index.stats()
    model = getattr(engine, "model", None)
    sep = g["sep"]
    rows = [
        _row("vault", _short_path(vault.root, 52, g["dots"]), use_color),
        _row("engine", engine.name + (f"{sep}{model}" if model else ""), use_color),
        _row("memory", f"{_count(stats['notes'], 'note')}{sep}{_count(stats['links'], 'link')}"
                       f"{sep}{_count(stats['orphans'], 'orphan')} ({index.backend})", use_color),
        _row("laws", sep.join(("never forget", "leave a trace", "compound")), use_color),
    ]
    return "\n".join([top, title, tagline, bottom, *rows])
