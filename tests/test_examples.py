from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]


def test_passing_examples_validate() -> None:
    from dataproduct_kit.cli import app

    expected_examples = {"saas-churn", "finance-revenue", "healthcare-appointments"}
    example_dirs = {
        path.name
        for path in (ROOT / "examples/pass").iterdir()
        if path.is_dir() and (path / "dataproduct.yaml").exists()
    }

    assert expected_examples <= example_dirs

    runner = CliRunner()
    for example in sorted(example_dirs):
        result = runner.invoke(app, ["validate", str(ROOT / f"examples/pass/{example}")])

        assert result.exit_code == 0, result.output
        assert "status: pass" in result.output


def test_failing_examples_fail_for_expected_primary_reason() -> None:
    from dataproduct_kit.cli import app

    cases = {
        "schema-drift": "schema.missing_column",
        "stale-data": "freshness.stale",
        "broken-metric": "semantic.unknown_dimension",
        "policy-gap": "policy.unknown_sensitive_field",
    }
    runner = CliRunner()

    for example, expected_code in cases.items():
        result = runner.invoke(app, ["validate", str(ROOT / f"examples/fail/{example}")])

        assert result.exit_code == 1, result.output
        assert "status: fail" in result.output
        assert expected_code in result.output
