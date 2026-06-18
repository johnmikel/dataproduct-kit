from __future__ import annotations

from pathlib import Path

from dataproduct_kit.loader import load_project
from dataproduct_kit.profiles import ReadinessProfile, profile_findings
from dataproduct_kit.validators import validate_project


def inspect_project(
    path: Path,
    target_profile: ReadinessProfile = "production",
) -> dict[str, object]:
    project = load_project(path)
    report = validate_project(project)
    profile_gap_findings = [
        finding.model_copy(update={"level": "warning"})
        for finding in profile_findings(project, report, target_profile)
    ]
    findings = [*report.findings, *profile_gap_findings]
    errors = [finding for finding in findings if finding.level == "error"]
    warnings = [finding for finding in findings if finding.level == "warning"]
    return {
        "profile": target_profile,
        "status": "fail" if errors else "warn" if warnings else "pass",
        "findings": [finding.model_dump(mode="json") for finding in findings],
        "next_steps": [_next_step(finding.code) for finding in findings],
    }


def _next_step(code: str) -> str:
    mapping = {
        "profile.agent_constraints_missing": "Add agent_constraints to policy.yaml.",
        "profile.quality_checks_missing": "Add quality_checks to contract.yaml.",
        "freshness.missing": "Add a freshness policy to dataproduct.yaml.",
    }
    return mapping.get(code, f"Resolve finding {code}.")
