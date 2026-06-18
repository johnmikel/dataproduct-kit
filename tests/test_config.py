from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import write_text, write_valid_project
from typer.testing import CliRunner


def test_config_accepts_ci_profile(tmp_path: Path) -> None:
    from dataproduct_kit.config import load_config

    (tmp_path / "dataproduct-kit.toml").write_text(
        "[ci]\nprofile = \"production\"\nfail_on = \"warn\"\n",
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    assert config.ci.profile == "production"
    assert config.ci.fail_on == "warn"


def test_config_rejects_unknown_ci_profile(tmp_path: Path) -> None:
    from dataproduct_kit.config import ConfigLoadError, load_config

    (tmp_path / "dataproduct-kit.toml").write_text(
        "[ci]\nprofile = \"anything\"\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigLoadError) as error:
        load_config(tmp_path)

    assert "ci.profile" in str(error.value)


def test_validate_suite_rejects_unknown_profile_override(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    write_valid_project(tmp_path / "data-products/pass")

    suite = validate_suite(tmp_path, profile_override="not-real")

    assert suite.status == "fail"
    assert suite.profile == "starter"
    assert suite.config["profile"] == "starter"
    assert suite.findings[0].code == "config.invalid"
    assert "ci.profile" in suite.findings[0].message


def test_ci_config_filters_discovered_products(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    write_valid_project(tmp_path / "data-products/include-me")
    write_valid_project(tmp_path / "data-products/skip-me")
    _remove_mrr_column(tmp_path / "data-products/skip-me")
    write_text(
        tmp_path / "dataproduct-kit.toml",
        """
        [ci]
        include = ["data-products/**"]
        exclude = ["data-products/skip-me"]
        fail_on = "warn"
        """,
    )

    suite = validate_suite(tmp_path)

    assert suite.status == "pass"
    assert suite.summary["products_total"] == 1
    assert [product.path for product in suite.products] == ["data-products/include-me"]
    assert suite.config["fail_on"] == "warn"


def test_ci_config_accepts_profile(tmp_path: Path) -> None:
    from dataproduct_kit.config import load_config

    write_text(
        tmp_path / "dataproduct-kit.toml",
        """
        [ci]
        profile = "production"
        fail_on = "warn"
        """,
    )

    config = load_config(tmp_path)

    assert config.ci.profile == "production"
    assert config.ci.fail_on == "warn"


def test_ci_config_rejects_unknown_profile(tmp_path: Path) -> None:
    from dataproduct_kit.config import ConfigLoadError, load_config

    write_text(
        tmp_path / "dataproduct-kit.toml",
        """
        [ci]
        profile = "anything"
        """,
    )

    with pytest.raises(ConfigLoadError) as error:
        load_config(tmp_path)

    assert "ci.profile" in str(error.value)


def test_active_suppression_marks_finding_and_changes_effective_status(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    project = tmp_path / "data-products/schema-drift"
    write_valid_project(project)
    _remove_mrr_column(project)
    write_text(
        tmp_path / "dataproduct-kit.toml",
        """
        [[suppressions]]
        code = "schema.missing_column"
        path = "data-products/schema-drift"
        reason = "Producer migration is scheduled in the next sprint."
        expires = "2999-01-01"
        """,
    )

    suite = validate_suite(tmp_path)

    assert suite.status == "pass"
    assert suite.summary["findings_total"] == 1
    assert suite.summary["findings_suppressed"] == 1
    product = suite.products[0]
    assert product.status == "pass"
    finding = product.findings[0]
    assert finding.code == "schema.missing_column"
    assert finding.suppressed is True
    assert finding.suppression_reason == "Producer migration is scheduled in the next sprint."
    assert finding.suppression_expires == "2999-01-01"


def test_unused_active_suppression_warns_without_failing_product(tmp_path: Path) -> None:
    from dataproduct_kit.ci import render_github_annotations
    from dataproduct_kit.suite import validate_suite

    write_valid_project(tmp_path / "data-products/pass")
    write_text(
        tmp_path / "dataproduct-kit.toml",
        """
        [[suppressions]]
        code = "schema.missing_column"
        path = "data-products/pass"
        reason = "This migration has already landed and the suppression should be removed."
        expires = "2999-01-01"
        """,
    )

    suite = validate_suite(tmp_path)

    assert suite.status == "warn"
    assert suite.summary["products_passed"] == 1
    assert suite.summary["products_warned"] == 0
    assert suite.summary["findings_total"] == 1
    assert suite.findings[0].code == "suppression.unused"
    assert suite.findings[0].level == "warning"
    assert "schema.missing_column" in suite.findings[0].message
    assert suite.products[0].status == "pass"

    annotations = render_github_annotations(suite)
    assert "::warning file=dataproduct-kit.toml,line=" in annotations
    assert "suppression.unused" in annotations


def test_expired_suppression_fails_suite_and_does_not_suppress_finding(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    project = tmp_path / "data-products/schema-drift"
    write_valid_project(project)
    _remove_mrr_column(project)
    write_text(
        tmp_path / "dataproduct-kit.toml",
        """
        [[suppressions]]
        code = "schema.missing_column"
        path = "data-products/schema-drift"
        reason = "This should have been fixed already."
        expires = "2000-01-01"
        """,
    )

    suite = validate_suite(tmp_path)

    assert suite.status == "fail"
    assert any(finding.code == "suppression.expired" for finding in suite.findings)
    assert suite.products[0].findings[0].suppressed is False


def test_unknown_suppression_code_fails_suite(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    write_valid_project(tmp_path / "data-products/pass")
    write_text(
        tmp_path / "dataproduct-kit.toml",
        """
        [[suppressions]]
        code = "schema.typo"
        path = "data-products/pass"
        reason = "Typo should be rejected."
        expires = "2999-01-01"
        """,
    )

    suite = validate_suite(tmp_path)

    assert suite.status == "fail"
    assert suite.findings[0].code == "suppression.unknown_code"
    assert "schema.typo" in suite.findings[0].message


def test_sarif_marks_suppressed_results(tmp_path: Path) -> None:
    from dataproduct_kit.ci import render_sarif_report
    from dataproduct_kit.suite import validate_suite

    project = tmp_path / "data-products/schema-drift"
    write_valid_project(project)
    _remove_mrr_column(project)
    write_text(
        tmp_path / "dataproduct-kit.toml",
        """
        [[suppressions]]
        code = "schema.missing_column"
        path = "data-products/schema-drift"
        reason = "Accepted temporarily by data product owner."
        expires = "2999-01-01"
        """,
    )

    payload = render_sarif_report(validate_suite(tmp_path))
    result = payload["runs"][0]["results"][0]

    assert result["ruleId"] == "schema.missing_column"
    assert result["suppressions"] == [
        {
            "kind": "external",
            "justification": "Accepted temporarily by data product owner. Expires 2999-01-01.",
        }
    ]


def test_cli_ci_uses_config_fail_on_default(tmp_path: Path) -> None:
    from dataproduct_kit.cli import app

    runner = CliRunner()
    write_valid_project(tmp_path / "data-products/warn")
    text = (tmp_path / "data-products/warn/dataproduct.yaml").read_text(encoding="utf-8")
    (tmp_path / "data-products/warn/dataproduct.yaml").write_text(
        text.replace(
            "    freshness:\n"
            "      column: updated_at\n"
            "      max_age_hours: 48\n"
            '      reference_time: "2026-06-17T00:00:00Z"\n',
            "",
        ),
        encoding="utf-8",
    )
    write_text(
        tmp_path / "dataproduct-kit.toml",
        """
        [ci]
        fail_on = "warn"
        """,
    )

    result = runner.invoke(app, ["ci", str(tmp_path), "--format", "json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "warn"
    assert payload["config"]["fail_on"] == "warn"


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
