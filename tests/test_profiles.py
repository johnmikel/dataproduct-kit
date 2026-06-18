from __future__ import annotations

from pathlib import Path

from conftest import write_valid_project


def test_starter_warns_for_missing_agent_constraints(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    project_dir = tmp_path / "products/customers"
    write_valid_project(project_dir)
    policy = (project_dir / "policy.yaml").read_text(encoding="utf-8")
    (project_dir / "policy.yaml").write_text(
        policy.replace(
            "agent_constraints:\n"
            "  - Agents may use the approved churn_rate metric only.\n"
            "  - Agents must include freshness and quality status with answers.\n",
            "agent_constraints: []\n",
        ),
        encoding="utf-8",
    )

    suite = validate_suite(tmp_path, profile_override="starter")

    assert suite.status == "warn"
    assert suite.products[0].status == "warn"
    assert any(
        finding.code == "profile.agent_constraints_missing"
        and finding.level == "warning"
        for finding in suite.products[0].findings
    )


def test_production_blocks_missing_agent_constraints(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    project_dir = tmp_path / "products/customers"
    write_valid_project(project_dir)
    policy = (project_dir / "policy.yaml").read_text(encoding="utf-8")
    (project_dir / "policy.yaml").write_text(
        policy.replace(
            "agent_constraints:\n"
            "  - Agents may use the approved churn_rate metric only.\n"
            "  - Agents must include freshness and quality status with answers.\n",
            "agent_constraints: []\n",
        ),
        encoding="utf-8",
    )

    suite = validate_suite(tmp_path, profile_override="production")

    assert suite.status == "fail"
    assert any(
        finding.code == "profile.agent_constraints_missing"
        and finding.level == "error"
        for finding in suite.products[0].findings
    )


def test_regulated_blocks_unsuppressed_warnings(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    project_dir = tmp_path / "products/warn"
    write_valid_project(project_dir)
    text = (project_dir / "dataproduct.yaml").read_text(encoding="utf-8")
    (project_dir / "dataproduct.yaml").write_text(
        text.replace(
            "    freshness:\n"
            "      column: updated_at\n"
            "      max_age_hours: 48\n"
            "      reference_time: \"2026-06-17T00:00:00Z\"\n",
            "",
        ),
        encoding="utf-8",
    )

    suite = validate_suite(tmp_path, profile_override="regulated")

    assert suite.status == "fail"
    assert any(finding.code == "profile.unsuppressed_warning" for finding in suite.findings)
