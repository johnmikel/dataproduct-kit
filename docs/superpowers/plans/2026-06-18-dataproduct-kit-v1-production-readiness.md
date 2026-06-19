# dataproduct-kit v1 Production Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the v1 production-readiness path for `dataproduct-kit` as an open source CI gate for agent-safe data products.

**Architecture:** Keep validation local and deterministic. Add a small readiness profile layer between project validation and suite aggregation, add CSV scaffolding and doctor diagnostics as onboarding helpers, and derive CLI/GitHub/SARIF/JSON outputs from the same structured report objects.

**Tech Stack:** Python 3.11+, Typer CLI, Pydantic v2, DuckDB, PyYAML, pytest, Ruff, GitHub composite actions, SARIF JSON.

---

## Spec Reference

Implement against:

- `docs/superpowers/specs/2026-06-18-dataproduct-kit-v1-production-readiness-design.md`

## File Structure

Create:

- `src/dataproduct_kit/profiles.py`  
  Owns readiness profile names and profile-specific finding generation.
- `src/dataproduct_kit/csv_scaffold.py`  
  Owns `init from-csv` inference and starter manifest writing.
- `src/dataproduct_kit/doctor.py`  
  Owns project diagnostics and production-gap explanations.
- `docs/readiness-profiles.md`  
  User-facing profile reference.
- `docs/from-csv.md`  
  User-facing bring-your-own CSV onboarding guide.
- `docs/json-output.md`  
  Stable JSON field compatibility notes.
- `tests/test_profiles.py`  
  Unit/CLI coverage for profile behavior.
- `tests/test_csv_scaffold.py`  
  Unit/CLI coverage for CSV starter generation.
- `tests/test_doctor.py`  
  Unit/CLI coverage for doctor diagnostics.

Modify:

- `src/dataproduct_kit/models.py`  
  Add profile metadata to report models if needed.
- `src/dataproduct_kit/config.py`  
  Add `[ci].profile`.
- `src/dataproduct_kit/suite.py`  
  Apply readiness profiles before suppressions and include profile metadata.
- `src/dataproduct_kit/validators.py`  
  Add any base findings needed for profile rules while keeping validator free of CI concerns.
- `src/dataproduct_kit/context.py`  
  Enforce policy-aware agent context rules.
- `src/dataproduct_kit/templates.py`  
  Route `init demo` and `init from-csv` scaffolding cleanly.
- `src/dataproduct_kit/cli.py`  
  Add `--profile`, `doctor`, and `init from-csv` CLI surfaces.
- `src/dataproduct_kit/finding_codes.py`  
  Add new stable finding codes.
- `src/dataproduct_kit/ci.py`  
  Preserve JSON/SARIF/GitHub output from shared findings; add profile metadata where needed.
- `action.yml`  
  Add `profile` input and pass it to `dataproduct-kit ci`.
- `README.md`, `docs/ci-adoption.md`, `docs/finding-codes.md`, `docs/suppressions.md`, `ROADMAP.md`, `CHANGELOG.md`  
  Update product identity, v1 usage, profile docs, and release notes.
- `tests/test_cli.py`, `tests/test_ci.py`, `tests/test_reports_and_standards.py`, `tests/test_release_readiness.py`  
  Extend existing integration and metadata checks.

## Implementation Tasks

### Task 1: Add Readiness Profile Config And CLI Plumbing

**Files:**
- Create: `src/dataproduct_kit/profiles.py`
- Modify: `src/dataproduct_kit/config.py`
- Modify: `src/dataproduct_kit/models.py`
- Modify: `src/dataproduct_kit/suite.py`
- Modify: `src/dataproduct_kit/cli.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_ci.py`

- [x] **Step 1: Write failing tests for config profile parsing**

Add to `tests/test_config.py`:

```python
import pytest


def test_config_accepts_ci_profile(tmp_path: Path) -> None:
    from dataproduct_kit.config import load_config

    (tmp_path / "dataproduct-kit.toml").write_text(
        "[ci]\nprofile = \"production\"\nfail_on = \"warn\"\n",
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    assert config.ci.profile == "production"
    assert config.ci.fail_on == "warn"


def test_config_rejects_unknown_ci_profile(tmp_path: Path) -> None:
    from dataproduct_kit.config import ConfigLoadError, load_config

    (tmp_path / "dataproduct-kit.toml").write_text(
        "[ci]\nprofile = \"anything\"\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigLoadError) as error:
        load_config(tmp_path)

    assert "ci.profile" in str(error.value)
```

- [x] **Step 2: Write failing tests for CLI profile override**

Add to `tests/test_ci.py`:

```python
def test_cli_ci_accepts_profile_override(tmp_path: Path) -> None:
    from dataproduct_kit.cli import app

    runner = CliRunner()
    write_valid_project(tmp_path / "products/pass")

    result = runner.invoke(
        app,
        ["ci", str(tmp_path), "--profile", "production", "--format", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["profile"] == "production"
    assert payload["config"]["profile"] == "production"
```

- [x] **Step 3: Run tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_config.py::test_config_accepts_ci_profile tests/test_config.py::test_config_rejects_unknown_ci_profile tests/test_ci.py::test_cli_ci_accepts_profile_override -q
```

Expected: fail because `profile` is not modeled and `ci --profile` does not exist.

- [x] **Step 4: Implement profile type and config field**

Create `src/dataproduct_kit/profiles.py`:

```python
from __future__ import annotations

from typing import Literal

ReadinessProfile = Literal["starter", "production", "regulated"]

DEFAULT_PROFILE: ReadinessProfile = "starter"
PROFILE_NAMES: tuple[ReadinessProfile, ...] = ("starter", "production", "regulated")
```

Modify `src/dataproduct_kit/config.py`:

```python
from dataproduct_kit.profiles import DEFAULT_PROFILE, ReadinessProfile


class CiConfig(StrictModel):
    include: list[str] = Field(default_factory=lambda: ["**"])
    exclude: list[str] = Field(default_factory=list)
    fail_on: Literal["fail", "warn"] = "fail"
    profile: ReadinessProfile = DEFAULT_PROFILE
```

- [x] **Step 5: Add profile metadata to suite report**

Modify `src/dataproduct_kit/models.py`:

```python
class ValidationSuiteReport(BaseModel):
    status: Literal["pass", "warn", "fail"]
    summary: dict[str, int]
    profile: str = "starter"
    config: dict[str, Any] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    products: list[SuiteProductReport] = Field(default_factory=list)
```

Modify all `ValidationSuiteReport(...)` constructors in `src/dataproduct_kit/suite.py`
to set `profile=config.ci.profile` or `"starter"` for invalid/no config fallbacks.

Update `_config_summary`:

```python
def _config_summary(config: KitConfig) -> dict:
    return {
        "include": config.ci.include,
        "exclude": config.ci.exclude,
        "fail_on": config.ci.fail_on,
        "profile": config.ci.profile,
        "suppressions": len(config.suppressions),
    }
```

- [x] **Step 6: Add CLI profile option**

Modify `src/dataproduct_kit/cli.py` `ci(...)` signature:

```python
from dataproduct_kit.profiles import ReadinessProfile

profile: Annotated[
    ReadinessProfile | None,
    typer.Option("--profile", help="Readiness profile to apply."),
] = None,
```

Then call:

```python
suite = validate_suite(path, profile_override=profile)
```

Update `validate_suite` signature in `src/dataproduct_kit/suite.py`:

```python
def validate_suite(root: Path, profile_override: str | None = None) -> ValidationSuiteReport:
```

After loading config, apply:

```python
if profile_override is not None:
    config = config.model_copy(
        update={"ci": config.ci.model_copy(update={"profile": profile_override})}
    )
```

- [x] **Step 7: Run profile plumbing tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_config.py tests/test_ci.py -q
```

Expected: pass.

- [x] **Step 8: Commit**

```bash
git add src/dataproduct_kit/profiles.py src/dataproduct_kit/config.py src/dataproduct_kit/models.py src/dataproduct_kit/suite.py src/dataproduct_kit/cli.py tests/test_config.py tests/test_ci.py
git commit -m "feat: add readiness profile plumbing"
```

### Task 2: Implement Profile-Specific Governance Findings

**Files:**
- Modify: `src/dataproduct_kit/profiles.py`
- Modify: `src/dataproduct_kit/suite.py`
- Modify: `src/dataproduct_kit/finding_codes.py`
- Create/modify: `tests/test_profiles.py`
- Modify: `tests/conftest.py` if helper fixtures are useful

- [x] **Step 1: Write failing tests for starter warnings**

In `tests/test_profiles.py`:

```python
from __future__ import annotations

from pathlib import Path

from conftest import write_valid_project


def test_starter_warns_for_missing_agent_constraints(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    project_dir = tmp_path / "products/customers"
    write_valid_project(project_dir)
    policy = (project_dir / "policy.yaml").read_text(encoding="utf-8")
    (project_dir / "policy.yaml").write_text(
        policy.replace(
            "agent_constraints:\n"
            "  - Agents may use the approved churn_rate metric only.\n"
            "  - Agents must include freshness and quality status with answers.\n",
            "agent_constraints: []\n",
        ),
        encoding="utf-8",
    )

    suite = validate_suite(tmp_path, profile_override="starter")

    assert suite.status == "warn"
    assert suite.products[0].status == "warn"
    assert any(
        finding.code == "profile.agent_constraints_missing"
        and finding.level == "warning"
        for finding in suite.products[0].findings
    )
```

- [x] **Step 2: Write failing tests for production blockers**

Add:

```python
def test_production_blocks_missing_agent_constraints(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    project_dir = tmp_path / "products/customers"
    write_valid_project(project_dir)
    policy = (project_dir / "policy.yaml").read_text(encoding="utf-8")
    (project_dir / "policy.yaml").write_text(
        policy.replace(
            "agent_constraints:\n"
            "  - Agents may use the approved churn_rate metric only.\n"
            "  - Agents must include freshness and quality status with answers.\n",
            "agent_constraints: []\n",
        ),
        encoding="utf-8",
    )

    suite = validate_suite(tmp_path, profile_override="production")

    assert suite.status == "fail"
    assert any(
        finding.code == "profile.agent_constraints_missing"
        and finding.level == "error"
        for finding in suite.products[0].findings
    )
```

- [x] **Step 3: Write failing tests for regulated warning policy**

Add:

```python
def test_regulated_blocks_unsuppressed_warnings(tmp_path: Path) -> None:
    from dataproduct_kit.suite import validate_suite

    project_dir = tmp_path / "products/warn"
    write_valid_project(project_dir)
    text = (project_dir / "dataproduct.yaml").read_text(encoding="utf-8")
    (project_dir / "dataproduct.yaml").write_text(
        text.replace(
            "    freshness:\n"
            "      column: updated_at\n"
            "      max_age_hours: 48\n"
            "      reference_time: \"2026-06-17T00:00:00Z\"\n",
            "",
        ),
        encoding="utf-8",
    )

    suite = validate_suite(tmp_path, profile_override="regulated")

    assert suite.status == "fail"
    assert any(finding.code == "profile.unsuppressed_warning" for finding in suite.findings)
```

- [x] **Step 4: Run tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_profiles.py -q
```

Expected: fail because profile findings are not implemented.

- [x] **Step 5: Implement profile rule function**

Add to `src/dataproduct_kit/profiles.py`:

```python
from dataproduct_kit.models import DataProductProject, Finding, TrustReport


SENSITIVE_CLASSIFICATIONS = {
    "confidential",
    "restricted",
    "sensitive",
    "pii",
    "personal",
    "personally_identifying",
}


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
```

Implement helpers:

```python
def _starter_findings(
    project: DataProductProject,
    report: TrustReport,
    profile: ReadinessProfile,
) -> list[Finding]:
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
```

Production helper:

```python
def _production_findings(project: DataProductProject, report: TrustReport) -> list[Finding]:
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
```

Regulated helper:

```python
def _regulated_findings(project: DataProductProject, report: TrustReport) -> list[Finding]:
    findings: list[Finding] = []
    missing_classification = sorted(
        field.name for field in project.contract.schema if not field.classification
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
```

- [x] **Step 6: Apply profile findings in suite validation**

In `src/dataproduct_kit/suite.py`, import and call `profile_findings` inside
`_validate_product`. Update its signature:

```python
def _validate_product(root: Path, product_dir: Path, profile: str) -> SuiteProductReport:
```

After `report = validate_project(project)`:

```python
profile_findings_list = profile_findings(project, report, profile)
findings = [*report.findings, *profile_findings_list]
errors = [finding for finding in findings if finding.level == "error"]
warnings = [finding for finding in findings if finding.level == "warning"]
status = "fail" if errors else "warn" if warnings else "pass"
summary = dict(report.summary)
summary["checks_failed"] = len(errors)
summary["checks_warned"] = len(warnings)
```

Return a `SuiteProductReport` using `findings` and `status`. If keeping
`trust_report`, update it with:

```python
trust_report=report.model_copy(update={"status": status, "findings": findings, "summary": summary})
```

- [x] **Step 7: Add regulated suite-level warning blocker**

After suppressions are applied and before computing final `status`, if profile is
`regulated`, add suite-level `Finding` for any unsuppressed warning:

```python
if config.ci.profile == "regulated":
    unsuppressed_warnings = [
        finding
        for product in products
        for finding in product.findings
        if finding.level == "warning" and not finding.suppressed
    ]
    if unsuppressed_warnings:
        config_findings.append(
            Finding(
                level="error",
                code="profile.unsuppressed_warning",
                message="regulated profile does not allow unsuppressed warnings",
            )
        )
```

- [x] **Step 8: Update known finding codes**

Add to `src/dataproduct_kit/finding_codes.py`:

```python
"profile.agent_constraints_missing",
"profile.agent_purpose_missing",
"profile.allowed_purposes_missing",
"profile.classification_missing",
"profile.quality_checks_missing",
"profile.semantic_metrics_missing",
"profile.sensitive_fields_missing",
"profile.unsuppressed_warning",
```

- [x] **Step 9: Run profile tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_profiles.py tests/test_ci.py tests/test_validation.py -q
```

Expected: pass.

- [x] **Step 10: Commit**

```bash
git add src/dataproduct_kit/profiles.py src/dataproduct_kit/suite.py src/dataproduct_kit/finding_codes.py tests/test_profiles.py tests/test_ci.py tests/test_validation.py
git commit -m "feat: apply readiness profile rules"
```

### Task 3: Harden Agent Context Safety

**Files:**
- Modify: `src/dataproduct_kit/context.py`
- Modify: `src/dataproduct_kit/finding_codes.py` if new codes are used
- Modify: `tests/test_reports_and_standards.py`
- Create/modify: `tests/test_context.py`

- [x] **Step 1: Write failing tests for denied agent context purpose**

Create `tests/test_context.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest
from conftest import write_valid_project


def test_agent_context_requires_agent_context_purpose(tmp_path: Path) -> None:
    from dataproduct_kit.context import build_agent_context
    from dataproduct_kit.loader import load_project
    from dataproduct_kit.validators import validate_project

    write_valid_project(tmp_path)
    policy = (tmp_path / "policy.yaml").read_text(encoding="utf-8")
    (tmp_path / "policy.yaml").write_text(
        policy.replace("  - agent_context\n", ""),
        encoding="utf-8",
    )

    project = load_project(tmp_path)

    with pytest.raises(ValueError, match="agent_context"):
        build_agent_context(project, validate_project(project), "churn_rate")
```

- [x] **Step 2: Write failing test for sensitive dimension exclusion**

Add:

```python
def test_agent_context_rejects_sensitive_dimensions(tmp_path: Path) -> None:
    from dataproduct_kit.context import build_agent_context
    from dataproduct_kit.loader import load_project
    from dataproduct_kit.validators import validate_project

    write_valid_project(tmp_path)
    semantic = (tmp_path / "semantic.yaml").read_text(encoding="utf-8")
    (tmp_path / "semantic.yaml").write_text(
        semantic.replace(
            "dimensions: [plan]",
            "dimensions: [customer_id]",
        ).replace(
            "  - name: plan\n    dataset: subscriptions\n    column: plan\n    type: string\n",
            "  - name: customer_id\n    dataset: subscriptions\n    column: customer_id\n    type: string\n",
        ),
        encoding="utf-8",
    )
    project = load_project(tmp_path)

    with pytest.raises(ValueError, match="sensitive"):
        build_agent_context(project, validate_project(project), "churn_rate")
```

- [x] **Step 3: Run tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_context.py -q
```

Expected: fail because context currently emits context without policy checks.

- [x] **Step 4: Implement context policy checks**

Modify `src/dataproduct_kit/context.py`:

```python
def build_agent_context(...):
    if "agent_context" not in project.policy.allowed_purposes:
        raise ValueError("policy does not allow agent_context purpose")
    ...
    sensitive_fields = set(project.policy.sensitive_fields)
    sensitive_dimensions = [
        dimension.name
        for dimension in project.semantic.dimensions
        if dimension.name in metric.dimensions and dimension.column in sensitive_fields
    ]
    if sensitive_dimensions:
        raise ValueError(
            "metric references sensitive dimension(s) not allowed for agent context: "
            + ", ".join(sorted(sensitive_dimensions))
        )
```

Keep output free of row-level values. Do not evaluate SQL expressions.

- [x] **Step 5: Add CLI context error regression**

Extend `tests/test_cli.py` with a runner test that removes `agent_context` from
`policy.yaml`, calls `context`, and asserts exit code `1` plus a clear message.

- [x] **Step 6: Run context and CLI tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_context.py tests/test_cli.py tests/test_reports_and_standards.py -q
```

Expected: pass.

- [x] **Step 7: Commit**

```bash
git add src/dataproduct_kit/context.py tests/test_context.py tests/test_cli.py tests/test_reports_and_standards.py
git commit -m "feat: enforce agent context policy"
```

### Task 4: Add Bring-Your-Own CSV Scaffolding

**Files:**
- Create: `src/dataproduct_kit/csv_scaffold.py`
- Modify: `src/dataproduct_kit/templates.py`
- Modify: `src/dataproduct_kit/cli.py`
- Create: `tests/test_csv_scaffold.py`
- Modify: `tests/test_cli.py`

- [x] **Step 1: Write failing unit test for CSV scaffold**

Create `tests/test_csv_scaffold.py`:

```python
from __future__ import annotations

from pathlib import Path

import yaml


def test_scaffold_from_csv_writes_starter_manifests(tmp_path: Path) -> None:
    from dataproduct_kit.csv_scaffold import scaffold_from_csv

    csv_path = tmp_path / "customers.csv"
    csv_path.write_text(
        "customer_id,email,created_at,total_spend\n"
        "cust_001,a@example.com,2026-06-01T00:00:00Z,42.5\n",
        encoding="utf-8",
    )
    out = tmp_path / "data-products/customers"

    scaffold_from_csv(csv_path, out)

    assert (out / "dataproduct.yaml").exists()
    assert (out / "contract.yaml").exists()
    assert (out / "semantic.yaml").exists()
    assert (out / "policy.yaml").exists()
    assert (out / "data/customers.csv").exists()
    product = yaml.safe_load((out / "dataproduct.yaml").read_text(encoding="utf-8"))
    contract = yaml.safe_load((out / "contract.yaml").read_text(encoding="utf-8"))
    policy = yaml.safe_load((out / "policy.yaml").read_text(encoding="utf-8"))
    assert product["owner"]["name"] == "TODO"
    assert contract["schema"][0]["name"] == "customer_id"
    assert policy["allowed_purposes"] == ["TODO"]
    assert "TODO" in policy["access_notes"]
```

- [x] **Step 2: Write failing CLI test**

Add to `tests/test_cli.py`:

```python
def test_cli_init_from_csv_generates_project(tmp_path: Path) -> None:
    from dataproduct_kit.cli import app

    runner = CliRunner()
    csv_path = tmp_path / "customers.csv"
    csv_path.write_text("customer_id,created_at\ncust_001,2026-06-01T00:00:00Z\n")
    out = tmp_path / "customers-product"

    result = runner.invoke(app, ["init", "from-csv", str(csv_path), "--out", str(out)])

    assert result.exit_code == 0, result.output
    assert (out / "dataproduct.yaml").exists()
    assert (out / "data/customers.csv").exists()
```

- [x] **Step 3: Run tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_csv_scaffold.py tests/test_cli.py::test_cli_init_from_csv_generates_project -q
```

Expected: fail because `csv_scaffold` and `init from-csv` do not exist.

- [x] **Step 4: Implement CSV inference and manifest writing**

Create `src/dataproduct_kit/csv_scaffold.py`:

```python
from __future__ import annotations

import csv
import shutil
from pathlib import Path
from typing import Any

import yaml


def scaffold_from_csv(csv_path: Path, out: Path) -> None:
    if not csv_path.exists():
        raise ValueError(f"CSV file not found: {csv_path}")
    rows = _sample_rows(csv_path)
    if not rows:
        raise ValueError(f"CSV file has no header row: {csv_path}")
    columns = list(rows[0].keys())
    dataset_id = _safe_name(csv_path.stem)
    out.mkdir(parents=True, exist_ok=True)
    data_dir = out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    target_csv = data_dir / csv_path.name
    shutil.copyfile(csv_path, target_csv)
    _write_yaml(out / "dataproduct.yaml", _product_payload(dataset_id, target_csv))
    _write_yaml(out / "contract.yaml", _contract_payload(dataset_id, columns, rows))
    _write_yaml(out / "semantic.yaml", {"metrics": [], "dimensions": [], "entities": []})
    _write_yaml(out / "policy.yaml", _policy_payload())
```

Helper payloads:

```python
def _sample_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))[:25]


def _contract_payload(dataset_id: str, columns: list[str], rows: list[dict[str, str]]) -> dict:
    return {
        "version": "0.1",
        "dataset": dataset_id,
        "schema": [
            {
                "name": column,
                "type": _infer_type([row.get(column, "") for row in rows]),
                "nullable": True,
                "classification": "TODO",
            }
            for column in columns
        ],
        "quality_checks": [
            {"name": "row_count_min", "type": "row_count_min", "value": 1},
        ],
    }
```

Use simple type inference only: boolean, integer, number, timestamp, string.
Avoid clever PII decisions; mark classifications as `TODO`.

- [x] **Step 5: Update Typer init command shape**

Current `init` command takes `path` and `--template`. To support subcommands
without breaking the existing demo path, convert `init` into a Typer group:

```python
init_app = typer.Typer(help="Scaffold demo or starter data products.")
app.add_typer(init_app, name="init")


@init_app.command("demo")
def init_demo(path: Path = Path("."), template: str = "saas-churn") -> None: ...


@init_app.command("from-csv")
def init_from_csv(csv_path: Path, out: Path = typer.Option(..., "--out")) -> None: ...
```

Preserve backwards compatibility by also accepting the current `dataproduct-kit
init <path> --template saas-churn` only if Typer supports it cleanly without
complex command hacks. If not, update docs and tests to the new `init demo`
shape in the same task.

- [x] **Step 6: Run CSV scaffold tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_csv_scaffold.py tests/test_cli.py -q
```

Expected: pass.

- [x] **Step 7: Commit**

```bash
git add src/dataproduct_kit/csv_scaffold.py src/dataproduct_kit/templates.py src/dataproduct_kit/cli.py tests/test_csv_scaffold.py tests/test_cli.py
git commit -m "feat: scaffold data products from CSV"
```

### Task 5: Add Doctor Diagnostics

**Files:**
- Create: `src/dataproduct_kit/doctor.py`
- Modify: `src/dataproduct_kit/cli.py`
- Create: `tests/test_doctor.py`
- Modify: `tests/test_cli.py`
- Modify: `src/dataproduct_kit/finding_codes.py` if doctor emits finding-like codes

- [x] **Step 1: Write failing doctor unit test**

Create `tests/test_doctor.py`:

```python
from __future__ import annotations

from pathlib import Path

from conftest import write_valid_project


def test_doctor_reports_production_gaps(tmp_path: Path) -> None:
    from dataproduct_kit.doctor import inspect_project

    write_valid_project(tmp_path)
    policy = (tmp_path / "policy.yaml").read_text(encoding="utf-8")
    (tmp_path / "policy.yaml").write_text(
        policy.replace(
            "agent_constraints:\n"
            "  - Agents may use the approved churn_rate metric only.\n"
            "  - Agents must include freshness and quality status with answers.\n",
            "agent_constraints: []\n",
        ),
        encoding="utf-8",
    )

    result = inspect_project(tmp_path)

    assert result["status"] == "warn"
    assert result["profile"] == "production"
    assert any("agent_constraints" in item for item in result["next_steps"])
```

- [x] **Step 2: Write failing CLI doctor test**

Add to `tests/test_cli.py`:

```python
def test_cli_doctor_outputs_next_steps(tmp_path: Path) -> None:
    from dataproduct_kit.cli import app

    runner = CliRunner()
    write_valid_project(tmp_path)

    result = runner.invoke(app, ["doctor", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "production readiness" in result.output
```

- [x] **Step 3: Run tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_doctor.py tests/test_cli.py::test_cli_doctor_outputs_next_steps -q
```

Expected: fail because doctor does not exist.

- [x] **Step 4: Implement doctor inspection**

Create `src/dataproduct_kit/doctor.py`:

```python
from __future__ import annotations

from pathlib import Path

from dataproduct_kit.loader import load_project
from dataproduct_kit.profiles import profile_findings
from dataproduct_kit.validators import validate_project


def inspect_project(path: Path, target_profile: str = "production") -> dict[str, object]:
    project = load_project(path)
    report = validate_project(project)
    findings = [*report.findings, *profile_findings(project, report, target_profile)]
    errors = [finding for finding in findings if finding.level == "error"]
    warnings = [finding for finding in findings if finding.level == "warning"]
    return {
        "profile": target_profile,
        "status": "fail" if errors else "warn" if warnings else "pass",
        "findings": [finding.model_dump(mode="json") for finding in findings],
        "next_steps": [_next_step(finding.code) for finding in findings],
    }
```

Keep `_next_step` deterministic and practical:

```python
def _next_step(code: str) -> str:
    mapping = {
        "profile.agent_constraints_missing": "Add agent_constraints to policy.yaml.",
        "profile.quality_checks_missing": "Add quality_checks to contract.yaml.",
        "freshness.missing": "Add a freshness policy to dataproduct.yaml.",
    }
    return mapping.get(code, f"Resolve finding {code}.")
```

- [x] **Step 5: Add CLI output**

In `src/dataproduct_kit/cli.py` add:

```python
@app.command()
def doctor(path: Path, profile: ReadinessProfile = "production", format: Literal["text", "json"] = "text") -> None:
    payload = inspect_project(path, profile)
    if format == "json":
        typer.echo(json.dumps(payload, indent=2, sort_keys=True) + "\n", nl=False)
        return
    typer.echo(f"production readiness: {payload['status']} ({payload['profile']})")
    for item in payload["next_steps"]:
        typer.echo(f"- {item}")
```

Catch `ManifestLoadError` the same way `_load_or_exit` does.

- [x] **Step 6: Run doctor tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_doctor.py tests/test_cli.py -q
```

Expected: pass.

- [x] **Step 7: Commit**

```bash
git add src/dataproduct_kit/doctor.py src/dataproduct_kit/cli.py tests/test_doctor.py tests/test_cli.py
git commit -m "feat: add production readiness doctor"
```

### Task 6: Update GitHub Action And Stable Output Contracts

**Files:**
- Modify: `action.yml`
- Modify: `src/dataproduct_kit/ci.py`
- Modify: `tests/test_ci.py`
- Modify: `tests/test_release_readiness.py`
- Create/modify: `docs/json-output.md`

- [x] **Step 1: Write failing action metadata test**

Update `tests/test_ci.py::test_action_metadata_runs_ci_command`:

```python
assert action["inputs"]["profile"]["default"] == "production"
assert '--profile "${{ inputs.profile }}"' in commands
```

- [x] **Step 2: Write failing JSON contract test**

Add to `tests/test_ci.py`:

```python
def test_ci_json_contains_stable_core_fields(tmp_path: Path) -> None:
    from dataproduct_kit.cli import app

    runner = CliRunner()
    write_valid_project(tmp_path / "products/pass")

    result = runner.invoke(
        app,
        ["ci", str(tmp_path), "--profile", "production", "--format", "json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    for field in ["status", "summary", "findings", "products", "profile", "config"]:
        assert field in payload
    assert payload["profile"] == "production"
    assert "policy" in payload["products"][0]["trust_report"]
```

- [x] **Step 3: Run tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_ci.py::test_action_metadata_runs_ci_command tests/test_ci.py::test_ci_json_contains_stable_core_fields -q
```

Expected: fail until action metadata and output profile are wired.

- [x] **Step 4: Update `action.yml`**

Add input:

```yaml
  profile:
    description: Readiness profile to apply.
    required: false
    default: "production"
```

Pass to command:

```bash
dataproduct-kit ci "${{ inputs.path }}" \
  --profile "${{ inputs.profile }}" \
  --format "${{ inputs.format }}" \
  --fail-on "${{ inputs.fail-on }}" \
  --sarif "${{ inputs.sarif }}"
```

- [x] **Step 5: Ensure JSON includes profile**

`render_json_suite` should already serialize `ValidationSuiteReport`. Confirm
`profile` appears at the top level. If not, update the model or renderer.

- [x] **Step 6: Add JSON compatibility docs**

Create `docs/json-output.md`:

```markdown
# JSON Output Compatibility

`dataproduct-kit` treats these top-level suite fields as stable for v1:

- `status`
- `summary`
- `findings`
- `products`
- `profile`
- `config`

Each `products[*].trust_report.policy` object is also part of the stable v1
automation contract for data-product policy evidence.

Minor releases may add fields. They will not remove or rename these core fields
without a major version.
```

- [x] **Step 7: Run action/output tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_ci.py tests/test_release_readiness.py -q
```

Expected: pass.

- [x] **Step 8: Commit**

```bash
git add action.yml src/dataproduct_kit/ci.py src/dataproduct_kit/models.py tests/test_ci.py tests/test_release_readiness.py docs/json-output.md
git commit -m "feat: expose readiness profiles in CI outputs"
```

### Task 7: Update Documentation For v1 Identity And Adoption

**Files:**
- Modify: `README.md`
- Modify: `docs/ci-adoption.md`
- Create: `docs/readiness-profiles.md`
- Create: `docs/from-csv.md`
- Modify: `docs/finding-codes.md`
- Modify: `docs/suppressions.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Modify: `tests/test_release_readiness.py`

- [x] **Step 1: Write failing docs presence test**

Add to `tests/test_release_readiness.py`:

```python
def test_v1_docs_cover_profiles_from_csv_and_json_contract() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    profiles = (ROOT / "docs/readiness-profiles.md").read_text(encoding="utf-8")
    from_csv = (ROOT / "docs/from-csv.md").read_text(encoding="utf-8")
    json_output = (ROOT / "docs/json-output.md").read_text(encoding="utf-8")

    assert "open source CI gate for agent-safe data products" in readme
    assert "dataproduct-kit init from-csv" in readme
    assert "starter" in profiles and "production" in profiles and "regulated" in profiles
    assert "TODO" in from_csv
    assert "status" in json_output and "products" in json_output
```

- [x] **Step 2: Run docs test and verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/test_release_readiness.py::test_v1_docs_cover_profiles_from_csv_and_json_contract -q
```

Expected: fail until docs exist and README is updated.

- [x] **Step 3: Update README**

Revise the opening description to:

```markdown
`dataproduct-kit` is the open source CI gate for agent-safe data products.
It validates contracts, quality checks, freshness, semantic metrics, policy
constraints, and evidence outputs before AI agents consume data-product context.
```

Add current v1 quickstart:

```bash
pipx install dataproduct-kit
dataproduct-kit init demo --template saas-churn
dataproduct-kit ci demo --profile starter
dataproduct-kit report demo --format markdown
dataproduct-kit context demo --metric churn_rate --format json
```

Add BYO CSV quickstart:

```bash
dataproduct-kit init from-csv data/customers.csv --out data-products/customers
dataproduct-kit doctor data-products/customers
dataproduct-kit ci data-products/customers --profile starter
```

- [x] **Step 4: Create readiness profile docs**

Create `docs/readiness-profiles.md` with:

- Purpose of profiles.
- `starter`, `production`, `regulated` behavior.
- Recommended local profile: `starter`.
- Recommended GitHub Action profile: `production`.
- Regulated caveat: use only when teams can maintain full classifications and warning-free gates.

- [x] **Step 5: Create from-csv docs**

Create `docs/from-csv.md` with:

- Command syntax.
- What is inferred.
- What remains `TODO`.
- How to run `doctor`.
- How to graduate from `starter` to `production`.

- [x] **Step 6: Update CI adoption docs**

Modify `docs/ci-adoption.md` GitHub Action example to include:

```yaml
profile: "production"
```

Explain `starter` versus `production`.

- [x] **Step 7: Update finding codes docs**

Add all `profile.*` finding codes to `docs/finding-codes.md`.

- [x] **Step 8: Update roadmap and changelog**

Update `ROADMAP.md` so v1 production readiness includes:

- Readiness profiles.
- CSV onboarding.
- Doctor command.
- Stable JSON output.

Update `CHANGELOG.md` under Unreleased with the same user-facing bullets.

- [x] **Step 9: Run docs tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_release_readiness.py -q
```

Expected: pass.

- [x] **Step 10: Commit**

```bash
git add README.md docs/ci-adoption.md docs/readiness-profiles.md docs/from-csv.md docs/finding-codes.md docs/suppressions.md ROADMAP.md CHANGELOG.md tests/test_release_readiness.py
git commit -m "docs: document v1 production readiness workflow"
```

### Task 8: Full Verification And Release Readiness

**Files:**
- Modify only if verification reveals defects:
  - `scripts/verify.sh`
  - `scripts/smoke-install.sh`
  - relevant tests or docs

- [x] **Step 1: Run focused feature tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_profiles.py tests/test_context.py tests/test_csv_scaffold.py tests/test_doctor.py tests/test_ci.py tests/test_cli.py -q
```

Expected: all pass.

- [x] **Step 2: Run full test suite**

Run:

```bash
.venv/bin/python -m pytest
```

Expected: all pass.

- [x] **Step 3: Run Ruff**

Run:

```bash
.venv/bin/python -m ruff check .
```

Expected: no lint errors.

- [x] **Step 4: Run pip check**

Run:

```bash
.venv/bin/python -m pip check
```

Expected: no broken requirements.

- [x] **Step 5: Run release verification script**

Run:

```bash
PYTHON=.venv/bin/python ./scripts/verify.sh
```

Expected: pytest, Ruff, pip check, build, twine check, and wheel smoke install pass.

- [x] **Step 6: Manually verify v1 quickstarts**

Use a temp directory:

```bash
tmpdir="$(mktemp -d)"
cd "$tmpdir"
python3 -m venv .venv
.venv/bin/python -m pip install /Users/johnmikelregida/Desktop/projects/dataproduct-kit/dist/dataproduct_kit-*.whl
.venv/bin/dataproduct-kit init demo --template saas-churn
.venv/bin/dataproduct-kit ci demo --profile starter
.venv/bin/dataproduct-kit report demo --format markdown
printf 'customer_id,created_at\ncust_001,2026-06-01T00:00:00Z\n' > customers.csv
.venv/bin/dataproduct-kit init from-csv customers.csv --out data-products/customers
.venv/bin/dataproduct-kit doctor data-products/customers
.venv/bin/dataproduct-kit ci data-products/customers --profile starter
```

Expected: demo passes; CSV scaffold commands run and produce actionable starter output.

- [x] **Step 7: Fix any verification defects**

If any verification fails, write the smallest failing regression test, fix the
defect, rerun the failing command, then rerun full verification.

- [x] **Step 8: Final commit**

If verification caused changes:

```bash
git status --short
git add path/to/changed-file path/to/another-changed-file
git commit -m "chore: verify v1 production readiness"
```

If no changes were needed, do not create an empty commit.

## Final Acceptance Checklist

- [ ] `dataproduct-kit ci` supports `--profile starter|production|regulated`.
- [ ] `dataproduct-kit.toml` supports `[ci].profile`.
- [ ] GitHub Action supports `profile` and defaults to `production`.
- [ ] Suite JSON includes stable core fields including `profile`.
- [ ] Profile-specific findings are stable and documented.
- [ ] Agent context refuses policy-disallowed context.
- [ ] `init from-csv` generates starter manifests with TODO governance.
- [ ] `doctor` explains production gaps.
- [ ] README leads with the v1 CI-gate identity.
- [ ] Docs cover profiles, CSV onboarding, JSON output, CI adoption, suppressions, and finding codes.
- [ ] Full verification passes.
