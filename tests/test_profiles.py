from __future__ import annotations

from pathlib import Path

from conftest import write_text, write_valid_project


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


def test_regulated_blocks_unused_suppression_warning(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    write_valid_project(tmp_path / "products/pass")
    write_text(
        tmp_path / "dataproduct-kit.toml",
        """
        [[suppressions]]
        code = "schema.missing_column"
        path = "products/pass"
        reason = "This migration has already landed and the suppression should be removed."
        expires = "2999-01-01"
        """,
    )

    suite = validate_suite(tmp_path, profile_override="regulated")

    assert suite.status == "fail"
    unused = _finding(suite.findings, "suppression.unused")
    blocker = _finding(suite.findings, "profile.unsuppressed_warning")
    assert unused.level == "warning"
    assert unused.line is not None
    assert blocker.level == "error"
    assert blocker.line is not None


def test_regulated_blocks_unused_suppression_warning_without_products(
    tmp_path: Path,
) -> None:
    from dataproduct_kit.suite import validate_suite

    write_text(
        tmp_path / "dataproduct-kit.toml",
        """
        [[suppressions]]
        code = "schema.missing_column"
        path = "products/pass"
        reason = "This migration has already landed and the suppression should be removed."
        expires = "2999-01-01"
        """,
    )

    suite = validate_suite(tmp_path, profile_override="regulated")

    assert suite.status == "fail"
    assert _finding(suite.findings, "discovery.no_products").level == "error"
    assert _finding(suite.findings, "suppression.unused").level == "warning"
    assert _finding(suite.findings, "profile.unsuppressed_warning").level == "error"


def test_regulated_treats_placeholder_classifications_as_missing(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    project_dir = tmp_path / "products/customers"
    write_valid_project(project_dir)
    contract = (project_dir / "contract.yaml").read_text(encoding="utf-8")
    for classification in ["internal", "public", "confidential"]:
        contract = contract.replace(
            f"classification: {classification}",
            "classification: TODO",
        )
    (project_dir / "contract.yaml").write_text(contract, encoding="utf-8")

    suite = validate_suite(tmp_path, profile_override="regulated")

    assert suite.status == "fail"
    finding = _finding(suite.products[0].findings, "profile.classification_missing")
    assert finding.level == "error"
    assert "customer_id" in finding.message


def test_agent_constraints_profile_finding_maps_to_policy_yaml(tmp_path: Path) -> None:
    from dataproduct_kit.ci import render_github_annotations
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

    finding = _finding(suite.products[0].findings, "profile.agent_constraints_missing")
    assert finding.line is not None
    assert "::warning file=products/customers/policy.yaml,line=" in render_github_annotations(suite)


def test_quality_checks_profile_finding_maps_to_contract_yaml(tmp_path: Path) -> None:
    from dataproduct_kit.ci import render_github_annotations
    from dataproduct_kit.suite import validate_suite

    project_dir = tmp_path / "products/customers"
    write_valid_project(project_dir)
    contract = (project_dir / "contract.yaml").read_text(encoding="utf-8")
    (project_dir / "contract.yaml").write_text(
        contract.replace(
            "quality_checks:\n"
            "  - name: customer_id_not_null\n"
            "    type: not_null\n"
            "    column: customer_id\n"
            "  - name: customer_id_unique\n"
            "    type: unique\n"
            "    column: customer_id\n"
            "  - name: status_values\n"
            "    type: accepted_values\n"
            "    column: status\n"
            "    values: [\"active\", \"canceled\"]\n"
            "  - name: positive_mrr\n"
            "    type: min\n"
            "    column: monthly_recurring_revenue\n"
            "    value: 0\n"
            "  - name: enough_rows\n"
            "    type: row_count_min\n"
            "    value: 5\n",
            "quality_checks: []\n",
        ),
        encoding="utf-8",
    )

    suite = validate_suite(tmp_path, profile_override="starter")

    finding = _finding(suite.products[0].findings, "profile.quality_checks_missing")
    assert finding.line is not None
    assert (
        "::warning file=products/customers/contract.yaml,line="
        in render_github_annotations(suite)
    )


def test_semantic_metrics_profile_finding_maps_to_semantic_yaml(tmp_path: Path) -> None:
    from dataproduct_kit.ci import render_github_annotations
    from dataproduct_kit.suite import validate_suite

    project_dir = tmp_path / "products/customers"
    write_valid_project(project_dir)
    semantic = (project_dir / "semantic.yaml").read_text(encoding="utf-8")
    (project_dir / "semantic.yaml").write_text(
        semantic.replace(
            "metrics:\n"
            "  - name: churn_rate\n"
            "    label: Churn Rate\n"
            "    description: Share of subscriptions that churned during the reporting grain.\n"
            "    dataset: subscriptions\n"
            '    expression: "sum(case when churned then 1 else 0 end)::double / '
            'nullif(count(*), 0)"\n'
            "    grain: month\n"
            "    dimensions: [plan]\n",
            "metrics: []\n",
        ),
        encoding="utf-8",
    )

    suite = validate_suite(tmp_path, profile_override="starter")

    finding = _finding(suite.products[0].findings, "profile.semantic_metrics_missing")
    assert finding.line is not None
    assert (
        "::warning file=products/customers/semantic.yaml,line="
        in render_github_annotations(suite)
    )


def _finding(findings, code: str):
    return next(finding for finding in findings if finding.code == code)
