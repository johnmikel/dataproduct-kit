# dataproduct-kit

[![CI](https://github.com/johnmikel/dataproduct-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/johnmikel/dataproduct-kit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/dataproduct-kit.svg)](https://pypi.org/project/dataproduct-kit/)
[![Python](https://img.shields.io/pypi/pyversions/dataproduct-kit.svg)](https://pypi.org/project/dataproduct-kit/)
[![License](https://img.shields.io/pypi/l/dataproduct-kit.svg)](LICENSE)

`dataproduct-kit` is the open source CI gate for agent-safe data products.
It validates contracts, quality checks, freshness, semantic metrics, policy
constraints, and evidence outputs before AI agents consume data-product context.

## Why this exists

Enterprise data products are increasingly consumed by BI users, platform teams,
and AI agents. The hard part is not just finding data; it is knowing whether the
data has an owner, a contract, a stable metric definition, quality checks,
freshness context, lineage, and policy constraints.

`dataproduct-kit` makes that trust context explicit and testable in a local repo.

## Install

For CLI use, `pipx` keeps `dataproduct-kit` isolated from project dependencies:

```bash
pipx install dataproduct-kit
```

You can also install it into an existing Python environment:

```bash
python -m pip install dataproduct-kit
```

For local branch testing and contribution work, use the editable install in
[Develop locally](#develop-locally).

## Quickstart

```bash
dataproduct-kit init demo demo --template saas-churn
dataproduct-kit ci demo --profile starter
dataproduct-kit report demo --format markdown
dataproduct-kit context demo --metric churn_rate --format json
```

## Bring your own CSV

```bash
dataproduct-kit init from-csv data/customers.csv --out data-products/customers
dataproduct-kit doctor data-products/customers
dataproduct-kit ci data-products/customers --profile starter
```

The CSV scaffold creates starter manifests with inferred columns and TODO
governance fields. See [docs/from-csv.md](docs/from-csv.md) for the graduation
path from a local starter to a production gate.

## Import from dbt

```bash
dataproduct-kit init from-dbt target/manifest.json --model fct_orders --out data-products/fct-orders
```

The dbt scaffold reads model and column metadata from `manifest.json`, maps dbt
column types into a starter contract, and creates TODO governance fields. It
does not connect to the warehouse or export data; replace the generated
`data/<model>.csv` path or add a local sample before validating the product.

## Develop locally

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

## Try the SaaS churn demo

```bash
dataproduct-kit init demo demo --template saas-churn
dataproduct-kit ci demo --profile starter
dataproduct-kit report demo --format markdown
dataproduct-kit context demo --metric churn_rate --format json
dataproduct-kit export odcs demo
dataproduct-kit export osi demo
dataproduct-kit emit openlineage demo
```

You can also validate with machine-readable output:

```bash
dataproduct-kit validate demo --format json
dataproduct-kit validate demo --fail-on warn
```

Expected validation output:

```text
status: pass
```

The Markdown report starts like this:

```markdown
# Trust Report: SaaS Churn Data Product

| Field | Value |
| --- | --- |
| Product ID | saas_churn |
| Overall status | pass |
```

## Manifest model

A data product directory contains four source-of-truth files:

- `dataproduct.yaml`: product identity, owner, datasets, freshness SLA.
- `contract.yaml`: schema fields, classifications, and built-in quality checks.
- `semantic.yaml`: approved metrics, dimensions, entities, and expressions.
- `policy.yaml`: allowed purposes, sensitive fields, and AI/BI usage constraints.

The bundled demo uses local CSV data and DuckDB, so it needs no cloud account or
running database.

Generate JSON Schema for editor integration or manifest authoring:

```bash
dataproduct-kit schema dataproduct
dataproduct-kit schema all --out schemas
```

## Validate

```bash
dataproduct-kit validate demo
```

The command exits with `0` for `pass` or `warn`, and `1` for `fail`.

For repository-wide pull request checks, use the CI command:

```bash
dataproduct-kit ci . --profile production --format text
dataproduct-kit ci . --profile production --format github --fail-on warn --sarif dataproduct-kit.sarif.json
```

The CI command discovers every directory containing `dataproduct.yaml` below the
path, validates each data product, emits a suite summary, and can write SARIF for
audit evidence or code-scanning upload. Use `starter` for local onboarding and
`production` for pull request gates; see
[docs/readiness-profiles.md](docs/readiness-profiles.md) for the full profile
behavior.

Repository defaults can live in `dataproduct-kit.toml`:

```toml
[ci]
include = ["data-products/**"]
exclude = ["data-products/sandbox/**"]
profile = "production"
fail_on = "warn"
```

You can also use the bundled GitHub Action. See the
[Copy-paste GitHub Action quickstart](docs/ci-adoption.md#copy-paste-github-action-quickstart)
for a complete pull request workflow with SARIF upload:

```yaml
- uses: johnmikel/dataproduct-kit@v0.4.0
  with:
    path: "."
    profile: "production"
    fail-on: "warn"
    format: "github"
    sarif: "dataproduct-kit.sarif.json"
```

## Reports and agent context

```bash
dataproduct-kit report demo --format json
dataproduct-kit report demo --format markdown
dataproduct-kit context demo --metric churn_rate --format json
```

The context command returns metric definition, freshness, policy, and lineage
metadata. It deliberately does not answer business questions or generate SQL.

Example context fields:

```json
{
  "metric": {
    "name": "churn_rate",
    "dataset": "subscriptions",
    "grain": "month"
  },
  "quality_status": "pass"
}
```

## Standards outputs

```bash
dataproduct-kit export odcs demo
dataproduct-kit export osi demo
dataproduct-kit emit openlineage demo
```

Exports are standards-aligned from the local profile:

- ODCS-compatible data contract JSON.
- OSI-inspired semantic model JSON.
- OpenLineage-compatible validation event JSONL.

Use `--out` to write standards exports to files:

```bash
dataproduct-kit export odcs demo --out contract.json
dataproduct-kit export osi demo --out semantic.json
```

## What this catches

The validator returns `fail` for issues such as:

- Missing required columns.
- Values that cannot cast to the declared contract type.
- Null or blank values in non-nullable fields.
- Failed quality checks such as uniqueness, accepted values, and row count.
- Stale data based on the dataset freshness SLA.
- Metrics that reference unknown dimensions or invalid expressions.
- Policy fields that reference columns not declared in the contract.

Runnable examples live under `examples/`:

- `examples/pass/saas-churn`
- `examples/pass/finance-revenue`
- `examples/pass/healthcare-appointments`
- `examples/fail/schema-drift`
- `examples/fail/stale-data`
- `examples/fail/broken-metric`
- `examples/fail/policy-gap`

See [docs/usage-scenarios.md](docs/usage-scenarios.md) for concrete usage
scenarios. See [docs/ci-adoption.md](docs/ci-adoption.md) for pull request gate
setup, [docs/readiness-profiles.md](docs/readiness-profiles.md) for profile
behavior, [docs/from-csv.md](docs/from-csv.md) for CSV onboarding,
[docs/json-output.md](docs/json-output.md) for the stable automation contract,
[docs/finding-codes.md](docs/finding-codes.md) for stable finding codes, and
[docs/suppressions.md](docs/suppressions.md) for expiring exceptions. See
[docs/compatibility.md](docs/compatibility.md) for supported automation surfaces
and [docs/ci-rollout.md](docs/ci-rollout.md) for a staged production rollout.
Maintainer release notes live in [docs/publishing.md](docs/publishing.md) and
[docs/release-checklist.md](docs/release-checklist.md).

## Project status

The current public release is `v0.4.0` on PyPI. The local CLI, SaaS churn demo,
CSV scaffold, readiness profiles, CI JSON output, GitHub Action, and report
generation are usable. The manifest profile and standards exports may still
evolve before a stable `v1.0` release.

See [ROADMAP.md](ROADMAP.md) for planned standards depth, ecosystem adapters,
and agent/platform integrations.

## Verify

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m pip check
./scripts/verify.sh
```
