"""Pytest configuration shared across all test modules."""

from __future__ import annotations

import sys
from pathlib import Path

# Make the in-tree pomodoro package and app.py importable.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
