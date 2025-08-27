# backend/tests/conftest.py
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]  # <repo>/backend
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

