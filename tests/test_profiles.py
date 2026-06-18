from __future__ import annotations

from pathlib import Path
from typing import Any

from conftest import write_text, write_valid_project


def test_starter_warns_for_missing_agent_constraints(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    product_dir = write_valid_project(tmp_path / "products/churn")
    _replace_policy_block(product_dir, "agent_constraints", [])

    suite = validate_suite(tmp_path)

    assert suite.status == "warn"
    assert suite.products[0].status == "warn"
    finding = _only_profile_finding(suite.products[0].findings)
    assert finding.level == "warning"
    assert finding.code == "profile.agent_constraints_missing"


def test_production_blocks_missing_agent_constraints(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    product_dir = write_valid_project(tmp_path / "products/churn")
    _replace_policy_block(product_dir, "agent_constraints", [])

    suite = validate_suite(tmp_path, profile_override="production")

    assert suite.status == "fail"
    assert suite.products[0].status == "fail"
    finding = _only_profile_finding(suite.products[0].findings)
    assert finding.level == "error"
    assert finding.code == "profile.agent_constraints_missing"


def test_production_blocks_missing_agent_purpose(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    product_dir = write_valid_project(tmp_path / "products/churn")
    policy_path = product_dir / "policy.yaml"
    policy_path.write_text(
        policy_path.read_text(encoding="utf-8").replace("  - agent_context\n", ""),
        encoding="utf-8",
    )

    suite = validate_suite(tmp_path, profile_override="production")

    assert suite.status == "fail"
    assert any(
        finding.level == "error" and finding.code == "profile.agent_purpose_missing"
        for finding in suite.products[0].findings
    )


def test_production_blocks_unlisted_sensitive_classified_fields(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    product_dir = write_valid_project(tmp_path / "products/churn")
    policy_path = product_dir / "policy.yaml"
    policy_path.write_text(
        policy_path.read_text(encoding="utf-8").replace("  - monthly_recurring_revenue\n", ""),
        encoding="utf-8",
    )

    suite = validate_suite(tmp_path, profile_override="production")

    assert suite.status == "fail"
    assert any(
        finding.level == "error"
        and finding.code == "profile.sensitive_fields_missing"
        and "monthly_recurring_revenue" in finding.message
        for finding in suite.products[0].findings
    )


def test_regulated_blocks_unsuppressed_warnings(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    product_dir = write_valid_project(tmp_path / "products/churn")
    _remove_freshness_policy(product_dir)

    suite = validate_suite(tmp_path, profile_override="regulated")

    assert suite.status == "fail"
    assert suite.products[0].status == "warn"
    assert any(finding.code == "freshness.missing" for finding in suite.products[0].findings)
    assert any(
        finding.level == "error" and finding.code == "profile.unsuppressed_warning"
        for finding in suite.findings
    )


def test_regulated_allows_suppressed_warnings(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    product_dir = write_valid_project(tmp_path / "products/churn")
    _remove_freshness_policy(product_dir)
    write_text(
        tmp_path / "dataproduct-kit.toml",
        """
        [ci]
        profile = "regulated"

        [[suppressions]]
        code = "freshness.missing"
        path = "products/churn"
        reason = "Freshness policy is being added during onboarding."
        expires = "2999-01-01"
        """,
    )

    suite = validate_suite(tmp_path)

    assert suite.status == "pass"
    assert suite.products[0].status == "pass"
    assert suite.summary["findings_suppressed"] == 1
    assert not any(finding.code == "profile.unsuppressed_warning" for finding in suite.findings)


def _only_profile_finding(findings: list[Any]) -> Any:
    profile_findings = [
        finding for finding in findings if finding.code.startswith("profile.")
    ]
    assert len(profile_findings) == 1
    return profile_findings[0]


def _replace_policy_block(product_dir: Path, key: str, values: list[str]) -> None:
    policy_path = product_dir / "policy.yaml"
    lines = policy_path.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line == f"{key}:":
            if values:
                output.append(line)
                for value in values:
                    output.append(f"  - {value}")
            else:
                output.append(f"{key}: []")
            index += 1
            while index < len(lines) and lines[index].startswith("  - "):
                index += 1
            continue
        output.append(line)
        index += 1
    policy_path.write_text("\n".join(output) + "\n", encoding="utf-8")


def _remove_freshness_policy(product_dir: Path) -> None:
    dataproduct_path = product_dir / "dataproduct.yaml"
    dataproduct_path.write_text(
        dataproduct_path.read_text(encoding="utf-8").replace(
            "    freshness:\n"
            "      column: updated_at\n"
            "      max_age_hours: 48\n"
            '      reference_time: "2026-06-17T00:00:00Z"\n',
            "",
        ),
        encoding="utf-8",
    )
