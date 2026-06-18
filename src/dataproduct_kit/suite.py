from __future__ import annotations

from datetime import date
from fnmatch import fnmatchcase
from pathlib import Path

from dataproduct_kit.config import (
    ConfigLoadError,
    KitConfig,
    SuppressionConfig,
    apply_profile_override,
    load_config,
)
from dataproduct_kit.finding_codes import KNOWN_FINDING_CODES
from dataproduct_kit.loader import ManifestLoadError, load_project
from dataproduct_kit.models import Finding, SuiteProductReport, ValidationSuiteReport
from dataproduct_kit.profiles import DEFAULT_PROFILE, ReadinessProfile, profile_findings
from dataproduct_kit.source_locations import with_config_source_lines, with_product_source_lines
from dataproduct_kit.validators import validate_project


def discover_project_dirs(root: Path, config: KitConfig | None = None) -> list[Path]:
    """Find candidate data product directories under a repo root."""
    root = root.resolve()
    if root.is_file():
        root = root.parent
    candidates = {path.parent for path in root.rglob("dataproduct.yaml")}
    config = config or KitConfig()
    filtered = [
        path
        for path in candidates
        if _included(_relative_path(path, root), config.ci.include, config.ci.exclude)
    ]
    return sorted(filtered, key=lambda path: _relative_path(path, root))


def validate_suite(root: Path, profile_override: str | None = None) -> ValidationSuiteReport:
    """Validate every data product discovered below root."""
    root = root.resolve()
    try:
        config = load_config(root)
        if profile_override is not None:
            config = apply_profile_override(config, profile_override)
    except ConfigLoadError as error:
        finding = Finding(level="error", code="config.invalid", message=str(error))
        return ValidationSuiteReport(
            status="fail",
            summary={
                "products_total": 0,
                "products_passed": 0,
                "products_warned": 0,
                "products_failed": 0,
                "findings_total": 1,
                "findings_suppressed": 0,
            },
            profile=DEFAULT_PROFILE,
            config={
                "fail_on": "fail",
                "include": ["**"],
                "exclude": [],
                "profile": DEFAULT_PROFILE,
            },
            findings=[finding],
            products=[],
        )
    config_findings = with_config_source_lines(root, _validate_suppressions(config))
    product_dirs = discover_project_dirs(root, config)
    if not product_dirs:
        finding = Finding(
            level="error",
            code="discovery.no_products",
            message="no dataproduct.yaml files found",
        )
        unused_findings = with_config_source_lines(
            root,
            _unused_suppression_findings(config, matched_suppressions=set()),
        )
        findings = [*config_findings, *unused_findings, finding]
        return ValidationSuiteReport(
            status="fail",
            summary={
                "products_total": 0,
                "products_passed": 0,
                "products_warned": 0,
                "products_failed": 0,
                "findings_total": len(findings),
                "findings_suppressed": 0,
            },
            profile=config.ci.profile,
            config=_config_summary(config),
            findings=findings,
            products=[],
        )

    matched_suppressions: set[tuple[str, str, str, str]] = set()
    products = []
    for product_dir in product_dirs:
        product = _validate_product(root, product_dir, config.ci.profile)
        products.append(_apply_suppressions(product, config, matched_suppressions))
    unused_findings = with_config_source_lines(
        root,
        _unused_suppression_findings(config, matched_suppressions),
    )
    config_findings = [*config_findings, *unused_findings]
    if config.ci.profile == "regulated":
        unsuppressed_warnings = [
            finding
            for product in products
            for finding in product.findings
            if finding.level == "warning" and not finding.suppressed
        ]
        if unsuppressed_warnings:
            config_findings.extend(
                with_config_source_lines(
                    root,
                    [
                        Finding(
                            level="error",
                            code="profile.unsuppressed_warning",
                            message="regulated profile does not allow unsuppressed warnings",
                        )
                    ],
                )
            )
    products_passed = sum(1 for product in products if product.status == "pass")
    products_warned = sum(1 for product in products if product.status == "warn")
    products_failed = sum(1 for product in products if product.status == "fail")
    findings_total = len(config_findings) + sum(len(product.findings) for product in products)
    findings_suppressed = sum(
        1 for product in products for finding in product.findings if finding.suppressed
    )
    config_failed = any(finding.level == "error" for finding in config_findings)
    config_warned = any(finding.level == "warning" for finding in config_findings)
    status = (
        "fail"
        if config_failed or products_failed
        else "warn"
        if config_warned or products_warned
        else "pass"
    )
    return ValidationSuiteReport(
        status=status,
        summary={
            "products_total": len(products),
            "products_passed": products_passed,
            "products_warned": products_warned,
            "products_failed": products_failed,
            "findings_total": findings_total,
            "findings_suppressed": findings_suppressed,
        },
        profile=config.ci.profile,
        config=_config_summary(config),
        findings=config_findings,
        products=products,
    )


def _validate_product(
    root: Path,
    product_dir: Path,
    profile: ReadinessProfile,
) -> SuiteProductReport:
    product_path = _relative_path(product_dir, root)
    try:
        project = load_project(product_dir)
    except ManifestLoadError as error:
        finding = Finding(
            level="error",
            code="manifest.load_error",
            message=str(error),
        )
        return SuiteProductReport(
            path=product_path,
            status="fail",
            summary={
                "checks_passed": 0,
                "checks_warned": 0,
                "checks_failed": 1,
            },
            findings=with_product_source_lines(root, product_path, [finding]),
        )
    report = validate_project(project)
    profile_findings_list = profile_findings(project, report, profile)
    findings = [*report.findings, *profile_findings_list]
    errors = [finding for finding in findings if finding.level == "error"]
    warnings = [finding for finding in findings if finding.level == "warning"]
    status = "fail" if errors else "warn" if warnings else "pass"
    summary = dict(report.summary)
    summary["checks_failed"] = len(errors)
    summary["checks_warned"] = len(warnings)
    findings = with_product_source_lines(root, product_path, findings)
    report = report.model_copy(
        update={"status": status, "findings": findings, "summary": summary}
    )
    return SuiteProductReport(
        path=product_path,
        product_id=report.product_id,
        product_name=report.product_name,
        status=status,
        summary=summary,
        findings=findings,
        trust_report=report,
    )


def _apply_suppressions(
    product: SuiteProductReport,
    config: KitConfig,
    matched_suppressions: set[tuple[str, str, str, str]],
) -> SuiteProductReport:
    findings = [
        _suppress_finding(finding, product.path, config.suppressions, matched_suppressions)
        for finding in product.findings
    ]
    unsuppressed_errors = sum(
        1 for finding in findings if finding.level == "error" and not finding.suppressed
    )
    unsuppressed_warnings = sum(
        1 for finding in findings if finding.level == "warning" and not finding.suppressed
    )
    suppressed = sum(1 for finding in findings if finding.suppressed)
    status = "fail" if unsuppressed_errors else "warn" if unsuppressed_warnings else "pass"
    summary = dict(product.summary)
    summary["checks_failed"] = unsuppressed_errors
    summary["checks_warned"] = unsuppressed_warnings
    summary["checks_suppressed"] = suppressed
    return product.model_copy(
        update={
            "status": status,
            "summary": summary,
            "findings": findings,
        }
    )


def _suppress_finding(
    finding: Finding,
    product_path: str,
    suppressions: list[SuppressionConfig],
    matched_suppressions: set[tuple[str, str, str, str]],
) -> Finding:
    if finding.suppressed:
        return finding
    for suppression in suppressions:
        if suppression.expires < date.today():
            continue
        if suppression.code == finding.code and _path_matches(product_path, suppression.path):
            matched_suppressions.add(_suppression_key(suppression))
            return finding.model_copy(
                update={
                    "suppressed": True,
                    "suppression_reason": suppression.reason,
                    "suppression_expires": suppression.expires.isoformat(),
                }
            )
    return finding


def _unused_suppression_findings(
    config: KitConfig,
    matched_suppressions: set[tuple[str, str, str, str]],
) -> list[Finding]:
    findings: list[Finding] = []
    for suppression in config.suppressions:
        if suppression.code not in KNOWN_FINDING_CODES:
            continue
        if suppression.expires < date.today():
            continue
        if _suppression_key(suppression) in matched_suppressions:
            continue
        findings.append(
            Finding(
                level="warning",
                code="suppression.unused",
                message=(
                    f"suppression for '{suppression.code}' at '{suppression.path}' "
                    "did not match any current finding"
                ),
            )
        )
    return findings


def _validate_suppressions(config: KitConfig) -> list[Finding]:
    findings: list[Finding] = []
    for suppression in config.suppressions:
        if suppression.code not in KNOWN_FINDING_CODES:
            findings.append(
                Finding(
                    level="error",
                    code="suppression.unknown_code",
                    message=f"suppression references unknown finding code '{suppression.code}'",
                )
            )
        if suppression.expires < date.today():
            findings.append(
                Finding(
                    level="error",
                    code="suppression.expired",
                    message=(
                        f"suppression for '{suppression.code}' at '{suppression.path}' "
                        f"expired on {suppression.expires.isoformat()}"
                    ),
                )
            )
    return findings


def _suppression_key(suppression: SuppressionConfig) -> tuple[str, str, str, str]:
    return (
        suppression.code,
        suppression.path,
        suppression.reason,
        suppression.expires.isoformat(),
    )


def _included(path: str, include: list[str], exclude: list[str]) -> bool:
    return _matches_any(path, include) and not _matches_any(path, exclude)


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(_path_matches(path, pattern) for pattern in patterns)


def _path_matches(path: str, pattern: str) -> bool:
    return fnmatchcase(path, pattern) or fnmatchcase(f"{path}/dataproduct.yaml", pattern)


def _config_summary(config: KitConfig) -> dict:
    return {
        "include": config.ci.include,
        "exclude": config.ci.exclude,
        "fail_on": config.ci.fail_on,
        "profile": config.ci.profile,
        "suppressions": len(config.suppressions),
    }


def _relative_path(path: Path, root: Path) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return path.as_posix()
    value = relative.as_posix()
    return value if value else "."
