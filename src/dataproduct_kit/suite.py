from __future__ import annotations

from pathlib import Path

from dataproduct_kit.loader import ManifestLoadError, load_project
from dataproduct_kit.models import Finding, SuiteProductReport, ValidationSuiteReport
from dataproduct_kit.validators import validate_project


def discover_project_dirs(root: Path) -> list[Path]:
    """Find candidate data product directories under a repo root."""
    root = root.resolve()
    if root.is_file():
        root = root.parent
    candidates = {path.parent for path in root.rglob("dataproduct.yaml")}
    return sorted(candidates, key=lambda path: _relative_path(path, root))


def validate_suite(root: Path) -> ValidationSuiteReport:
    """Validate every data product discovered below root."""
    root = root.resolve()
    product_dirs = discover_project_dirs(root)
    if not product_dirs:
        finding = Finding(
            level="error",
            code="discovery.no_products",
            message="no dataproduct.yaml files found",
        )
        return ValidationSuiteReport(
            status="fail",
            summary={
                "products_total": 0,
                "products_passed": 0,
                "products_warned": 0,
                "products_failed": 0,
                "findings_total": 1,
            },
            findings=[finding],
            products=[],
        )

    products = [_validate_product(root, product_dir) for product_dir in product_dirs]
    products_passed = sum(1 for product in products if product.status == "pass")
    products_warned = sum(1 for product in products if product.status == "warn")
    products_failed = sum(1 for product in products if product.status == "fail")
    findings_total = sum(len(product.findings) for product in products)
    status = "fail" if products_failed else "warn" if products_warned else "pass"
    return ValidationSuiteReport(
        status=status,
        summary={
            "products_total": len(products),
            "products_passed": products_passed,
            "products_warned": products_warned,
            "products_failed": products_failed,
            "findings_total": findings_total,
        },
        products=products,
    )


def _validate_product(root: Path, product_dir: Path) -> SuiteProductReport:
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
            findings=[finding],
        )
    report = validate_project(project)
    return SuiteProductReport(
        path=product_path,
        product_id=report.product_id,
        product_name=report.product_name,
        status=report.status,
        summary=report.summary,
        findings=report.findings,
        trust_report=report,
    )


def _relative_path(path: Path, root: Path) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return path.as_posix()
    value = relative.as_posix()
    return value if value else "."
