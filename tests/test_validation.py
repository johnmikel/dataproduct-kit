from __future__ import annotations

from pathlib import Path

import pytest
from conftest import write_text, write_valid_project


def test_valid_project_passes_and_returns_trust_context(tmp_path: Path) -> None:
    from dataproduct_kit.loader import load_project
    from dataproduct_kit.validators import validate_project

    project = load_project(write_valid_project(tmp_path))
    report = validate_project(project)

    assert report.status == "pass"
    assert report.product_id == "saas_churn"
    assert report.summary["checks_failed"] == 0
    assert report.semantic.metrics[0].name == "churn_rate"
    assert report.freshness[0].status == "pass"


def test_missing_owner_fails_with_deterministic_message(tmp_path: Path) -> None:
    from dataproduct_kit.loader import ManifestLoadError, load_project

    write_valid_project(tmp_path)
    text = (tmp_path / "dataproduct.yaml").read_text(encoding="utf-8")
    (tmp_path / "dataproduct.yaml").write_text(
        text.replace(
            "owner:\n"
            "  name: Growth Analytics\n"
            "  email: growth-analytics@example.com\n"
            "  team: Growth\n",
            "",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ManifestLoadError) as error:
        load_project(tmp_path)

    assert "dataproduct.yaml: owner: Field required" in str(error.value)


def test_invalid_yaml_reports_file_and_parser_error(tmp_path: Path) -> None:
    from dataproduct_kit.loader import ManifestLoadError, load_project

    write_valid_project(tmp_path)
    write_text(tmp_path / "semantic.yaml", "metrics:\n  - name: broken\n    expression: [\n")

    with pytest.raises(ManifestLoadError) as error:
        load_project(tmp_path)

    assert "semantic.yaml:" in str(error.value)
    assert "YAML parse error" in str(error.value)


def test_schema_mismatch_fails_when_required_column_missing(tmp_path: Path) -> None:
    from dataproduct_kit.loader import load_project
    from dataproduct_kit.validators import validate_project

    write_valid_project(tmp_path)
    write_text(
        tmp_path / "data/subscriptions.csv",
        """
        customer_id,plan,status,churned,updated_at
        cust_001,pro,active,false,2026-06-16T09:00:00Z
        """,
    )

    report = validate_project(load_project(tmp_path))

    assert report.status == "fail"
    assert "schema.missing_column" in [finding.code for finding in report.findings]
    assert "monthly_recurring_revenue" in "\n".join(f.message for f in report.findings)


def test_not_null_quality_failure_is_reported(tmp_path: Path) -> None:
    from dataproduct_kit.loader import load_project
    from dataproduct_kit.validators import validate_project

    write_valid_project(tmp_path)
    write_text(
        tmp_path / "data/subscriptions.csv",
        """
        customer_id,plan,status,churned,monthly_recurring_revenue,updated_at
        ,pro,active,false,99.0,2026-06-16T09:00:00Z
        cust_002,pro,canceled,true,99.0,2026-06-16T09:30:00Z
        cust_003,business,active,false,299.0,2026-06-16T10:00:00Z
        cust_004,business,canceled,true,299.0,2026-06-16T10:30:00Z
        cust_005,starter,active,false,29.0,2026-06-16T11:00:00Z
        """,
    )

    report = validate_project(load_project(tmp_path))

    assert report.status == "fail"
    assert any(
        f.code == "quality.not_null" and f.check == "customer_id_not_null"
        for f in report.findings
    )


def test_accepted_values_quality_failure_is_reported(tmp_path: Path) -> None:
    from dataproduct_kit.loader import load_project
    from dataproduct_kit.validators import validate_project

    write_valid_project(tmp_path)
    csv = (tmp_path / "data/subscriptions.csv").read_text(encoding="utf-8")
    (tmp_path / "data/subscriptions.csv").write_text(
        csv.replace("cust_003,business,active,false", "cust_003,business,paused,false"),
        encoding="utf-8",
    )

    report = validate_project(load_project(tmp_path))

    assert report.status == "fail"
    assert any(
        f.code == "quality.accepted_values" and "paused" in f.message
        for f in report.findings
    )


def test_stale_freshness_fails(tmp_path: Path) -> None:
    from dataproduct_kit.loader import load_project
    from dataproduct_kit.validators import validate_project

    write_valid_project(tmp_path)
    csv = (tmp_path / "data/subscriptions.csv").read_text(encoding="utf-8")
    (tmp_path / "data/subscriptions.csv").write_text(
        csv.replace("2026-06-16", "2026-06-10"),
        encoding="utf-8",
    )

    report = validate_project(load_project(tmp_path))

    assert report.status == "fail"
    assert any(f.code == "freshness.stale" for f in report.findings)


def test_broken_semantic_reference_fails(tmp_path: Path) -> None:
    from dataproduct_kit.loader import load_project
    from dataproduct_kit.validators import validate_project

    write_valid_project(tmp_path)
    semantic = (tmp_path / "semantic.yaml").read_text(encoding="utf-8")
    (tmp_path / "semantic.yaml").write_text(
        semantic.replace("dimensions: [plan]", "dimensions: [region]"),
        encoding="utf-8",
    )

    report = validate_project(load_project(tmp_path))

    assert report.status == "fail"
    assert any(f.code == "semantic.unknown_dimension" for f in report.findings)
