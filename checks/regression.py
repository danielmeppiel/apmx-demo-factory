"""Apply changes.diff; the repository's whole unittest suite must pass, plus new tests.

The existing tests come from the original project (the scope rule forbids
editing them). Their identities are observed on the original tree first, so
every one of them must still run and pass on the candidate, and the change must
add at least one new test of its own.
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from software_factory_support import Invalid, execute, original_tree, run_driver


def suite(root: Path, tree: Path, area: Path) -> tuple[int, dict[str, str]]:
    returncode, report = run_driver(root, tree, area, "regression_driver.py")
    tests = report.get("tests") if isinstance(report, dict) else None
    if (
        not isinstance(tests, list)
        or len(tests) > 5000
        or any(
            not isinstance(row, dict)
            or not isinstance(row.get("id"), str)
            or row.get("status") not in ("passed", "failed", "incomplete")
            for row in tests
        )
    ):
        raise Invalid("Malformed unittest report.")
    rows = {row["id"]: row["status"] for row in tests}
    if len(rows) != len(tests) or returncode not in (0, 1):
        raise Invalid("Unittest report identities or exit status are incomplete.")
    if (returncode == 0) != (bool(rows) and all(s == "passed" for s in rows.values())):
        raise Invalid("Unittest process and complete report disagree.")
    return returncode, rows


def inspect(
    root: Path, candidate: Path, area: Path, subject: dict[str, Any]
) -> tuple[int, list[dict[str, Any]]]:
    code, original = suite(root, original_tree(root, area), area)
    if code or not original:
        raise Invalid("The repository's own tests do not pass on the original project.")
    _, observed = suite(root, candidate, area)
    rows: list[dict[str, Any]] = []
    for identifier in sorted(original):
        rows.append({"id": identifier, "status": observed.get(identifier, "missing")})
    added = sorted(set(observed) - set(original))
    rows.extend(
        {"id": identifier, "status": observed[identifier], "new": True} for identifier in added
    )
    if not added:
        rows.append(
            {"id": "new-tests", "status": "failed", "detail": "the change adds no new tests"}
        )
    return int(any(row["status"] != "passed" for row in rows)), rows


if __name__ == "__main__":
    raise SystemExit(execute("regression", inspect))
