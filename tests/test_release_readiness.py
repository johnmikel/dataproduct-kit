from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_verify_script_runs_release_readiness_checks() -> None:
    script = ROOT / "scripts/verify.sh"

    assert script.exists()
    assert os.access(script, os.X_OK)
    text = script.read_text(encoding="utf-8")
    assert 'PYTHON="${PYTHON:-python3}"' in text
    assert '"$PYTHON" -m pytest' in text
    assert '"$PYTHON" -m ruff check .' in text
    assert '"$PYTHON" -m pip check' in text
    assert '"$PYTHON" -m build' in text
    assert '"$PYTHON" -m twine check' in text


def test_manifest_includes_docs_examples_and_scripts_in_sdist() -> None:
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert "include CHANGELOG.md" in manifest
    assert "recursive-include docs *.md" in manifest
    assert "recursive-include examples *.yaml *.csv" in manifest
    assert "recursive-include scripts *.sh" in manifest
