from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from dataproduct_kit.profiles import DEFAULT_PROFILE, ReadinessProfile


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Owner(StrictModel):
    name: str
    email: EmailStr
    team: str


class FreshnessPolicy(StrictModel):
    column: str
    max_age_hours: float = Field(gt=0)
    reference_time: str | None = None


class DatasetManifest(StrictModel):
    id: str
    path: str
    format: Literal["csv"] = "csv"
    table: str
    freshness: FreshnessPolicy | None = None


class DataProductManifest(StrictModel):
    id: str
    name: str
    domain: str
    version: str
    description: str
    owner: Owner
    datasets: list[DatasetManifest]


class FieldManifest(StrictModel):
    name: str
    type: Literal["string", "integer", "number", "boolean", "date", "timestamp"]
    nullable: bool = True
    classification: str | None = None


class QualityCheck(StrictModel):
    name: str
    type: Literal[
        "not_null",
        "unique",
        "accepted_values",
        "min",
        "max",
        "row_count_min",
        "expression",
    ]
    column: str | None = None
    values: list[Any] = Field(default_factory=list)
    value: float | int | None = None
    expression: str | None = None


class ContractManifest(StrictModel):
    version: str
    dataset: str
    schema_: list[FieldManifest] = Field(alias="schema")
    quality_checks: list[QualityCheck] = Field(default_factory=list)

    @property
    def schema(self) -> list[FieldManifest]:
        return self.schema_


class MetricManifest(StrictModel):
    name: str
    label: str
    description: str
    dataset: str
    expression: str
    grain: str | None = None
    dimensions: list[str] = Field(default_factory=list)


class DimensionManifest(StrictModel):
    name: str
    dataset: str
    column: str
    type: str


class EntityManifest(StrictModel):
    name: str
    dataset: str
    key: str


class SemanticManifest(StrictModel):
    metrics: list[MetricManifest] = Field(default_factory=list)
    dimensions: list[DimensionManifest] = Field(default_factory=list)
    entities: list[EntityManifest] = Field(default_factory=list)


class PolicyManifest(StrictModel):
    allowed_purposes: list[str]
    access_notes: str
    sensitive_fields: list[str] = Field(default_factory=list)
    agent_constraints: list[str] = Field(default_factory=list)
    bi_constraints: list[str] = Field(default_factory=list)


class DataProductProject(BaseModel):
    root: Path
    product: DataProductManifest
    contract: ContractManifest
    semantic: SemanticManifest
    policy: PolicyManifest


class Finding(BaseModel):
    level: Literal["error", "warning"]
    code: str
    message: str
    check: str | None = None
    line: int | None = None
    suppressed: bool = False
    suppression_reason: str | None = None
    suppression_expires: str | None = None


class FreshnessResult(BaseModel):
    dataset: str
    column: str
    status: Literal["pass", "fail", "warn"]
    latest_value: str | None = None
    reference_time: str | None = None
    max_age_hours: float | None = None
    observed_age_hours: float | None = None


class MetricReport(BaseModel):
    name: str
    dataset: str
    expression: str
    dimensions: list[str]


class SemanticReport(BaseModel):
    metrics: list[MetricReport] = Field(default_factory=list)


class TrustReport(BaseModel):
    product_id: str
    product_name: str
    status: Literal["pass", "warn", "fail"]
    summary: dict[str, int]
    findings: list[Finding]
    freshness: list[FreshnessResult]
    semantic: SemanticReport
    policy: dict[str, Any]


class SuiteProductReport(BaseModel):
    path: str
    product_id: str | None = None
    product_name: str | None = None
    status: Literal["pass", "warn", "fail"]
    summary: dict[str, int]
    findings: list[Finding]
    trust_report: TrustReport | None = None


class ValidationSuiteReport(BaseModel):
    status: Literal["pass", "warn", "fail"]
    summary: dict[str, int]
    profile: ReadinessProfile = DEFAULT_PROFILE
    config: dict[str, Any] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    products: list[SuiteProductReport] = Field(default_factory=list)
