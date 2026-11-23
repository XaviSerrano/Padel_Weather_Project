import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.vercel_app import build_handler  # noqa: E402


class handler(build_handler()):
    pass
