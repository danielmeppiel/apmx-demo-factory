"""Rerun the repository's acceptance scenarios and unittest suite on code plus docs."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from regression import inspect as inspect_regression
from software_factory_bdd import inspect as inspect_acceptance
from software_factory_support import execute


def inspect(
    root: Path, candidate: Path, area: Path, subject: dict[str, Any]
) -> tuple[int, list[dict[str, Any]]]:
    status = 0
    observed = []
    for name, check in (("acceptance", inspect_acceptance), ("regression", inspect_regression)):
        code, rows = check(root, candidate, area, subject)
        status = max(status, code)
        observed.append(
            {"id": name, "status": "passed" if code == 0 else "failed", "observed": rows}
        )
    return status, observed


if __name__ == "__main__":
    raise SystemExit(execute("combined-candidate", inspect, documentation=True))
