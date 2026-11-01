"""Apply changes.diff and run the repository's own acceptance/*.feature scenarios.

Features and step definitions are the repository's, read from the original
project bytes; a patch that touches acceptance/ is rejected before anything runs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from software_factory_bdd import inspect
from software_factory_support import execute

if __name__ == "__main__":
    raise SystemExit(execute("acceptance", inspect))
