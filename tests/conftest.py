"""Pytest configuration: make the ``scripts/`` modules importable as
plain top-level modules (``fabric_items``, ``validate_pbip``, ...)
without turning ``scripts/`` into an installed package.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
