"""Desktop GUI launcher for the CCPP HBD solver."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.exists():
    sys.path.insert(0, str(SRC_PATH))

from ccpp_hbd_solver.ui import launch_gui


def main() -> None:
    """Start the interactive GUI."""

    launch_gui()


if __name__ == "__main__":
    main()
