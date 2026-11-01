"""The receiving repository's Gherkin acceptance: discovery and strict report checks.

Feature files and their step definitions live in the repository's acceptance/
directory and are read from the ORIGINAL project bytes, never from a patch.
"""

from pathlib import Path
from typing import Any

from software_factory_support import ACCEPTANCE_ROOT, Invalid, read_file, run_driver

MAX_FEATURES = 20


def load_behave() -> Any:
    try:
        import behave
        from behave.parser import parse_file
    except ImportError as exc:
        raise Invalid(
            "Behave is missing. Install checks/requirements.txt (Behave==1.3.3) "
            "in the Python environment running this check."
        ) from exc
    if behave.__version__ != "1.3.3":
        raise Invalid("This factory requires Behave==1.3.3.")
    return parse_file


def feature_files(root: Path) -> list[Path]:
    directory = root / ACCEPTANCE_ROOT
    if directory.is_symlink() or not directory.is_dir():
        raise Invalid("The repository has no acceptance/ directory of Gherkin features.")
    files = sorted(directory.glob("*.feature"))
    if not 1 <= len(files) <= MAX_FEATURES:
        raise Invalid(f"Expected 1 to {MAX_FEATURES} acceptance/*.feature files.")
    for path in files:
        read_file(root, path.relative_to(root).as_posix(), 64 * 1024)
    return files


def _top_level(feature: Any) -> list[Any]:
    items = list(feature.scenarios)
    for rule in getattr(feature, "rules", None) or []:
        items.extend(rule.scenarios)
    return items


def scenario_ids(root: Path) -> tuple[str, ...]:
    """Acceptance IDs: Scenario and Scenario Outline titles, as written, across features."""
    parse_file = load_behave()
    identifiers: list[str] = []
    for path in feature_files(root):
        try:
            feature = parse_file(str(path))
        except Exception as exc:
            raise Invalid(f"Acceptance feature could not be parsed: {path.name}") from exc
        identifiers.extend(item.name.strip() for item in _top_level(feature))
    if not identifiers or len(set(identifiers)) != len(identifiers) or not all(identifiers):
        raise Invalid("Acceptance scenarios need unique, nonempty titles.")
    return tuple(identifiers)


def expected_scenarios(root: Path) -> dict[tuple[str, str, int], dict[str, Any]]:
    """Every executable scenario (outline rows expanded) keyed by file, name and line."""
    parse_file = load_behave()
    expected: dict[tuple[str, str, int], dict[str, Any]] = {}
    scenario_ids(root)
    for path in feature_files(root):
        feature = parse_file(str(path))
        for item in _top_level(feature):
            runs = list(item.scenarios) if hasattr(item, "examples") else [item]
            if not runs:
                raise Invalid(f"Scenario Outline without examples: {item.name}")
            for scenario in runs:
                key = (str(path.resolve()), scenario.name, scenario.line)
                expected[key] = {
                    "id": item.name.strip(),
                    "steps": [
                        {"name": step.name, "keyword": step.keyword, "line": step.line}
                        for step in scenario.all_steps
                    ],
                }
    return expected


def _location(location: Any, report_root: Path) -> tuple[str, int] | None:
    if not isinstance(location, str):
        return None
    name, separator, number = location.rpartition(":")
    if not separator or not name or not number.isdigit():
        return None
    return str((report_root / name).resolve()), int(number)


FAILED = ("failed", "error", "hook_error")


def validate_report(
    report: Any, expected: dict[tuple[str, str, int], dict[str, Any]], report_root: Path
) -> tuple[int, list[dict[str, Any]]]:
    if not isinstance(report, list) or any(
        not isinstance(feature, dict) or not isinstance(feature.get("elements"), list)
        for feature in report
    ):
        raise Invalid("Malformed Behave report.")
    seen: dict[tuple[str, str, int], str] = {}
    for feature in report:
        for element in feature["elements"]:
            if not isinstance(element, dict):
                raise Invalid("Malformed Behave scenario report.")
            if element.get("type") == "background":
                continue
            where = _location(element.get("location"), report_root)
            name = element.get("name")
            if element.get("type") != "scenario" or where is None or not isinstance(name, str):
                raise Invalid("Behave scenario identities are incomplete.")
            key = (where[0], name, where[1])
            if key not in expected or key in seen:
                raise Invalid("Behave reported an unexpected or duplicated scenario.")
            trusted = expected[key]["steps"]
            steps = element.get("steps")
            if not isinstance(steps, list) or len(steps) != len(trusted):
                raise Invalid("Behave steps do not match the repository's scenario.")
            statuses = []
            for actual, step in zip(steps, trusted, strict=True):
                if not isinstance(actual, dict):
                    raise Invalid("Malformed Behave step.")
                at = _location(actual.get("location"), report_root)
                if (
                    actual.get("name") != step["name"]
                    or actual.get("keyword") != step["keyword"]
                    or at != (where[0], step["line"])
                ):
                    raise Invalid("Behave steps do not match the repository's scenario.")
                result = actual.get("result")
                statuses.append(result.get("status") if isinstance(result, dict) else None)
            status = element.get("status")
            if status == "passed":
                if any(item != "passed" for item in statuses):
                    raise Invalid("A passing scenario contains an unexecuted step.")
            elif status in FAILED:
                if status != "hook_error" and not any(item in FAILED for item in statuses):
                    raise Invalid("A failed scenario lacks an observed step failure.")
            else:
                raise Invalid(
                    f"Scenario '{name}' was {status}: undefined, skipped or unexecuted "
                    "steps are not results."
                )
            seen[key] = "passed" if status == "passed" else "failed"
    if set(seen) != set(expected):
        raise Invalid("Behave omitted or filtered required acceptance scenarios.")
    rows: dict[str, str] = {}
    for key, status in seen.items():
        identifier = expected[key]["id"]
        rows[identifier] = "failed" if "failed" in (rows.get(identifier), status) else status
    observed = [{"id": identifier, "status": status} for identifier, status in rows.items()]
    return int(any(row["status"] == "failed" for row in observed)), observed


def inspect(
    root: Path, candidate: Path, area: Path, subject: dict[str, Any]
) -> tuple[int, list[dict[str, Any]]]:
    expected = expected_scenarios(root)
    returncode, report = run_driver(root, candidate, area, "acceptance_driver.py")
    code, rows = validate_report(report, expected, area)
    if returncode not in (0, 1) or (returncode == 0) != (code == 0):
        raise Invalid("Behave process and complete report disagree.")
    return code, rows
