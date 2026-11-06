import os
import re
from pathlib import Path


_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def load_env_file(path: Path):
    if not path.exists():
        return

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or not _NAME.fullmatch(name):
            raise ValueError(f"Configuración no válida en {path.name}, línea {line_number}.")
        value = value.strip()
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError(f"Comillas no válidas en {path.name}, línea {line_number}.")
            value = value[1:-1]
        os.environ.setdefault(name, value)
