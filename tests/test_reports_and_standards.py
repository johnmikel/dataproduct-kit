from __future__ import annotations

import json
from pathlib import Path

from conftest import write_valid_project


def test_json_and_markdown_reports_are_deterministic(tmp_path: Path) -> None:
    from dataproduct_kit.loader import load_project
    from dataproduct_kit.reports import render_json_report, render_markdown_report
    from dataproduct_kit.validators import validate_project

    report = validate_project(load_project(write_valid_project(tmp_path)))

    json_report = render_json_report(report)
    markdown_report = render_markdown_report(report)

    parsed = json.loads(json_report)
    assert parsed["status"] == "pass"
    assert parsed["summary"]["checks_passed"] >= 1
    assert json_report == render_json_report(report)
    assert "# Trust Report: SaaS Churn Data Product" in markdown_report
    assert "| Overall status | pass |" in markdown_report
    assert markdown_report == render_markdown_report(report)


def test_agent_context_contains_metric_without_query_answer(tmp_path: Path) -> None:
    from dataproduct_kit.context import build_agent_context
    from dataproduct_kit.loader import load_project
    from dataproduct_kit.validators import validate_project

    project = load_project(write_valid_project(tmp_path))
    report = validate_project(project)

    context = build_agent_context(project, report, "churn_rate")

    assert context["metric"]["name"] == "churn_rate"
    assert context["metric"]["expression"].startswith("sum(case when churned")
    assert context["quality_status"] == "pass"
    assert context["policy"]["allowed_purposes"] == [
        "retention_reporting",
        "board_metrics",
        "agent_context",
    ]
    assert "value" not in context["metric"]


def test_odcs_and_osi_exports_are_standards_aligned(tmp_path: Path) -> None:
    from dataproduct_kit.loader import load_project
    from dataproduct_kit.standards import export_odcs, export_osi

    project = load_project(write_valid_project(tmp_path))

    odcs = export_odcs(project)
    osi = export_osi(project)

    assert odcs["kind"] == "DataContract"
    assert odcs["id"] == "saas_churn"
    assert odcs["schema"][0]["name"] == "customer_id"
    assert odcs["quality"][0]["type"] == "not_null"
    assert osi["kind"] == "SemanticModel"
    assert osi["metrics"][0]["name"] == "churn_rate"
    assert osi["dimensions"][0]["name"] == "plan"


def test_openlineage_emit_writes_deterministic_jsonl(tmp_path: Path) -> None:
    from dataproduct_kit.loader import load_project
    from dataproduct_kit.standards import emit_openlineage
    from dataproduct_kit.validators import validate_project

    project = load_project(write_valid_project(tmp_path))
    report = validate_project(project)
    output = tmp_path / ".dataproduct-kit/openlineage.jsonl"

    emit_openlineage(project, report, output)

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["eventType"] == "COMPLETE"
    assert event["eventTime"] == "2026-06-17T00:00:00Z"
    assert event["job"]["name"] == "saas_churn.validation"
    assert event["inputs"][0]["name"].endswith("data/subscriptions.csv")
    assert event["run"]["facets"]["dataproduct"]["status"] == "pass"
