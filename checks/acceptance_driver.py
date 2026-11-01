"""Run the repository's own acceptance/ features against one candidate tree.

argv: ROOT CANDIDATE REPORT. Features and step definitions come from ROOT, the
original project bytes; only the application under test comes from CANDIDATE.
External Behave configuration is ignored.
"""

import sys
from pathlib import Path


def main() -> int:
    root, candidate, report = map(Path, sys.argv[1:4])
    from behave.configuration import Configuration
    from behave.runner import Runner

    sys.path[0:0] = [str(candidate / "src"), str(candidate)]
    config = Configuration(
        [
            str(root / "acceptance"),
            "--format",
            "json",
            "--outfile",
            str(report),
            "--no-summary",
            "--no-snippets",
            "--no-capture",
            "--no-capture-stderr",
            "--no-logcapture",
            "-D",
            f"candidate={candidate}",
        ],
        load_config=False,
    )
    config.stop = False
    return int(Runner(config).run())


if __name__ == "__main__":
    raise SystemExit(main())
