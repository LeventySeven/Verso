# verso/scaffolds.py
"""The version-tagged scaffolding ratchet (PRD §439).

Scaffolding is the code the harness carries to compensate for a *current* model's limitations —
lenient parsers, retry budgets, defensive reprompts. The discipline is to keep the loop thin and
delete scaffolding at each model bump. This module turns that slogan into an artifact: tag each
compensating block with a one-line convention, and `find_scaffolds` (or `python -m verso.scaffolds`)
surfaces the whole inventory to review when the model changes.

Convention — a comment placed on or above the block it compensates for::

    # SCAFFOLD(<weakness>): <note>

`<weakness>` is a short slug for the model limitation (e.g. ``malformed-json``); `<note>` is free text.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path

# Matches a real tag comment. The weakness slug is an identifier-ish token ([\w.-]+), which excludes
# the literal <weakness>/<note> placeholders used in the docstring above (so the convention can be
# documented in-file without the tool matching its own example). Leading text before the `#`
# (indentation, trailing code after a statement) is tolerated.
_SCAFFOLD_RE = re.compile(r"#\s*SCAFFOLD\((?P<weakness>[\w.\-]+)\)\s*:\s*(?P<note>.*)$")


@dataclass
class Scaffold:
    file: str
    line: int
    weakness: str
    note: str


def find_scaffolds(root: str = "verso") -> list[Scaffold]:
    """Walk ``*.py`` under ``root`` and return every ``# SCAFFOLD(...)`` tag, sorted by file then line.

    Pure stdlib, read-only. ``file`` is reported as the path relative to the current directory when
    possible (falling back to the path as walked), so output is stable across machines."""
    base = Path(root)
    out: list[Scaffold] = []
    for path in sorted(base.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            name = str(path.relative_to(Path.cwd()))
        except ValueError:
            name = str(path)
        for i, raw in enumerate(text.splitlines(), start=1):
            m = _SCAFFOLD_RE.search(raw)
            if m:
                out.append(Scaffold(file=name, line=i,
                                    weakness=m.group("weakness").strip(),
                                    note=m.group("note").strip()))
    out.sort(key=lambda s: (s.file, s.line))
    return out


def _format(scaffolds: list[Scaffold]) -> str:
    if not scaffolds:
        return "No scaffolds found."
    lines: list[str] = [f"{len(scaffolds)} scaffold(s):"]
    current: str | None = None
    for s in scaffolds:
        if s.file != current:
            current = s.file
            lines.append(f"\n{s.file}")
        lines.append(f"  L{s.line} [{s.weakness}] {s.note}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import sys
    root = (argv or sys.argv[1:] or ["verso"])[0]
    print(_format(find_scaffolds(root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
