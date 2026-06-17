from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

import typer

from dataproduct_kit.context import build_agent_context
from dataproduct_kit.loader import ManifestLoadError, load_project
from dataproduct_kit.reports import render_json_report, render_markdown_report
from dataproduct_kit.schemas import build_all_schemas, build_schema, write_schema_files
from dataproduct_kit.standards import emit_openlineage, export_odcs, export_osi
from dataproduct_kit.templates import scaffold_template
from dataproduct_kit.validators import validate_project

app = typer.Typer(help="Validate agent-ready data products from local manifests.")


@app.command()
def init(
    path: Annotated[Path, typer.Argument(help="Directory to scaffold.")] = Path("."),
    template: Annotated[str, typer.Option("--template", help="Template name.")] = "saas-churn",
) -> None:
    """Scaffold an example data product."""
    try:
        scaffold_template(path, template)
    except ValueError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(f"scaffolded {template} at {path}")


@app.command()
def validate(
    path: Annotated[Path, typer.Argument(help="Data product directory.")],
    format: Annotated[
        Literal["text", "json"],
        typer.Option("--format", help="Output format."),
    ] = "text",
    fail_on: Annotated[
        Literal["fail", "warn"],
        typer.Option("--fail-on", help="Exit nonzero at this status threshold."),
    ] = "fail",
) -> None:
    """Validate manifests, data, quality checks, semantics, freshness, and policy."""
    project = _load_or_exit(path)
    report = validate_project(project)
    if format == "json":
        typer.echo(render_json_report(report), nl=False)
    else:
        typer.echo(f"status: {report.status}")
        for finding in report.findings:
            typer.echo(f"{finding.level}: {finding.code}: {finding.message}")
    if _should_fail(report.status, fail_on):
        raise typer.Exit(1)


@app.command()
def report(
    path: Annotated[Path, typer.Argument(help="Data product directory.")],
    format: Annotated[
        Literal["json", "markdown"],
        typer.Option("--format", help="Output format."),
    ] = "json",
) -> None:
    """Emit a machine or human-readable trust report."""
    project = _load_or_exit(path)
    trust_report = validate_project(project)
    if format == "json":
        typer.echo(render_json_report(trust_report), nl=False)
    else:
        typer.echo(render_markdown_report(trust_report), nl=False)


@app.command()
def context(
    path: Annotated[Path, typer.Argument(help="Data product directory.")],
    metric: Annotated[str, typer.Option("--metric", help="Metric name.")],
    format: Annotated[Literal["json"], typer.Option("--format", help="Output format.")] = "json",
) -> None:
    """Emit compact context that agents can use without receiving query answers."""
    project = _load_or_exit(path)
    trust_report = validate_project(project)
    try:
        payload = build_agent_context(project, trust_report, metric)
    except ValueError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    typer.echo(json.dumps(payload, indent=2, sort_keys=True) + "\n", nl=False)


@app.command(name="export")
def export_command(
    standard: Annotated[
        Literal["odcs", "osi"],
        typer.Argument(help="Standard export to emit."),
    ],
    path: Annotated[Path, typer.Argument(help="Data product directory.")],
    out: Annotated[Path | None, typer.Option("--out", help="Output JSON file path.")] = None,
) -> None:
    """Export standards-aligned JSON from the local profile."""
    project = _load_or_exit(path)
    payload = export_odcs(project) if standard == "odcs" else export_osi(project)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if out is None:
        typer.echo(rendered, nl=False)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        typer.echo(str(out))


@app.command()
def schema(
    name: Annotated[
        Literal["dataproduct", "contract", "semantic", "policy", "all"],
        typer.Argument(help="Schema to emit."),
    ],
    out: Annotated[Path | None, typer.Option("--out", help="Directory for schema files.")] = None,
) -> None:
    """Emit JSON Schema for manifest files."""
    if out is not None:
        if name == "all":
            written = write_schema_files(out)
        else:
            out.mkdir(parents=True, exist_ok=True)
            path = out / f"{name}.schema.json"
            path.write_text(
                json.dumps(build_schema(name), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            written = [path]
        for path in written:
            typer.echo(str(path))
        return
    payload = build_all_schemas() if name == "all" else build_schema(name)
    typer.echo(json.dumps(payload, indent=2, sort_keys=True) + "\n", nl=False)


@app.command()
def emit(
    standard: Annotated[
        Literal["openlineage"],
        typer.Argument(help="Event format to emit."),
    ],
    path: Annotated[Path, typer.Argument(help="Data product directory.")],
    out: Annotated[Path | None, typer.Option("--out", help="Output JSONL path.")] = None,
) -> None:
    """Write local standards-compatible events."""
    project = _load_or_exit(path)
    trust_report = validate_project(project)
    output = out or path / ".dataproduct-kit" / "openlineage.jsonl"
    emit_openlineage(project, trust_report, output)
    typer.echo(str(output))


def _load_or_exit(path: Path):
    try:
        return load_project(path)
    except ManifestLoadError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error


def _should_fail(status: str, fail_on: str) -> bool:
    if status == "fail":
        return True
    return fail_on == "warn" and status == "warn"
