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


def test_cli_validate_json_returns_machine_readable_report(tmp_path: Path) -> None:
    from dataproduct_kit.cli import app

    runner = CliRunner()
    write_valid_project(tmp_path)

    result = runner.invoke(app, ["validate", str(tmp_path), "--format", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "pass"
    assert payload["summary"]["checks_failed"] == 0
    assert payload["product_id"] == "saas_churn"


def test_cli_validate_fail_on_warn_returns_nonzero_for_warning_project(tmp_path: Path) -> None:
    from dataproduct_kit.cli import app

    runner = CliRunner()
    write_valid_project(tmp_path)
    text = (tmp_path / "dataproduct.yaml").read_text(encoding="utf-8")
    (tmp_path / "dataproduct.yaml").write_text(
        text.replace(
            "    freshness:\n"
            "      column: updated_at\n"
            "      max_age_hours: 48\n"
            '      reference_time: "2026-06-17T00:00:00Z"\n',
            "",
        ),
        encoding="utf-8",
    )

    default_result = runner.invoke(app, ["validate", str(tmp_path)])
    strict_result = runner.invoke(app, ["validate", str(tmp_path), "--fail-on", "warn"])

    assert default_result.exit_code == 0, default_result.output
    assert "status: warn" in default_result.output
    assert strict_result.exit_code == 1
    assert "freshness.missing" in strict_result.output


def test_cli_schema_prints_single_schema_and_writes_all(tmp_path: Path) -> None:
    from dataproduct_kit.cli import app

    runner = CliRunner()

    single_result = runner.invoke(app, ["schema", "dataproduct"])
    assert single_result.exit_code == 0, single_result.output
    single_schema = json.loads(single_result.output)
    assert single_schema["title"] == "DataProductManifest"
    assert "owner" in single_schema["required"]

    out_dir = tmp_path / "schemas"
    all_result = runner.invoke(app, ["schema", "all", "--out", str(out_dir)])

    assert all_result.exit_code == 0, all_result.output
    assert json.loads((out_dir / "dataproduct.schema.json").read_text())["type"] == "object"
    assert json.loads((out_dir / "contract.schema.json").read_text())["title"] == "ContractManifest"
    assert json.loads((out_dir / "semantic.schema.json").read_text())["title"] == "SemanticManifest"
    assert json.loads((out_dir / "policy.schema.json").read_text())["title"] == "PolicyManifest"


def test_cli_export_out_writes_file_without_breaking_stdout_default(tmp_path: Path) -> None:
    from dataproduct_kit.cli import app

    runner = CliRunner()
    write_valid_project(tmp_path)
    output = tmp_path / "contract.json"

    result = runner.invoke(app, ["export", "odcs", str(tmp_path), "--out", str(output)])

    assert result.exit_code == 0, result.output
    assert str(output) in result.output
    assert json.loads(output.read_text(encoding="utf-8"))["kind"] == "DataContract"

    stdout_result = runner.invoke(app, ["export", "osi", str(tmp_path)])
    assert stdout_result.exit_code == 0, stdout_result.output
    assert json.loads(stdout_result.output)["kind"] == "SemanticModel"
