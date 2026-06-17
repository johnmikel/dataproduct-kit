from __future__ import annotations

import json
from pathlib import Path

from conftest import write_valid_project
from typer.testing import CliRunner


def test_cli_init_validate_report_context_export_and_emit(tmp_path: Path) -> None:
    from dataproduct_kit.cli import app

    runner = CliRunner()
    project_dir = tmp_path / "demo"

    init_result = runner.invoke(app, ["init", str(project_dir), "--template", "saas-churn"])
    assert init_result.exit_code == 0, init_result.output
    assert (project_dir / "dataproduct.yaml").exists()
    assert (project_dir / "data/subscriptions.csv").exists()

    validate_result = runner.invoke(app, ["validate", str(project_dir)])
    assert validate_result.exit_code == 0, validate_result.output
    assert "status: pass" in validate_result.output

    report_result = runner.invoke(app, ["report", str(project_dir), "--format", "json"])
    assert report_result.exit_code == 0, report_result.output
    assert json.loads(report_result.output)["status"] == "pass"

    markdown_result = runner.invoke(app, ["report", str(project_dir), "--format", "markdown"])
    assert markdown_result.exit_code == 0, markdown_result.output
    assert "# Trust Report: SaaS Churn Data Product" in markdown_result.output

    context_result = runner.invoke(
        app,
        ["context", str(project_dir), "--metric", "churn_rate", "--format", "json"],
    )
    assert context_result.exit_code == 0, context_result.output
    assert json.loads(context_result.output)["metric"]["name"] == "churn_rate"

    odcs_result = runner.invoke(app, ["export", "odcs", str(project_dir)])
    assert odcs_result.exit_code == 0, odcs_result.output
    assert json.loads(odcs_result.output)["kind"] == "DataContract"

    osi_result = runner.invoke(app, ["export", "osi", str(project_dir)])
    assert osi_result.exit_code == 0, osi_result.output
    assert json.loads(osi_result.output)["kind"] == "SemanticModel"

    emit_result = runner.invoke(app, ["emit", "openlineage", str(project_dir)])
    assert emit_result.exit_code == 0, emit_result.output
    assert (project_dir / ".dataproduct-kit/openlineage.jsonl").exists()


def test_cli_validate_returns_nonzero_for_failed_project(tmp_path: Path) -> None:
    from dataproduct_kit.cli import app

    runner = CliRunner()
    write_valid_project(tmp_path)
    csv = (tmp_path / "data/subscriptions.csv").read_text(encoding="utf-8")
    (tmp_path / "data/subscriptions.csv").write_text(
        csv.replace("cust_005", ""),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["validate", str(tmp_path)])

    assert result.exit_code == 1
    assert "status: fail" in result.output
    assert "quality.not_null" in result.output
