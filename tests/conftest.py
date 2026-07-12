"""Repo root isn't installed as a package (see how scripts/*.py all do a
manual sys.path.insert), so tests need the same treatment to import `src.*`.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
