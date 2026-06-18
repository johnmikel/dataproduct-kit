from __future__ import annotations

import json
from pathlib import Path

import yaml
from conftest import write_valid_project
from typer.testing import CliRunner


def test_validate_suite_discovers_products_and_summarizes_status(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    passing = tmp_path / "products/pass"
    failing = tmp_path / "products/fail"
    write_valid_project(passing)
    write_valid_project(failing)
    _remove_mrr_column(failing)

    suite = validate_suite(tmp_path)

    assert suite.status == "fail"
    assert suite.summary == {
        "products_total": 2,
        "products_passed": 1,
        "products_warned": 0,
        "products_failed": 1,
        "findings_total": 1,
        "findings_suppressed": 0,
    }
    assert [product.path for product in suite.products] == ["products/fail", "products/pass"]
    failed_product = suite.products[0]
    assert failed_product.product_id == "saas_churn"
    assert failed_product.status == "fail"
    assert [finding.code for finding in failed_product.findings] == ["schema.missing_column"]


def test_validate_suite_reports_no_products(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    suite = validate_suite(tmp_path)

    assert suite.status == "fail"
    assert suite.summary["products_total"] == 0
    assert suite.findings[0].code == "discovery.no_products"
    assert suite.findings[0].message == "no dataproduct.yaml files found"


def test_github_annotations_point_findings_to_manifest_files(tmp_path: Path) -> None:
    from dataproduct_kit.ci import render_github_annotations
    from dataproduct_kit.suite import validate_suite

    failing = tmp_path / "products/fail"
    write_valid_project(failing)
    _remove_mrr_column(failing)

    output = render_github_annotations(validate_suite(tmp_path))

    assert "::error file=products/fail/contract.yaml,line=" in output
    assert "title=schema.missing_column::" in output
    assert "required column 'monthly_recurring_revenue' is missing" in output


def test_sarif_report_contains_rules_results_and_locations(tmp_path: Path) -> None:
    from dataproduct_kit.ci import render_sarif_report
    from dataproduct_kit.suite import validate_suite

    failing = tmp_path / "products/fail"
    write_valid_project(failing)
    _remove_mrr_column(failing)

    payload = render_sarif_report(validate_suite(tmp_path))

    assert payload["version"] == "2.1.0"
    rules = payload["runs"][0]["tool"]["driver"]["rules"]
    assert rules == [
        {
            "id": "schema.missing_column",
            "name": "schema.missing_column",
            "shortDescription": {"text": "schema.missing_column"},
        }
    ]
    result = payload["runs"][0]["results"][0]
    assert result["ruleId"] == "schema.missing_column"
    assert result["level"] == "error"
    assert result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == (
        "products/fail/contract.yaml"
    )
    assert result["locations"][0]["physicalLocation"]["region"]["startLine"] > 0


def test_cli_ci_outputs_json_github_annotations_and_sarif(tmp_path: Path) -> None:
    from dataproduct_kit.cli import app

    runner = CliRunner()
    failing = tmp_path / "products/fail"
    write_valid_project(failing)
    _remove_mrr_column(failing)

    json_result = runner.invoke(app, ["ci", str(tmp_path), "--format", "json"])

    assert json_result.exit_code == 1
    payload = json.loads(json_result.output)
    assert payload["status"] == "fail"
    assert payload["products"][0]["path"] == "products/fail"

    sarif_path = tmp_path / "dataproduct-kit.sarif.json"
    github_result = runner.invoke(
        app,
        [
            "ci",
            str(tmp_path),
            "--format",
            "github",
            "--sarif",
            str(sarif_path),
        ],
    )

    assert github_result.exit_code == 1
    assert "::error file=products/fail/contract.yaml,line=" in (
        github_result.output
    )
    assert "title=schema.missing_column::" in github_result.output
    sarif_payload = json.loads(sarif_path.read_text(encoding="utf-8"))
    assert sarif_payload["version"] == "2.1.0"
    assert (
        sarif_payload["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"][
            "startLine"
        ]
        > 0
    )


def test_cli_ci_fail_on_warn_exits_nonzero_for_warning_suite(tmp_path: Path) -> None:
    from dataproduct_kit.cli import app

    runner = CliRunner()
    write_valid_project(tmp_path / "products/warn")
    text = (tmp_path / "products/warn/dataproduct.yaml").read_text(encoding="utf-8")
    (tmp_path / "products/warn/dataproduct.yaml").write_text(
        text.replace(
            "    freshness:\n"
            "      column: updated_at\n"
            "      max_age_hours: 48\n"
            '      reference_time: "2026-06-17T00:00:00Z"\n',
            "",
        ),
        encoding="utf-8",
    )

    default_result = runner.invoke(app, ["ci", str(tmp_path)])
    strict_result = runner.invoke(app, ["ci", str(tmp_path), "--fail-on", "warn"])

    assert default_result.exit_code == 0
    assert "status: warn" in default_result.output
    assert strict_result.exit_code == 1
    assert "freshness.missing" in strict_result.output


def test_action_metadata_runs_ci_command() -> None:
    action = yaml.safe_load(Path("action.yml").read_text(encoding="utf-8"))

    assert action["runs"]["using"] == "composite"
    assert action["inputs"]["path"]["default"] == "."
    assert action["inputs"]["fail-on"]["default"] == "fail"
    assert any(step.get("uses") == "actions/setup-python@v6" for step in action["runs"]["steps"])
    commands = "\n".join(step.get("run", "") for step in action["runs"]["steps"])
    assert 'python -m pip install "${{ github.action_path }}"' in commands
    assert 'dataproduct-kit ci "${{ inputs.path }}"' in commands
    assert '--format "${{ inputs.format }}"' in commands
    assert '--sarif "${{ inputs.sarif }}"' in commands


def _remove_mrr_column(project_dir: Path) -> None:
    (project_dir / "data/subscriptions.csv").write_text(
        "\n".join(
            [
                "customer_id,plan,status,churned,updated_at",
                "cust_001,pro,active,false,2026-06-16T09:00:00Z",
                "cust_002,pro,canceled,true,2026-06-16T09:30:00Z",
                "cust_003,business,active,false,2026-06-16T10:00:00Z",
                "cust_004,business,canceled,true,2026-06-16T10:30:00Z",
                "cust_005,starter,active,false,2026-06-16T11:00:00Z",
                "",
            ]
        ),
        encoding="utf-8",
    )
