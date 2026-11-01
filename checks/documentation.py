"""Check the documentation patch: Markdown pages under docs/, valid links, changed behaviour named.

The pages it edits must keep valid inline local links and H2 anchors, and at
least one line it adds or rewrites must link to a src/ file that the code patch
changed, so the documentation describes the change rather than the old page.
"""

import collections
import difflib
import posixpath
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

from documents import Rejected, markdown_sections
from software_factory_support import SOURCE_ROOT, Invalid, execute, read_file

LINK = r"!?\[[^\]\n]*\]\(([^()\n]*)\)"


def local_links(candidate: Path, name: str, text: str) -> list[str]:
    """Resolve inline local links and H2 fragments; external URLs are not fetched."""
    if re.search(r"(?m)^ {0,3}\[[^\]\n]+\]:|!?\[[^\]\n]+\]\[[^\]\n]*\]", text):
        raise Rejected(f"{name}: reference-style links are outside this factory's link format.")
    if re.search(r"!?\[[^\]\n]*\]\(", re.sub(LINK, "", text)):
        raise Rejected(f"{name}: malformed or unsupported inline link.")
    resolved = []
    for target in re.findall(LINK, text):
        if not target or any(character.isspace() for character in target):
            raise Rejected(f"{name}: link targets must be nonempty URLs without spaces.")
        try:
            parsed = urlsplit(target)
        except ValueError as exc:
            raise Rejected(f"{name}: malformed link {target}") from exc
        if parsed.scheme in ("http", "https") and parsed.netloc:
            continue
        if parsed.scheme or parsed.netloc or parsed.query:
            raise Rejected(f"{name}: expected a relative local link or an absolute HTTP(S) link.")
        path = (
            posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(parsed.path)))
            if parsed.path
            else name
        )
        try:
            raw = read_file(candidate, path)
        except (Invalid, FileNotFoundError, IsADirectoryError, NotADirectoryError) as exc:
            raise Rejected(f"{name}: local link target does not exist: {target}") from exc
        if parsed.fragment:
            sections, _ = markdown_sections(raw.decode("utf-8", "replace"))
            anchors = {
                re.sub(r"[^a-z0-9 _-]", "", heading.lower()).replace(" ", "-")
                for heading in sections
            }
            if unquote(parsed.fragment) not in anchors:
                raise Rejected(f"{name}: H2 anchor does not exist: {target}")
        resolved.append(path)
    return resolved


def added_lines(before: str, after: str) -> str:
    """The lines the documentation patch adds or rewrites, in page order."""
    old, new = before.splitlines(), after.splitlines()
    matcher = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    return "\n".join(
        line
        for tag, _, _, start, end in matcher.get_opcodes()
        if tag in ("insert", "replace")
        for line in new[start:end]
    )


def inspect(
    root: Path, candidate: Path, area: Path, subject: dict[str, Any]
) -> tuple[int, list[dict[str, Any]]]:
    pages = subject["documentation_edits"]
    changed_source = {name for name in subject["changed"] if name.startswith(SOURCE_ROOT + "/")}
    rows = []
    new_targets: collections.Counter[str] = collections.Counter()
    for name in pages:
        try:
            text = read_file(candidate, name, 16 * 1024).decode("ascii")
            sections, _ = markdown_sections(text)
            if not sections:
                raise Rejected(f"{name}: a documentation page needs H2 sections.")
            local_links(candidate, name, text)
            before = (
                read_file(root, name).decode("utf-8", "replace") if (root / name).is_file() else ""
            )
            new_targets.update(local_links(candidate, name, added_lines(before, text)))
            rows.append({"id": name, "status": "passed"})
        except (Rejected, UnicodeError) as exc:
            rows.append({"id": name, "status": "failed", "detail": str(exc)[:600]})
    described = sorted(changed_source & set(new_targets))
    rows.append(
        {
            "id": "describes-changed-source",
            "status": "passed" if described else "failed",
            "detail": (
                "new links to changed source: " + ", ".join(described)
                if described
                else "no added or rewritten line of the documentation links to a src/ file "
                "the code patch changed; link the new text to one of: "
                + ", ".join(sorted(changed_source))
            ),
        }
    )
    return int(any(row["status"] != "passed" for row in rows)), rows


if __name__ == "__main__":
    raise SystemExit(execute("documentation", inspect, documentation=True))
