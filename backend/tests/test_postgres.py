import os
import sys

import pytest

from app.core import postgres


def test_linux_ignores_windows_configuration(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    before = dict(os.environ)
    postgres.configure_libpq("/nonexistent/postgres")
    assert dict(os.environ) == before


def test_empty_configuration_is_noop():
    before = dict(os.environ)
    postgres.configure_libpq("")
    assert dict(os.environ) == before


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DLL discovery")
def test_windows_rejects_invalid_directories(tmp_path):
    for directory in ("relative", str(tmp_path)):
        with pytest.raises(RuntimeError, match="POSTGRES_BIN"):
            postgres.configure_libpq(directory)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DLL discovery")
@pytest.mark.parametrize("implementation", [None, "binary"])
def test_windows_retains_dll_handle_and_respects_implementation(monkeypatch, tmp_path, implementation):
    (tmp_path / "libpq.dll").touch()
    handle = object()
    directories = []
    monkeypatch.setattr(postgres, "_dll_directories", [])
    monkeypatch.setattr(os, "add_dll_directory", lambda path: directories.append(path) or handle)
    monkeypatch.setenv("PATH", "original-path")
    if implementation is None:
        monkeypatch.delenv("PSYCOPG_IMPL", raising=False)
    else:
        monkeypatch.setenv("PSYCOPG_IMPL", implementation)

    postgres.configure_libpq(str(tmp_path))

    assert directories == [str(tmp_path.resolve())]
    assert postgres._dll_directories == [handle]
    assert os.environ["PATH"] == str(tmp_path.resolve()) + os.pathsep + "original-path"
    assert os.environ["PSYCOPG_IMPL"] == (implementation or "python")
