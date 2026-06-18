from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from dataproduct_kit.models import DataProductProject, Finding, TrustReport

ReadinessProfile = Literal["starter", "production", "regulated"]

DEFAULT_PROFILE: ReadinessProfile = "starter"
PROFILE_NAMES: tuple[ReadinessProfile, ...] = ("starter", "production", "regulated")

SENSITIVE_CLASSIFICATIONS = {
    "confidential",
    "restricted",
    "sensitive",
    "pii",
    "personal",
    "personally_identifying",
}

PLACEHOLDER_CLASSIFICATIONS = {"todo", "unknown"}


def profile_findings(
    project: DataProductProject,
    report: TrustReport,
    profile: ReadinessProfile,
) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_starter_findings(project, report, profile))
    if profile in {"production", "regulated"}:
        findings.extend(_production_findings(project, report))
    if profile == "regulated":
        findings.extend(_regulated_findings(project, report))
    return findings


def _starter_findings(
    project: DataProductProject,
    report: TrustReport,
    profile: ReadinessProfile,
) -> list[Finding]:
    from dataproduct_kit.models import Finding

    level = "error" if profile in {"production", "regulated"} else "warning"
    findings: list[Finding] = []
    if not project.policy.agent_constraints:
        findings.append(
            Finding(
                level=level,
                code="profile.agent_constraints_missing",
                message="policy.yaml must declare agent_constraints for agent-safe use",
            )
        )
    if not project.contract.quality_checks:
        findings.append(
            Finding(
                level=level,
                code="profile.quality_checks_missing",
                message="contract.yaml should declare quality checks",
            )
        )
    if not project.semantic.metrics:
        findings.append(
            Finding(
                level=level,
                code="profile.semantic_metrics_missing",
                message="semantic.yaml should declare approved metrics",
            )
        )
    return findings


def _production_findings(project: DataProductProject, report: TrustReport) -> list[Finding]:
    from dataproduct_kit.models import Finding

    findings: list[Finding] = []
    if not project.policy.allowed_purposes:
        findings.append(
            Finding(
                level="error",
                code="profile.allowed_purposes_missing",
                message="policy.yaml must declare allowed_purposes",
            )
        )
    if "agent_context" not in project.policy.allowed_purposes:
        findings.append(
            Finding(
                level="error",
                code="profile.agent_purpose_missing",
                message="policy.yaml allowed_purposes must include agent_context",
            )
        )
    contract_sensitive = {
        field.name
        for field in project.contract.schema
        if (field.classification or "").lower() in SENSITIVE_CLASSIFICATIONS
    }
    undeclared = sorted(contract_sensitive - set(project.policy.sensitive_fields))
    if undeclared:
        findings.append(
            Finding(
                level="error",
                code="profile.sensitive_fields_missing",
                message=(
                    "policy.yaml sensitive_fields must include classified sensitive "
                    f"field(s): {', '.join(undeclared)}"
                ),
            )
        )
    return findings


def _regulated_findings(project: DataProductProject, report: TrustReport) -> list[Finding]:
    from dataproduct_kit.models import Finding

    findings: list[Finding] = []
    missing_classification = sorted(
        field.name
        for field in project.contract.schema
        if _is_missing_classification(field.classification)
    )
    if missing_classification:
        findings.append(
            Finding(
                level="error",
                code="profile.classification_missing",
                message=(
                    "regulated profile requires classifications for field(s): "
                    + ", ".join(missing_classification)
                ),
            )
        )
    return findings


def _is_missing_classification(classification: str | None) -> bool:
    normalized = (classification or "").strip().lower()
    return not normalized or normalized in PLACEHOLDER_CLASSIFICATIONS
