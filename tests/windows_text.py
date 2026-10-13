"""Windows text mode on any platform: a text file written without `newline`
gets CRLF line endings, as io writes it on Windows. CI runs the suite this
way on Linux: python -m tests.windows_text [unittest discover options]."""
from __future__ import annotations

import contextlib
import io
import sys
import unittest
from unittest.mock import patch

_open = io.open


def _windows_open(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, closefd=True,
                  opener=None):
    if "b" not in mode and newline is None and set(mode) & set("wax+"):
        newline = "\r\n"
    return _open(file, mode, buffering, encoding, errors, newline, closefd, opener)


@contextlib.contextmanager
def windows_text():
    """open() and Path.write_text() write as on Windows while it is active."""
    with patch("io.open", _windows_open), patch("builtins.open", _windows_open):
        yield


if __name__ == "__main__":
    with windows_text():
        unittest.main(module=None, argv=[sys.argv[0], "discover", "-s", "tests", "-t", ".", *sys.argv[1:]])
