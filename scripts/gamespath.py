"""Locate the project root and make the build scripts importable.

Every script addresses its inputs and outputs from the project root: it reads
`games/*.yml`, and writes `games.json`, `pgn/` and `book/`. Importing this
module moves there and puts the build folder on the import path, so a script
runs the same from anywhere:

    uv run python scripts/build/records.py
"""

import os
import sys

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPTS)

GAMES_DIR = os.path.join(ROOT, "games")

_path = os.path.join(SCRIPTS, "build")
if _path not in sys.path:
    sys.path.insert(0, _path)

os.chdir(ROOT)
