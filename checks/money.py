"""House standard: money is integer cents, so src/ has no float literals and no float() calls.

An AST rule over every Python file under src/ in the patched candidate.
"""

import ast
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from software_factory_support import SOURCE_ROOT, execute, read_file, tree_names


def violations(tree: Path) -> list[dict[str, Any]]:
    rows = []
    for name in tree_names(tree, (SOURCE_ROOT,)):
        if not name.endswith(".py"):
            continue
        try:
            module = ast.parse(read_file(tree, name), filename=name)
        except SyntaxError as exc:
            rows.append(
                {"id": f"{name}:{exc.lineno}", "status": "failed", "detail": "syntax error"}
            )
            continue
        for node in ast.walk(module):
            if isinstance(node, ast.Constant) and isinstance(node.value, (float, complex)):
                detail = f"float literal {node.value!r}; use integer cents"
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "float"
            ):
                detail = "float() call; use integer cents"
            else:
                continue
            rows.append({"id": f"{name}:{node.lineno}", "status": "failed", "detail": detail})
    return rows


def inspect(
    root: Path, candidate: Path, area: Path, subject: dict[str, Any]
) -> tuple[int, list[dict[str, Any]]]:
    rows = violations(candidate)
    return (1, rows) if rows else (0, [{"id": "integer-cents", "status": "passed"}])


if __name__ == "__main__":
    raise SystemExit(execute("money-in-cents", inspect))
