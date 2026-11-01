"""Generic candidate materialization shared by this factory's checks.

The checks run in a fresh copy of the receiving repository's ORIGINAL bytes plus
the artifact under check. The agent's work arrives only as a Git patch, which is
profiled, applied to a private copy and judged there. The repository's own
acceptance specs and existing tests are read from the original bytes, so a
patch cannot weaken what judges it.

This is an example checker, not a scheduler, receipt owner or sandbox. It never
imports APMX and emits one JSON observation on stdout.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

MAX_FILE = 256 * 1024
MAX_PATCH = 128 * 1024
MAX_FILES = 2000
# The repository layout this factory works on (see README.md: Repository conventions).
APPLICATION_ROOTS = ("src", "tests", "docs", "acceptance")
APPLICATION_FILES = ("README.md",)
SOURCE_ROOT = "src"
TESTS_ROOT = "tests"
ACCEPTANCE_ROOT = "acceptance"
CODE_ROOTS = ("src/", "tests/")
DOCUMENTATION_ROOTS = ("docs/",)


class Invalid(Exception):
    """Missing, unsupported or incomplete check input or execution (exit 2)."""


class OutOfScope(Exception):
    """A well-formed patch that changes what this factory may not change (exit 1).

    An assessed rejection, so an authored repair budget can retry it.
    """

    def __init__(self, reasons: list[str], subject: dict[str, Any] | None = None) -> None:
        super().__init__("Patch is out of scope: " + "; ".join(reasons) + ".")
        self.reasons = reasons
        self.subject = subject


def read_file(root: Path, name: str, limit: int = MAX_FILE) -> bytes:
    """Read a bounded regular file without following symlink components."""
    path = Path(name)
    if path.is_absolute() or not path.parts or any(p in ("..", ".") for p in path.parts):
        raise Invalid("Expected a safe relative file path.")
    target = root
    for part in path.parts:
        target = target / part
        if target.is_symlink():
            raise Invalid(f"Symlink input is not supported: {name}")
    metadata = target.stat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
        raise Invalid(f"Expected a regular file of at most {limit} bytes: {name}")
    raw = target.read_bytes()
    if len(raw) > limit:
        raise Invalid(f"File exceeded its size limit: {name}")
    return raw


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def inventory(root: Path, names: tuple[str, ...] | list[str]) -> dict[str, dict[str, Any]]:
    result = {}
    for name in sorted(names):
        raw = read_file(root, name)
        result[name] = {"sha256": digest(raw), "size": len(raw)}
    return result


def tree_hash(files: dict[str, dict[str, Any]]) -> str:
    return digest(json.dumps(files, sort_keys=True, separators=(",", ":")).encode("ascii"))


def tree_names(root: Path, tops: tuple[str, ...], files: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Regular files under the given top-level directories, refusing symlinks."""
    names = []
    for top in tops:
        base = root / top
        if base.is_symlink():
            raise Invalid(f"Symlinked directory is not supported: {top}")
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            if path.is_symlink():
                raise Invalid(f"Symlink input is not supported: {path.relative_to(root)}")
            if path.is_file():
                names.append(path.relative_to(root).as_posix())
            elif not path.is_dir():
                raise Invalid(f"Unsupported file type: {path.relative_to(root)}")
    names.extend(name for name in files if (root / name).is_file())
    if len(names) > MAX_FILES:
        raise Invalid("The application tree is larger than this example supports.")
    return tuple(sorted(names))


def application_names(root: Path) -> tuple[str, ...]:
    return tree_names(root, APPLICATION_ROOTS, APPLICATION_FILES)


def check_inventory(root: Path) -> dict[str, dict[str, Any]]:
    names = tree_names(root, ("checks",))
    if not names or len(names) > 32:
        raise Invalid("The supplied check resource inventory is empty or too large.")
    return inventory(root, names)


def clean_environment(home: Path) -> dict[str, str]:
    """Do not let ambient Git, Python or Behave selection change the check."""
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith(("GIT_", "BEHAVE_", "PYTHON"))
    }
    env.update(
        HOME=str(home),
        USERPROFILE=str(home),
        XDG_CONFIG_HOME=str(home),
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CEILING_DIRECTORIES=str(home),
        GIT_TERMINAL_PROMPT="0",
    )
    return env


EXTENDED_VIOLATIONS = (
    ("deleted file mode", "deletes"),
    ("old mode", "changes the file mode of"),
    ("new mode", "changes the file mode of"),
    ("similarity index", "renames or copies"),
    ("dissimilarity index", "renames or copies"),
    ("rename from", "renames"),
    ("rename to", "renames"),
    ("copy from", "copies"),
    ("copy to", "copies"),
    ("Binary files", "changes binary content in"),
    ("GIT binary patch", "changes binary content in"),
)


def parse_patch(raw: bytes) -> list[dict[str, Any]]:
    """Parse a Git text patch into file edits; malformed content is invalid input."""
    try:
        text = raw.decode("ascii")
    except UnicodeError as exc:
        raise OutOfScope(["the patch is not ASCII text"]) from exc
    sections = re.split(r"(?m)^diff --git ", text)
    if sections[0] or len(sections) == 1:
        raise Invalid("Expected a Git patch with at least one file section.")
    edits: list[dict[str, Any]] = []
    for section in sections[1:]:
        lines = section.splitlines() or [""]
        header = re.fullmatch(r"a/([a-zA-Z0-9_./@+-]+) b/([a-zA-Z0-9_./@+-]+)", lines[0])
        if not header:
            raise Invalid("Patch contains an unsupported file header.")
        name = header[2]
        if any(part in ("", ".", "..") for part in name.split("/") + header[1].split("/")):
            raise Invalid("Patch contains an unsafe path.")
        if any(edit["path"] == name for edit in edits):
            raise Invalid("Patch changes the same path twice.")
        edit: dict[str, Any] = {"path": name, "kind": "modify", "violations": []}
        if header[1] != name:
            edit["violations"].append("renames or copies")
        position = 1
        while position < len(lines) and not lines[position].startswith("--- "):
            line = lines[position]
            if line == "new file mode 100644":
                edit["kind"] = "add"
            elif line.startswith("new file mode"):
                edit["kind"] = "add"
                edit["violations"].append("adds a non-regular or executable file")
            elif re.fullmatch(r"index [0-9a-f]+\.\.[0-9a-f]+(?: [0-7]{6})?", line):
                pass
            else:
                for prefix, reason in EXTENDED_VIOLATIONS:
                    if line.startswith(prefix):
                        edit["violations"].append(reason)
                        if prefix == "deleted file mode":
                            edit["kind"] = "delete"
                        break
                else:
                    raise Invalid("Patch contains an unsupported extended header.")
            position += 1
        if position < len(lines):
            before = "--- /dev/null" if edit["kind"] == "add" else f"--- a/{header[1]}"
            after = "+++ /dev/null" if edit["kind"] == "delete" else f"+++ b/{name}"
            if lines[position : position + 2] != [before, after]:
                raise Invalid("Patch headers do not describe the declared file edit.")
            position += 2
            if position == len(lines):
                raise Invalid("Patch has no text change hunks.")
            while position < len(lines):
                hunk = re.fullmatch(r"@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@.*", lines[position])
                if not hunk:
                    raise Invalid("Patch contains unsupported text outside a change hunk.")
                old, new = (int(count) if count is not None else 1 for count in hunk.groups())
                position += 1
                while old or new:
                    if position >= len(lines) or not lines[position]:
                        raise Invalid("Incomplete patch hunk.")
                    prefix = lines[position][0]
                    if prefix not in (" ", "+", "-"):
                        raise Invalid("Unsupported patch hunk content.")
                    old -= int(prefix in (" ", "-"))
                    new -= int(prefix in (" ", "+"))
                    if min(old, new) < 0:
                        raise Invalid("Patch hunk lengths do not match its content.")
                    position += 1
                    if position < len(lines) and lines[position] == r"\ No newline at end of file":
                        position += 1
        elif not edit["violations"]:
            raise Invalid("Patch section has no change.")
        edits.append(edit)
    return edits


def describe(path: str) -> str:
    if path.startswith(ACCEPTANCE_ROOT + "/"):
        return f"{path} (acceptance/ belongs to the repository)"
    if path.startswith(".github/"):
        return f"{path} (CI workflows are not the factory's to change)"
    return path


def profile(
    root: Path, raw: bytes, roots: tuple[str, ...], *, require_source: bool
) -> list[dict[str, Any]]:
    """Accept only additions/edits of regular files under ``roots``; never existing tests.

    This is the factory's scope rule, shared by every patch-applying check.
    """
    edits = parse_patch(raw)
    reasons = []
    existing_tests = {
        name.lower() for name in tree_names(root, (TESTS_ROOT,)) if name.endswith(".py")
    }
    for edit in edits:
        path = edit["path"]
        for reason in edit["violations"]:
            reasons.append(f"it {reason} {describe(path)}")
        if not path.startswith(roots):
            reasons.append(f"it changes {describe(path)}, outside {', '.join(roots)}")
        elif path.lower() in existing_tests and edit["kind"] != "add":
            reasons.append(f"it changes the existing test {path}; add new test files instead")
    if require_source and not any(edit["path"].startswith(SOURCE_ROOT + "/") for edit in edits):
        reasons.append("it does not change any file under src/")
    if reasons:
        raise OutOfScope(reasons)
    return edits


def apply_patch(candidate: Path, raw: bytes, area: Path, name: str) -> None:
    """Check and apply one profiled patch without ambient Git configuration."""
    exported = area / name
    exported.write_bytes(raw)
    git = shutil.which("git")
    if git is None:
        raise Invalid("Git is missing. Install Git and rerun this check.")
    command = [
        git,
        "-c",
        "core.longpaths=true",
        "-c",
        "core.autocrlf=false",
        "apply",
        "--whitespace=nowarn",
    ]
    for options in (["--check"], []):
        result = subprocess.run(
            [*command, *options, str(exported)],
            cwd=candidate,
            env=clean_environment(area),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
        if result.returncode:
            detail = result.stderr.decode("ascii", "backslashreplace")[:300]
            raise Invalid(f"Patch does not apply cleanly to the original project: {detail}")


def copy_tree(root: Path, destination: Path, names: tuple[str, ...]) -> None:
    for name in names:
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(read_file(root, name))


def original_tree(root: Path, area: Path, label: str = "original") -> Path:
    """A private copy of the repository's original application bytes."""
    destination = area / label
    destination.mkdir()
    copy_tree(root, destination, application_names(root))
    return destination


def _changed(base: dict[str, Any], files: dict[str, Any]) -> dict[str, Any]:
    return {
        name: {"before": base.get(name, {}).get("sha256"), "after": files[name]["sha256"]}
        for name in sorted(files)
        if base.get(name) != files[name]
    }


def materialize(root: Path, patch: str, area: Path) -> tuple[Path, dict[str, Any]]:
    """Apply the code patch to a private copy of the original application."""
    raw = read_file(root, patch, MAX_PATCH)
    base_names = application_names(root)
    base = inventory(root, base_names)
    subject: dict[str, Any] = {
        "base": tree_hash(base),
        "patch": digest(raw),
        "checks": tree_hash(check_inventory(root)),
    }
    try:
        edits = profile(root, raw, CODE_ROOTS, require_source=True)
    except OutOfScope as exc:
        exc.subject = subject
        raise
    candidate = area / "candidate"
    candidate.mkdir()
    copy_tree(root, candidate, base_names)
    apply_patch(candidate, raw, area, "captured.diff")
    expected = set(base_names) | {edit["path"] for edit in edits}
    names = tree_names(candidate, APPLICATION_ROOTS, APPLICATION_FILES)
    if set(names) != expected:
        raise Invalid("Patch changed files outside its declared edits.")
    files = inventory(candidate, names)
    subject.update(candidate=tree_hash(files), changed=_changed(base, files))
    subject["_base_files"] = base
    subject["_candidate_files"] = files
    return candidate, subject


def materialize_documented(
    root: Path, patch: str, documentation_patch: str, area: Path
) -> tuple[Path, dict[str, Any]]:
    """Apply the accepted code patch, then the documentation patch (docs/ only)."""
    candidate, subject = materialize(root, patch, area)
    raw = read_file(root, documentation_patch, MAX_PATCH)
    subject["documentation_patch"] = digest(raw)
    subject["code_candidate"] = subject["candidate"]
    try:
        edits = profile(root, raw, DOCUMENTATION_ROOTS, require_source=False)
    except OutOfScope as exc:
        exc.subject = {key: value for key, value in subject.items() if not key.startswith("_")}
        raise
    not_markdown = [edit["path"] for edit in edits if not edit["path"].endswith(".md")]
    if not_markdown:
        raise OutOfScope(
            [f"it changes {name}; documentation pages are Markdown" for name in not_markdown],
            {key: value for key, value in subject.items() if not key.startswith("_")},
        )
    code_files = subject["_candidate_files"]
    apply_patch(candidate, raw, area, "captured-documentation.diff")
    names = tree_names(candidate, APPLICATION_ROOTS, APPLICATION_FILES)
    if set(names) != set(code_files) | {edit["path"] for edit in edits}:
        raise Invalid("Documentation patch changed files outside its declared edits.")
    files = inventory(candidate, names)
    for name, entry in code_files.items():
        if not name.startswith(DOCUMENTATION_ROOTS) and files[name] != entry:
            raise Invalid("Documentation changed the accepted code candidate.")
    subject.update(
        candidate=tree_hash(files),
        changed=_changed(subject["_base_files"], files),
        documentation_edits=sorted(edit["path"] for edit in edits),
    )
    subject["_candidate_files"] = files
    return candidate, subject


def run_driver(
    root: Path, tree: Path, area: Path, script: str, *arguments: str, timeout: int = 60
) -> tuple[int, Any]:
    """Run trusted check code in a fresh interpreter with a bounded JSON report."""
    report = area / f"result-{uuid.uuid4().hex}.json"
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(root / "checks" / script),
            str(root),
            str(tree),
            str(report),
            *arguments,
        ],
        cwd=area,
        env=clean_environment(area),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=timeout,
        check=False,
    )
    try:
        raw = read_file(area, report.name, 4 * 1024 * 1024)
    except FileNotFoundError as exc:
        raise Invalid(f"{script} did not write its report (exit {result.returncode}).") from exc
    try:
        return result.returncode, json.loads(raw)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise Invalid("The check report is not valid bounded JSON.") from exc


def import_roots(tree: Path) -> list[str]:
    """The repository convention: src/ is the import root (the tree root as fallback)."""
    return [str(tree / SOURCE_ROOT), str(tree)]


def execute(
    name: str,
    inspect: Callable[[Path, Path, Path, dict[str, Any]], tuple[int, list[dict[str, Any]]]],
    argv: list[str] | None = None,
    *,
    documentation: bool = False,
) -> int:
    parser = argparse.ArgumentParser(description=f"Apply a captured patch and run {name}.")
    parser.add_argument("patch", help="Relative code patch artifact, normally changes.diff")
    if documentation:
        parser.add_argument("documentation_patch", help="Docs-only patch, applied after code")
    args = parser.parse_args(argv)
    root = Path.cwd().resolve()
    area = root / f".software-factory-check-{uuid.uuid4().hex}"
    evidence: dict[str, Any] = {
        "schema": "software-factory-check/2",
        "check": name,
        "observed": [],
        "subject": None,
        "status": "error",
    }
    code = 2
    try:
        area.mkdir(mode=0o700)
        candidate, subject = (
            materialize_documented(root, args.patch, args.documentation_patch, area)
            if documentation
            else materialize(root, args.patch, area)
        )
        evidence["subject"] = {k: v for k, v in subject.items() if not k.startswith("_")}
        code, rows = inspect(root, candidate, area, subject)
        evidence["observed"] = rows
        if code not in (0, 1):
            raise Invalid("The check could not complete.")
        names = tuple(subject["_candidate_files"])
        if inventory(candidate, names) != subject["_candidate_files"]:
            raise Invalid("Candidate files changed while checks were running.")
        if inventory(root, tuple(subject["_base_files"])) != subject["_base_files"]:
            raise Invalid("The original project changed while checks were running.")
        if digest(read_file(root, args.patch, MAX_PATCH)) != subject["patch"]:
            raise Invalid("Patch artifact changed while checks were running.")
        if documentation and (
            digest(read_file(root, args.documentation_patch, MAX_PATCH))
            != subject["documentation_patch"]
        ):
            raise Invalid("Documentation patch changed while checks were running.")
        if tree_hash(check_inventory(root)) != subject["checks"]:
            raise Invalid("Supplied check resources changed while checks were running.")
        evidence["status"] = "passed" if code == 0 else "failed"
    except OutOfScope as exc:
        code = 1
        evidence["status"] = "failed"
        evidence["subject"] = exc.subject
        evidence["detail"] = str(exc).encode("ascii", "backslashreplace").decode("ascii")[:900]
    except (
        Invalid,
        OSError,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
        subprocess.SubprocessError,
    ) as exc:
        code = 2
        evidence["status"] = "error"
        evidence["detail"] = str(exc).encode("ascii", "backslashreplace").decode("ascii")[:900]
    finally:
        if area.exists():
            try:
                shutil.rmtree(area)
            except OSError:
                code = 2
                evidence.update(
                    status="error", detail="Could not remove the private check workspace."
                )
    print(json.dumps(evidence, sort_keys=True, ensure_ascii=True))
    return code
