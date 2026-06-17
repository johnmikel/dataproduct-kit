from __future__ import annotations

from dataproduct_kit.models import DataProductProject, TrustReport


def build_agent_context(
    project: DataProductProject,
    report: TrustReport,
    metric_name: str,
) -> dict[str, object]:
    metric = next((item for item in project.semantic.metrics if item.name == metric_name), None)
    if metric is None:
        raise ValueError(f"metric '{metric_name}' not found")
    dataset = next(item for item in project.product.datasets if item.id == metric.dataset)
    freshness = next((item for item in report.freshness if item.dataset == dataset.id), None)
    dimensions = [
        dimension.model_dump(mode="json")
        for dimension in project.semantic.dimensions
        if dimension.name in metric.dimensions
    ]
    return {
        "product": {
            "id": project.product.id,
            "name": project.product.name,
            "domain": project.product.domain,
            "version": project.product.version,
            "owner": project.product.owner.model_dump(mode="json"),
        },
        "metric": {
            "name": metric.name,
            "label": metric.label,
            "description": metric.description,
            "dataset": metric.dataset,
            "expression": metric.expression,
            "grain": metric.grain,
            "dimensions": metric.dimensions,
        },
        "dimensions": dimensions,
        "quality_status": report.status,
        "freshness": freshness.model_dump(mode="json") if freshness else None,
        "policy": {
            "allowed_purposes": project.policy.allowed_purposes,
            "access_notes": project.policy.access_notes,
            "sensitive_fields": project.policy.sensitive_fields,
            "agent_constraints": project.policy.agent_constraints,
        },
        "lineage": {
            "dataset": dataset.id,
            "path": dataset.path,
            "table": dataset.table,
        },
    }
