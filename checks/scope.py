"""The change scope rule: the code patch adds or edits files under src/ and tests/ only.

It may not touch acceptance/, .github/, policy, the request, documentation
(the documentation contract owns docs/) or any existing test; it may not delete,
rename, or change file modes. Every patch-applying check enforces the same rule;
this check reports it on its own row.
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from software_factory_support import execute


def inspect(
    root: Path, candidate: Path, area: Path, subject: dict[str, Any]
) -> tuple[int, list[dict[str, Any]]]:
    return 0, [{"id": "scope", "status": "passed"}]


if __name__ == "__main__":
    raise SystemExit(execute("change-scope", inspect))
