"""Opt-in Windows libpq discovery using the administrator-installed PostgreSQL client."""

import os
from pathlib import Path
from typing import Any

_dll_directories: list[Any] = []


def configure_libpq(postgres_bin: str) -> None:
    if os.name != "nt" or not postgres_bin:
        return
    directory = Path(postgres_bin)
    if not directory.is_absolute() or not (directory / "libpq.dll").is_file():
        raise RuntimeError(
            "POSTGRES_BIN must be an absolute installed PostgreSQL bin directory with libpq.dll"
        )
    directory = directory.resolve()
    # ctypes discovery uses PATH; Windows resolves libpq's dependencies through
    # AddDllDirectory. Retain the handle for the lifetime of this process.
    _dll_directories.append(os.add_dll_directory(str(directory)))
    os.environ["PATH"] = str(directory) + os.pathsep + os.environ.get("PATH", "")
    os.environ.setdefault("PSYCOPG_IMPL", "python")
