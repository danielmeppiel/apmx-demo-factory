"""Run the repository's unittest suite (tests/) against one tree.

argv: ROOT TREE REPORT. Records every test identity and outcome; skips, expected
failures and unexpected successes are not passes.
"""

import io
import json
import sys
import unittest
from pathlib import Path
from typing import Any


class ObservedResult(unittest.TextTestResult):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.rows: dict[str, str] = {}

    def _mark(self, test: Any, status: str) -> None:
        identifier = test.id()
        if self.rows.get(identifier) in (None, "passed"):
            self.rows[identifier] = status

    def addSuccess(self, test: Any) -> None:
        super().addSuccess(test)
        self._mark(test, "passed")

    def addFailure(self, test: Any, err: Any) -> None:
        super().addFailure(test, err)
        self._mark(test, "failed")

    def addError(self, test: Any, err: Any) -> None:
        super().addError(test, err)
        self._mark(test, "failed")

    def addSkip(self, test: Any, reason: str) -> None:
        super().addSkip(test, reason)
        self._mark(test, "incomplete")

    def addExpectedFailure(self, test: Any, err: Any) -> None:
        super().addExpectedFailure(test, err)
        self._mark(test, "incomplete")

    def addUnexpectedSuccess(self, test: Any) -> None:
        super().addUnexpectedSuccess(test)
        self._mark(test, "incomplete")

    def addSubTest(self, test: Any, subtest: Any, err: Any) -> None:
        super().addSubTest(test, subtest, err)
        if err is not None:
            self._mark(test, "failed")


def main() -> int:
    _root, tree, destination = map(Path, sys.argv[1:4])
    sys.path[0:0] = [str(tree / "src"), str(tree)]
    tests = tree / "tests"
    top = tree if (tests / "__init__.py").is_file() else tests
    suite = unittest.defaultTestLoader.discover(
        str(tests), pattern="test*.py", top_level_dir=str(top)
    )
    result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=ObservedResult).run(suite)
    rows = [{"id": key, "status": value} for key, value in sorted(result.rows.items())]
    destination.write_text(
        json.dumps({"tests": rows, "tests_run": result.testsRun}), encoding="ascii"
    )
    return int(any(row["status"] != "passed" for row in rows) or not rows)


if __name__ == "__main__":
    raise SystemExit(main())
