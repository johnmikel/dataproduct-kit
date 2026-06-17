from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]


def test_passing_example_validates() -> None:
    from dataproduct_kit.cli import app

    result = CliRunner().invoke(app, ["validate", str(ROOT / "examples/pass/saas-churn")])

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
