"""Check this example's document formats/references, not prose semantic correctness."""

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from software_factory_bdd import feature_files, scenario_ids
from software_factory_support import (
    SOURCE_ROOT,
    TESTS_ROOT,
    Invalid,
    digest,
    inventory,
    read_file,
)

TARGET_ROOTS = ("src/", "tests/", "docs/")

SCHEMA = "software-factory-document/2"
SECTIONS = {
    "planning": ("Goal", "Changes", "Validation", "Risks"),
    "specification": ("Behavior", "Interface", "Acceptance"),
    "implementation": ("Changes", "Validation", "Limitations"),
    "documentation": ("Changes", "Validation", "Limitations"),
    "review": ("Assessment", "Findings", "Limitations"),
}
FIELDS = {
    "planning": {"acceptance", "targets"},
    "specification": {"acceptance", "interfaces"},
    "implementation": set(),
    "documentation": set(),
    "review": {"findings"},
}
REVIEW_ARTIFACTS = {
    "request.md",
    "specification.md",
    "changes.diff",
    "implementation.md",
    "documentation.diff",
    "documentation.md",
}


class Rejected(Exception):
    """A completed candidate does not satisfy the authored document profile."""


def markdown_sections(text: str) -> tuple[dict[str, str], list[str]]:
    """Parse bounded H2 sections and JSON fences, ignoring headings in code fences."""
    sections: dict[str, list[str]] = {}
    blocks: list[str] = []
    heading = None
    fence = None
    language = ""
    block: list[str] = []
    for line in text.splitlines():
        marker = re.fullmatch(r" {0,3}(`{3,}|~{3,})(.*)", line)
        if fence:
            if (
                marker
                and marker[1][0] == fence[0]
                and len(marker[1]) >= len(fence)
                and not marker[2].strip()
            ):
                if language == "json":
                    blocks.append("\n".join(block))
                fence = None
            else:
                block.append(line)
                if heading is not None:
                    sections[heading].append(line)
            continue
        if marker:
            fence, language, block = marker[1], marker[2].strip(), []
            if language == "json" and heading is not None:
                raise Rejected("The metadata JSON block must precede document sections.")
            continue
        match = re.fullmatch(r"## ([^\n]+)", line)
        if match:
            heading = match[1].strip()
            if heading in sections:
                raise Rejected(f"Duplicate Markdown section: {heading}")
            sections[heading] = []
        elif heading is not None:
            sections[heading].append(line)
    if fence:
        raise Rejected("Unterminated Markdown code fence.")
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}, blocks


def require_sections(sections: dict[str, str], required: tuple[str, ...]) -> None:
    for name in required:
        if not sections.get(name):
            raise Rejected(f"Missing or empty Markdown section: {name}")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise Rejected(f"Duplicate JSON metadata key: {key}")
        result[key] = value
    return result


def exact_references(value: Any, expected: tuple[str, ...], label: str) -> None:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) for item in value)
        or len(value) != len(expected)
        or set(value) != set(expected)
    ):
        raise Rejected(f"{label} must name every supplied reference exactly once.")


def validate_metadata(root: Path, kind: str, data: Any) -> set[str]:
    if (
        not isinstance(data, dict)
        or set(data) != {"schema", "document", *FIELDS[kind]}
        or data.get("schema") != SCHEMA
        or data.get("document") != kind
    ):
        raise Rejected("Metadata fields, document type or example schema version do not match.")
    references: set[str] = set()
    if kind in ("planning", "specification"):
        exact_references(data["acceptance"], scenario_ids(root), "Acceptance IDs")
        references.update(path.relative_to(root).as_posix() for path in feature_files(root))
    if kind == "planning":
        targets = data["targets"]
        if (
            not isinstance(targets, list)
            or not 1 <= len(targets) <= 30
            or any(
                not isinstance(item, dict)
                or set(item) != {"path", "state"}
                or not isinstance(item["path"], str)
                for item in targets
            )
        ):
            raise Rejected("Targets must be 1 to 30 objects with path and state.")
        paths = [item["path"] for item in targets]
        if len(set(paths)) != len(paths):
            raise Rejected("Each target path must appear once.")
        for item in targets:
            path = item["path"]
            if not path.startswith(TARGET_ROOTS) or ".." in path.split("/"):
                raise Rejected(f"Targets stay under src/, tests/ or docs/: {path}")
            try:
                read_file(root, path)
            except FileNotFoundError:
                expected = "new"
            else:
                expected = "existing"
                references.add(path)
            if item["state"] != expected:
                raise Rejected(f"Target state must be {expected}: {path}")
            if path.startswith(TESTS_ROOT + "/") and expected == "existing":
                raise Rejected(f"Existing tests are preserved, not targets: {path}")
        for prefix, label in (
            ("src/", "a src/ file"),
            ("tests/", "a new test file"),
            ("docs/", "a docs/ page"),
        ):
            if not any(path.startswith(prefix) for path in paths):
                raise Rejected(f"Targets must include {label}.")
    elif kind == "specification":
        interfaces = data["interfaces"]
        if (
            not isinstance(interfaces, list)
            or not 1 <= len(interfaces) <= 30
            or any(not isinstance(item, str) for item in interfaces)
            or len(set(interfaces)) != len(interfaces)
        ):
            raise Rejected("Interfaces must be 1 to 30 unique path:name strings.")
        for item in interfaces:
            path, separator, name = item.partition(":")
            if not separator or not path.startswith(SOURCE_ROOT + "/") or not path.endswith(".py"):
                raise Rejected(f"Interface must be src/<module>.py:<name>: {item}")
            try:
                module = ast.parse(read_file(root, path), filename=path)
            except FileNotFoundError as exc:
                raise Rejected(
                    f"Interface module does not exist in the captured source: {path}"
                ) from exc
            public = {
                node.name
                for node in module.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and not node.name.startswith("_")
            }
            if name not in public:
                raise Rejected(f"Interface is not a public function or class in {path}: {name}")
            references.add(path)
    elif kind == "review":
        findings = data["findings"]
        if not isinstance(findings, list) or len(findings) > 20:
            raise Rejected("Findings must be a list of at most 20 references; [] is valid.")
        for item in findings:
            if (
                not isinstance(item, dict)
                or set(item) != {"artifact", "line", "detail"}
                or not isinstance(item["artifact"], str)
                or item["artifact"] not in REVIEW_ARTIFACTS
                or type(item["line"]) is not int
                or not isinstance(item["detail"], str)
                or not 1 <= len(item["detail"].strip()) <= 800
            ):
                raise Rejected(
                    "A finding needs an admitted artifact, integer line and bounded detail."
                )
            lines = read_file(root, item["artifact"]).splitlines()
            if not 1 <= item["line"] <= len(lines):
                raise Rejected("Finding line does not exist in the referenced artifact.")
            references.add(item["artifact"])
    return references


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", choices=SECTIONS)
    parser.add_argument("artifact")
    args = parser.parse_args(argv)
    result = {
        "schema": SCHEMA,
        "document": args.document,
        "scope": "Document format and reference consistency; no semantic correctness or execution claim.",
    }
    try:
        raw = read_file(Path.cwd(), args.artifact, 16 * 1024)
        result["sha256"] = digest(raw)
        text = raw.decode("ascii")
        sections, blocks = markdown_sections(text)
        require_sections(sections, SECTIONS[args.document])
        if len(blocks) != 1:
            raise Rejected("Expected exactly one versioned JSON metadata block before sections.")
        data = json.loads(blocks[0], object_pairs_hook=unique_object)
        references = validate_metadata(Path.cwd(), args.document, data)
        result.update(status="passed", references=inventory(Path.cwd(), tuple(references)))
        code = 0
    except (Rejected, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        result.update(status="failed", detail=str(exc)[:600])
        code = 1
    except (Invalid, OSError, SyntaxError) as exc:
        result.update(status="error", detail=str(exc)[:600])
        code = 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
