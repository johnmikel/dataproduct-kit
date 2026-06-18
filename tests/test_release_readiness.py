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


def test_smoke_install_script_checks_built_wheel() -> None:
    script = ROOT / "scripts/smoke-install.sh"

    assert script.exists()
    assert os.access(script, os.X_OK)
    text = script.read_text(encoding="utf-8")
    assert "python -m venv" in text
    assert "pip install" in text
    assert "dataproduct-kit --help" in text
    assert "dataproduct-kit schema all" in text
    assert "dataproduct-kit ci examples/pass" in text


def test_manifest_includes_docs_examples_and_scripts_in_sdist() -> None:
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert "include CHANGELOG.md" in manifest
    assert "include action.yml" in manifest
    assert "include dataproduct-kit.toml" in manifest
    assert "recursive-include docs *.md" in manifest
    assert "recursive-include examples *.yaml *.csv" in manifest
    assert "recursive-include scripts *.sh" in manifest


def test_ci_adoption_docs_and_finding_codes_are_present() -> None:
    ci_docs = (ROOT / "docs/ci-adoption.md").read_text(encoding="utf-8")
    finding_docs = (ROOT / "docs/finding-codes.md").read_text(encoding="utf-8")
    suppression_docs = (ROOT / "docs/suppressions.md").read_text(encoding="utf-8")

    assert "dataproduct-kit ci" in ci_docs
    assert "johnmikel/dataproduct-kit@v0.4.0" in ci_docs
    assert "github/codeql-action/upload-sarif@v4" in ci_docs
    assert "schema.missing_column" in finding_docs
    assert "freshness.stale" in finding_docs
    assert "policy.unknown_sensitive_field" in finding_docs
    assert "suppression.unused" in finding_docs
    assert "[[suppressions]]" in suppression_docs
    assert "expires" in suppression_docs
    assert "unused" in suppression_docs


def test_compatibility_and_ci_rollout_docs_are_present() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    compatibility = (ROOT / "docs/compatibility.md").read_text(encoding="utf-8")
    rollout = (ROOT / "docs/ci-rollout.md").read_text(encoding="utf-8")

    assert "docs/compatibility.md" in readme
    assert "docs/ci-rollout.md" in readme
    assert "stable CLI" in compatibility
    assert "stable config" in compatibility
    assert "evolving manifests" in compatibility
    assert "observe mode" in rollout
    assert "fail-only gate" in rollout
    assert "warn gate" in rollout
    assert "suppression cleanup" in rollout


def test_ci_workflow_uses_node24_action_versions() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "actions/checkout@v5" in workflow
    assert "actions/setup-python@v6" in workflow


def test_dogfood_action_workflow_uses_local_action_and_sarif() -> None:
    workflow = (ROOT / ".github/workflows/dataproduct-kit-dogfood.yml").read_text(
        encoding="utf-8"
    )

    assert "uses: ./" in workflow
    assert "path: examples/pass" in workflow
    assert "sarif: dataproduct-kit-dogfood.sarif.json" in workflow
    assert "github/codeql-action/upload-sarif@v4" in workflow


def test_release_smoke_workflow_builds_and_installs_wheel() -> None:
    workflow = (ROOT / ".github/workflows/release-smoke.yml").read_text(encoding="utf-8")

    assert "python -m build" in workflow
    assert "./scripts/smoke-install.sh dist/dataproduct_kit-" in workflow


def test_publish_workflow_uses_trusted_publishing() -> None:
    workflow = (ROOT / ".github/workflows/publish.yml").read_text(encoding="utf-8")

    assert "release:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "target:" in workflow
    assert "type: choice" in workflow
    assert "- testpypi" in workflow
    assert "- pypi" in workflow
    assert "id-token: write" in workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
    assert "repository-url: https://test.pypi.org/legacy/" in workflow
    assert "environment:" in workflow


def test_publish_workflow_can_dry_run_testpypi_without_pypi() -> None:
    workflow = (ROOT / ".github/workflows/publish.yml").read_text(encoding="utf-8")

    assert (
        "if: ${{ github.event_name == 'release' || inputs.target == 'testpypi' "
        "|| inputs.target == 'pypi' }}"
    ) in workflow
    assert "if: ${{ github.event_name == 'release' || inputs.target == 'pypi' }}" in workflow
    assert "needs: publish-testpypi" in workflow


def test_issue_templates_exist_for_public_contributors() -> None:
    templates = ROOT / ".github/ISSUE_TEMPLATE"

    assert (templates / "bug_report.yml").exists()
    assert (templates / "feature_request.yml").exists()
    assert (templates / "data_product_example.yml").exists()


def test_trusted_publishing_docs_cover_setup_and_dry_run() -> None:
    docs = (ROOT / "docs/publishing.md").read_text(encoding="utf-8")

    assert ".github/workflows/publish.yml" in docs
    assert "testpypi" in docs
    assert "pypi" in docs
    assert "id-token: write" in docs
    assert "repository-url: https://test.pypi.org/legacy/" in docs
    assert "No PyPI API token" in docs
    assert "workflow_dispatch" in docs
    assert "target: testpypi" in docs
    assert "TestPyPI dry run" in docs


def test_release_checklist_documents_v040_cut_steps() -> None:
    docs = (ROOT / "docs/release-checklist.md").read_text(encoding="utf-8")

    assert "git checkout main" in docs
    assert "git status --short --branch" in docs
    assert "./scripts/verify.sh" in docs
    assert "v0.4.0 - 2026-06-17" in docs
    assert "git tag -a v0.4.0" in docs
    assert "git push origin v0.4.0" in docs
    assert "target: testpypi" in docs
    assert "GitHub Release" in docs
    assert ".github/workflows/publish.yml" in docs
