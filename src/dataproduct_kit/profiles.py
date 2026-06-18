from __future__ import annotations

from typing import Literal

from dataproduct_kit.models import DataProductProject, Finding, TrustReport

ReadinessProfile = Literal["starter", "production", "regulated"]

DEFAULT_PROFILE: ReadinessProfile = "starter"
PROFILE_NAMES: tuple[ReadinessProfile, ...] = ("starter", "production", "regulated")

SENSITIVE_CLASSIFICATIONS = {
    "confidential",
    "restricted",
    "secret",
    "sensitive",
    "highly_sensitive",
    "pii",
}


def profile_findings(
    project: DataProductProject,
    report: TrustReport,
    profile: ReadinessProfile,
) -> list[Finding]:
    """Return governance findings required by the selected readiness profile."""
    findings = _starter_findings(project, profile)
    if profile in {"production", "regulated"}:
        findings.extend(_production_findings(project, profile))
    if profile == "regulated":
        findings.extend(_regulated_findings(project))
    existing_codes = {finding.code for finding in report.findings}
    return _without_duplicates(findings, existing_codes=existing_codes)


def _starter_findings(project: DataProductProject, profile: ReadinessProfile) -> list[Finding]:
    level = "error" if profile in {"production", "regulated"} else "warning"
    findings: list[Finding] = []
    if not project.policy.agent_constraints:
        findings.append(
            Finding(
                level=level,
                code="profile.agent_constraints_missing",
                message=(
                    f"{profile} profile requires policy agent_constraints so agents have "
                    "explicit usage boundaries"
                ),
            )
        )
    if not project.contract.quality_checks:
        findings.append(
            Finding(
                level=level,
                code="profile.quality_checks_missing",
                message=f"{profile} profile requires at least one contract quality check",
            )
        )
    if not project.semantic.metrics:
        findings.append(
            Finding(
                level=level,
                code="profile.semantic_metrics_missing",
                message=f"{profile} profile requires at least one semantic metric",
            )
        )
    return findings


def _production_findings(
    project: DataProductProject,
    profile: ReadinessProfile,
) -> list[Finding]:
    findings: list[Finding] = []
    if not project.policy.allowed_purposes:
        findings.append(
            Finding(
                level="error",
                code="profile.allowed_purposes_missing",
                message=f"{profile} profile requires policy allowed_purposes",
            )
        )
    if "agent_context" not in project.policy.allowed_purposes:
        findings.append(
            Finding(
                level="error",
                code="profile.agent_purpose_missing",
                message=(
                    f"{profile} profile requires policy allowed_purposes to include "
                    "'agent_context'"
                ),
            )
        )
    missing_sensitive_fields = sorted(
        field.name
        for field in project.contract.schema
        if _is_sensitive(field.classification) and field.name not in project.policy.sensitive_fields
    )
    if missing_sensitive_fields:
        findings.append(
            Finding(
                level="error",
                code="profile.sensitive_fields_missing",
                message=(
                    f"{profile} profile requires sensitive classified field(s) in "
                    f"policy sensitive_fields: {', '.join(missing_sensitive_fields)}"
                ),
            )
        )
    return findings


def _regulated_findings(project: DataProductProject) -> list[Finding]:
    unclassified_fields = sorted(
        field.name for field in project.contract.schema if not (field.classification or "").strip()
    )
    if not unclassified_fields:
        return []
    return [
        Finding(
            level="error",
            code="profile.classification_missing",
            message=(
                "regulated profile requires classifications for field(s): "
                f"{', '.join(unclassified_fields)}"
            ),
        )
    ]


def _is_sensitive(classification: str | None) -> bool:
    return (classification or "").strip().lower() in SENSITIVE_CLASSIFICATIONS


def _without_duplicates(findings: list[Finding], existing_codes: set[str]) -> list[Finding]:
    seen = set(existing_codes)
    unique: list[Finding] = []
    for finding in findings:
        if finding.code in seen:
            continue
        seen.add(finding.code)
        unique.append(finding)
    return unique
