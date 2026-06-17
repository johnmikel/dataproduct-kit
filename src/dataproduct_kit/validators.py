from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from dataproduct_kit.models import (
    DataProductProject,
    DatasetManifest,
    FieldManifest,
    Finding,
    FreshnessResult,
    MetricReport,
    SemanticReport,
    TrustReport,
)

TYPE_CASTS = {
    "integer": "BIGINT",
    "number": "DOUBLE",
    "boolean": "BOOLEAN",
    "date": "DATE",
    "timestamp": "TIMESTAMP",
}

COLUMN_CHECKS = {"not_null", "unique", "accepted_values", "min", "max", "expression"}


def validate_project(project: DataProductProject) -> TrustReport:
    findings: list[Finding] = []
    freshness: list[FreshnessResult] = []
    pass_count = 0

    dataset_by_id = {dataset.id: dataset for dataset in project.product.datasets}
    field_by_name = {field.name: field for field in project.contract.schema}

    if project.contract.dataset not in dataset_by_id:
        findings.append(
            _error(
                "contract.unknown_dataset",
                f"contract dataset '{project.contract.dataset}' is not declared in "
                "dataproduct.yaml",
            )
        )

    with duckdb.connect(database=":memory:") as con:
        table_ready = _prepare_dataset(
            con,
            project.root,
            dataset_by_id,
            project.contract.dataset,
            findings,
        )
        if table_ready:
            table = dataset_by_id[project.contract.dataset].table
            pass_count += _validate_schema(con, table, project.contract.schema, findings)
            pass_count += _validate_quality(
                con,
                table,
                project.contract.schema,
                project.contract.quality_checks,
                findings,
            )
            fresh_result, fresh_passes = _validate_freshness(
                con,
                table,
                dataset_by_id[project.contract.dataset],
                field_by_name,
                findings,
            )
            if fresh_result is not None:
                freshness.append(fresh_result)
            pass_count += fresh_passes
            pass_count += _validate_semantics(
                con,
                table,
                project,
                dataset_by_id,
                field_by_name,
                findings,
            )

    pass_count += _validate_policy(project, field_by_name, findings)

    errors = [finding for finding in findings if finding.level == "error"]
    warnings = [finding for finding in findings if finding.level == "warning"]
    status = "fail" if errors else "warn" if warnings else "pass"
    metrics = [
        MetricReport(
            name=metric.name,
            dataset=metric.dataset,
            expression=metric.expression,
            dimensions=metric.dimensions,
        )
        for metric in project.semantic.metrics
    ]
    return TrustReport(
        product_id=project.product.id,
        product_name=project.product.name,
        status=status,
        summary={
            "checks_passed": pass_count,
            "checks_warned": len(warnings),
            "checks_failed": len(errors),
        },
        findings=findings,
        freshness=freshness,
        semantic=SemanticReport(metrics=metrics),
        policy={
            "allowed_purposes": project.policy.allowed_purposes,
            "sensitive_fields": project.policy.sensitive_fields,
            "agent_constraints": project.policy.agent_constraints,
            "bi_constraints": project.policy.bi_constraints,
        },
    )


def _prepare_dataset(
    con: duckdb.DuckDBPyConnection,
    root: Path,
    dataset_by_id: dict[str, DatasetManifest],
    dataset_id: str,
    findings: list[Finding],
) -> bool:
    dataset = dataset_by_id.get(dataset_id)
    if dataset is None:
        return False
    path = root / dataset.path
    if not path.exists():
        findings.append(
            _error(
                "dataset.missing_file",
                f"dataset '{dataset.id}' file not found: {dataset.path}",
            )
        )
        return False
    try:
        con.execute(
            f"CREATE OR REPLACE VIEW {_qi(dataset.table)} AS "
            f"SELECT * FROM read_csv_auto({_literal(str(path))}, header=true)"
        )
    except duckdb.Error as error:
        findings.append(
            _error(
                "dataset.read_error",
                f"dataset '{dataset.id}' could not be read: {str(error).splitlines()[0]}",
            )
        )
        return False
    return True


def _validate_schema(
    con: duckdb.DuckDBPyConnection,
    table: str,
    fields: list[FieldManifest],
    findings: list[Finding],
) -> int:
    passes = 0
    available = _columns(con, table)
    for field in fields:
        if field.name not in available:
            findings.append(
                _error(
                    "schema.missing_column",
                    f"required column '{field.name}' is missing from dataset '{table}'",
                )
            )
            continue
        passes += 1
        if field.type != "string":
            cast_type = TYPE_CASTS[field.type]
            bad_count = con.execute(
                f"SELECT count(*) FROM {_qi(table)} "
                f"WHERE {_qi(field.name)} IS NOT NULL "
                f"AND try_cast({_qi(field.name)} AS {cast_type}) IS NULL"
            ).fetchone()[0]
            if bad_count:
                findings.append(
                    _error(
                        "schema.type_mismatch",
                        f"column '{field.name}' has {bad_count} value(s) that cannot "
                        f"cast to {field.type}",
                    )
                )
            else:
                passes += 1
    return passes


def _validate_quality(
    con: duckdb.DuckDBPyConnection,
    table: str,
    fields: list[FieldManifest],
    checks: list[Any],
    findings: list[Finding],
) -> int:
    passes = 0
    available = {field.name for field in fields}
    for field in fields:
        if (
            not field.nullable
            and field.name in available
            and _column_exists(con, table, field.name)
        ):
            failures = _blank_count(con, table, field.name)
            if failures:
                findings.append(
                    _error(
                        "schema.nullable",
                        f"non-nullable column '{field.name}' contains {failures} "
                        "blank/null value(s)",
                    )
                )
            else:
                passes += 1
    for check in checks:
        if check.type == "row_count_min":
            if check.value is None:
                findings.append(
                    _error(
                        "quality.invalid_check",
                        f"check '{check.name}' requires a value",
                        check.name,
                    )
                )
                continue
            count = con.execute(f"SELECT count(*) FROM {_qi(table)}").fetchone()[0]
            if check.value is None or count < check.value:
                findings.append(
                    _error(
                        "quality.row_count_min",
                        f"check '{check.name}' expected at least {check.value} rows "
                        f"but found {count}",
                        check.name,
                    )
                )
            else:
                passes += 1
            continue
        if check.type in COLUMN_CHECKS and check.column is None:
            findings.append(
                _error(
                    "quality.invalid_check",
                    f"check '{check.name}' requires a column",
                    check.name,
                )
            )
            continue
        if check.column and not _column_exists(con, table, check.column):
            findings.append(
                _error(
                    "quality.unknown_column",
                    f"check '{check.name}' references missing column '{check.column}'",
                    check.name,
                )
            )
            continue
        if check.type == "not_null":
            failures = _blank_count(con, table, _require_column(check))
            if failures:
                findings.append(
                    _error(
                        "quality.not_null",
                        f"check '{check.name}' found {failures} blank/null value(s)",
                        check.name,
                    )
                )
            else:
                passes += 1
        elif check.type == "unique":
            column = _require_column(check)
            duplicates = con.execute(
                f"SELECT count(*) - count(DISTINCT {_qi(column)}) FROM {_qi(table)} "
                f"WHERE {_qi(column)} IS NOT NULL"
            ).fetchone()[0]
            if duplicates:
                findings.append(
                    _error(
                        "quality.unique",
                        f"check '{check.name}' found {duplicates} duplicate value(s)",
                        check.name,
                    )
                )
            else:
                passes += 1
        elif check.type == "accepted_values":
            column = _require_column(check)
            allowed = {_stringify(value) for value in check.values}
            invalid = [
                _stringify(row[0])
                for row in con.execute(
                    f"SELECT DISTINCT cast({_qi(column)} AS VARCHAR) FROM {_qi(table)} "
                    f"WHERE {_qi(column)} IS NOT NULL ORDER BY 1"
                ).fetchall()
                if _stringify(row[0]) not in allowed
            ]
            if invalid:
                findings.append(
                    _error(
                        "quality.accepted_values",
                        f"check '{check.name}' found disallowed value(s): {', '.join(invalid)}",
                        check.name,
                    )
                )
            else:
                passes += 1
        elif check.type in {"min", "max"}:
            if check.value is None:
                findings.append(
                    _error(
                        "quality.invalid_check",
                        f"check '{check.name}' requires a value",
                        check.name,
                    )
                )
                continue
            column = _require_column(check)
            operator = "<" if check.type == "min" else ">"
            failures = con.execute(
                f"SELECT count(*) FROM {_qi(table)} "
                f"WHERE try_cast({_qi(column)} AS DOUBLE) {operator} ?",
                [check.value],
            ).fetchone()[0]
            if failures:
                findings.append(
                    _error(
                        f"quality.{check.type}",
                        f"check '{check.name}' found {failures} value(s) outside "
                        f"threshold {check.value}",
                        check.name,
                    )
                )
            else:
                passes += 1
        elif check.type == "expression":
            if not check.expression:
                findings.append(
                    _error(
                        "quality.expression",
                        f"check '{check.name}' has no expression",
                        check.name,
                    )
                )
                continue
            failures = con.execute(
                f"SELECT count(*) FROM {_qi(table)} WHERE NOT ({check.expression})"
            ).fetchone()[0]
            if failures:
                findings.append(
                    _error(
                        "quality.expression",
                        f"check '{check.name}' failed for {failures} row(s)",
                        check.name,
                    )
                )
            else:
                passes += 1
    return passes


def _validate_freshness(
    con: duckdb.DuckDBPyConnection,
    table: str,
    dataset: DatasetManifest,
    fields: dict[str, FieldManifest],
    findings: list[Finding],
) -> tuple[FreshnessResult | None, int]:
    if dataset.freshness is None:
        findings.append(
            _warning(
                "freshness.missing",
                f"dataset '{dataset.id}' has no freshness policy",
            )
        )
        return None, 0
    policy = dataset.freshness
    if policy.column not in fields or not _column_exists(con, table, policy.column):
        findings.append(
            _error(
                "freshness.unknown_column",
                f"freshness column '{policy.column}' is not declared in the contract",
            )
        )
        return (
            FreshnessResult(
                dataset=dataset.id,
                column=policy.column,
                status="fail",
                max_age_hours=policy.max_age_hours,
            ),
            0,
        )
    latest = con.execute(
        f"SELECT max(try_cast({_qi(policy.column)} AS TIMESTAMP)) FROM {_qi(table)}"
    ).fetchone()[0]
    reference = _parse_time(policy.reference_time) if policy.reference_time else datetime.now(UTC)
    if latest is None:
        findings.append(
            _error(
                "freshness.no_values",
                f"freshness column '{policy.column}' has no timestamp values",
            )
        )
        return (
            FreshnessResult(
                dataset=dataset.id,
                column=policy.column,
                status="fail",
                reference_time=_format_time(reference),
                max_age_hours=policy.max_age_hours,
            ),
            0,
        )
    latest_utc = latest.replace(tzinfo=UTC) if latest.tzinfo is None else latest.astimezone(UTC)
    observed_age = round((reference - latest_utc).total_seconds() / 3600, 3)
    if observed_age > policy.max_age_hours:
        findings.append(
            _error(
                "freshness.stale",
                f"dataset '{dataset.id}' is {observed_age:g} hours old; SLA is "
                f"{policy.max_age_hours:g} hours",
            )
        )
        status = "fail"
        passes = 0
    else:
        status = "pass"
        passes = 1
    return (
        FreshnessResult(
            dataset=dataset.id,
            column=policy.column,
            status=status,
            latest_value=_format_time(latest_utc),
            reference_time=_format_time(reference),
            max_age_hours=policy.max_age_hours,
            observed_age_hours=observed_age,
        ),
        passes,
    )


def _validate_semantics(
    con: duckdb.DuckDBPyConnection,
    table: str,
    project: DataProductProject,
    dataset_by_id: dict[str, DatasetManifest],
    fields: dict[str, FieldManifest],
    findings: list[Finding],
) -> int:
    passes = 0
    dimensions = {dimension.name: dimension for dimension in project.semantic.dimensions}
    for dimension in project.semantic.dimensions:
        if dimension.dataset not in dataset_by_id:
            findings.append(
                _error(
                    "semantic.unknown_dataset",
                    f"dimension '{dimension.name}' references unknown dataset "
                    f"'{dimension.dataset}'",
                )
            )
        elif dimension.column not in fields:
            findings.append(
                _error(
                    "semantic.unknown_column",
                    f"dimension '{dimension.name}' references unknown column '{dimension.column}'",
                )
            )
        else:
            passes += 1
    for entity in project.semantic.entities:
        if entity.dataset not in dataset_by_id:
            findings.append(
                _error(
                    "semantic.unknown_dataset",
                    f"entity '{entity.name}' references unknown dataset '{entity.dataset}'",
                )
            )
        elif entity.key not in fields:
            findings.append(
                _error(
                    "semantic.unknown_key",
                    f"entity '{entity.name}' references unknown key '{entity.key}'",
                )
            )
        else:
            passes += 1
    for metric in project.semantic.metrics:
        if metric.dataset not in dataset_by_id:
            findings.append(
                _error(
                    "semantic.unknown_dataset",
                    f"metric '{metric.name}' references unknown dataset '{metric.dataset}'",
                )
            )
            continue
        for dimension_name in metric.dimensions:
            if dimension_name not in dimensions:
                findings.append(
                    _error(
                        "semantic.unknown_dimension",
                        f"metric '{metric.name}' references unknown dimension '{dimension_name}'",
                    )
                )
            else:
                passes += 1
        try:
            con.execute(f"SELECT {metric.expression} AS metric_value FROM {_qi(table)}").fetchone()
        except duckdb.Error as error:
            findings.append(
                _error(
                    "semantic.expression",
                    f"metric '{metric.name}' expression failed: {str(error).splitlines()[0]}",
                )
            )
        else:
            passes += 1
    return passes


def _validate_policy(
    project: DataProductProject,
    fields: dict[str, FieldManifest],
    findings: list[Finding],
) -> int:
    passes = 0
    if project.policy.allowed_purposes:
        passes += 1
    else:
        findings.append(
            _error(
                "policy.allowed_purposes",
                "policy must define at least one allowed purpose",
            )
        )
    if project.policy.access_notes.strip():
        passes += 1
    else:
        findings.append(_error("policy.access_notes", "policy access_notes must not be blank"))
    for field in project.policy.sensitive_fields:
        if field not in fields:
            findings.append(
                _error(
                    "policy.unknown_sensitive_field",
                    f"sensitive field '{field}' is not in contract",
                )
            )
        else:
            passes += 1
    return passes


def _columns(con: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    rows = con.execute(f"DESCRIBE SELECT * FROM {_qi(table)}").fetchall()
    return {row[0] for row in rows}


def _column_exists(con: duckdb.DuckDBPyConnection, table: str, column: str) -> bool:
    return column in _columns(con, table)


def _blank_count(con: duckdb.DuckDBPyConnection, table: str, column: str) -> int:
    return con.execute(
        f"SELECT count(*) FROM {_qi(table)} "
        f"WHERE {_qi(column)} IS NULL OR trim(cast({_qi(column)} AS VARCHAR)) = ''"
    ).fetchone()[0]


def _require_column(check: Any) -> str:
    if check.column is None:
        raise ValueError(f"quality check '{check.name}' requires a column")
    return check.column


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _format_time(value: datetime) -> str:
    return value.astimezone(UTC).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"


def _qi(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _stringify(value: Any) -> str:
    return str(value)


def _error(code: str, message: str, check: str | None = None) -> Finding:
    return Finding(level="error", code=code, message=message, check=check)


def _warning(code: str, message: str, check: str | None = None) -> Finding:
    return Finding(level="warning", code=code, message=message, check=check)
