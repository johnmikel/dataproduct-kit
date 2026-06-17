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
    assert "include action.yml" in manifest
    assert "recursive-include docs *.md" in manifest
    assert "recursive-include examples *.yaml *.csv" in manifest
    assert "recursive-include scripts *.sh" in manifest


def test_ci_adoption_docs_and_finding_codes_are_present() -> None:
    ci_docs = (ROOT / "docs/ci-adoption.md").read_text(encoding="utf-8")
    finding_docs = (ROOT / "docs/finding-codes.md").read_text(encoding="utf-8")

    assert "dataproduct-kit ci" in ci_docs
    assert "johnmikel/dataproduct-kit@v0.3.0" in ci_docs
    assert "github/codeql-action/upload-sarif@v4" in ci_docs
    assert "schema.missing_column" in finding_docs
    assert "freshness.stale" in finding_docs
    assert "policy.unknown_sensitive_field" in finding_docs


def test_ci_workflow_uses_node24_action_versions() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "actions/checkout@v5" in workflow
    assert "actions/setup-python@v6" in workflow
