import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from tseda.bump_version import _bump, main


def test_bump_major_minor_patch():
    assert _bump(0, 0, 0, "patch") == (0, 0, 1)
    assert _bump(0, 0, 0, "minor") == (0, 1, 0)
    assert _bump(0, 0, 0, "major") == (1, 0, 0)


def test_main_updates_pyproject_toml(tmp_path, monkeypatch, capsys):
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text('version = "0.1.7"\n', encoding="utf-8")

    monkeypatch.setattr("tseda.bump_version._PYPROJECT", pyproject_path)
    monkeypatch.setattr(sys, "argv", ["bump-version", "minor"])

    main()

    assert pyproject_path.read_text(encoding="utf-8").strip() == 'version = "0.2.0"'
    captured = capsys.readouterr()
    assert "Bumped minor: 0.1.7 → 0.2.0" in captured.out


def test_main_rejects_invalid_part(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["bump-version", "invalid"])
    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "error: unknown part 'invalid'" in captured.err
