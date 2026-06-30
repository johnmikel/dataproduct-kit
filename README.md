# dataproduct-kit

[![CI](https://github.com/johnmikel/dataproduct-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/johnmikel/dataproduct-kit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/dataproduct-kit.svg)](https://pypi.org/project/dataproduct-kit/)
[![Python](https://img.shields.io/pypi/pyversions/dataproduct-kit.svg)](https://pypi.org/project/dataproduct-kit/)
[![License](https://img.shields.io/pypi/l/dataproduct-kit.svg)](LICENSE)

**A CLI and GitHub Action that turn data-product trust — contracts, quality, freshness, semantics, and policy — into a testable CI gate, before BI users or AI agents ever consume the data.**

`dataproduct-kit` treats a data product as a versioned artifact with a contract, not a table you discover after the fact. You declare a product in four manifest files, and the tool runs real SQL-backed checks against your data, produces a pass/warn/fail trust report with stable finding codes, and fails your pull request when the product drifts out of contract — the same shift-left discipline teams already apply to application code.

## Why this exists

Enterprise data is increasingly consumed not just by analysts and dashboards, but by platform teams and LLM agents. The hard problem is no longer *finding* data — it is knowing whether a dataset has an owner, a stable schema contract, agreed metric definitions, quality and freshness guarantees, and policy constraints on how it may be used.

Most tooling answers that *after* the data is published: catalogs, observability dashboards, and incident alerts that fire once something already broke. `dataproduct-kit` moves the trust check left. It makes the contract explicit in the repository and enforces it in CI, so a broken schema, a stale dataset, an undefined metric, or a policy gap fails the build the same way a failing unit test does.

It is deliberately scoped. It does **not** answer natural-language questions, generate SQL, sync to a live catalog, or hand an agent row-level access. Those are explicit non-goals (see [Project status](#project-status)). The product is the trust gate itself.

## Install

For CLI use, `pipx` keeps the tool isolated from your project's dependencies:

```bash
pipx install dataproduct-kit
```

Or install into an existing environment:

```bash
python -m pip install dataproduct-kit
```

Requires Python 3.11+. Published on [PyPI](https://pypi.org/project/dataproduct-kit/) (current release: `0.4.0`).

## Quickstart

Scaffold the bundled SaaS-churn demo, gate it, and inspect the report. The demo ships with local CSV data and runs entirely on an in-memory DuckDB — no cloud account or running database required.

```bash
dataproduct-kit init demo demo --template saas-churn   # scaffold a data product
dataproduct-kit validate demo                          # -> status: pass (exit 0)
dataproduct-kit ci demo --profile starter              # repo-style suite check
dataproduct-kit report demo --format markdown          # human-readable trust report
dataproduct-kit context demo --metric churn_rate --format json
```

`validate` exits `0` for `pass`/`warn` and `1` for `fail`, so it drops straight into any CI runner. (Pass `--fail-on warn` to also fail on warnings.)

## How it works

A data product is a directory with four source-of-truth manifests:

| File               | Declares                                                            |
| ------------------ | ------------------------------------------------------------------ |
| `dataproduct.yaml` | Product identity, owner, datasets, and freshness SLA               |
| `contract.yaml`    | Schema fields, classifications, and built-in quality checks        |
| `semantic.yaml`    | Approved metrics, dimensions, entities, and their expressions      |
| `policy.yaml`      | Allowed purposes, sensitive fields, and AI/BI usage constraints    |

The validation engine loads the declared local CSV data into **in-memory DuckDB** and runs real SQL-backed checks rather than static linting:

- **Schema** — required-column presence, type-castability against the declared contract, null/blank values in non-nullable fields.
- **Quality** — `unique`, `not_null`, `accepted_values`, `min`/`max`, `expression`, and `row_count_min` checks executed over the data.
- **Freshness** — measured against the dataset's declared SLA.
- **Semantics** — metrics, dimensions, and entities that reference unknown datasets/columns, or metrics with invalid SQL expressions.
- **Policy** — sensitive fields that reference columns absent from the contract, plus missing allowed purposes or access notes.

Every issue is emitted as a finding with a **stable, machine-readable code** — `schema.missing_column`, `schema.type_mismatch`, `freshness.stale`, `semantic.unknown_dimension`, `policy.unknown_sensitive_field`, and others — so CI gates, dashboards, and policy exceptions can key off codes that stay compatible across the `0.x` line. The result is a `TrustReport` with an overall `pass` / `warn` / `fail` status. See [docs/finding-codes.md](docs/finding-codes.md) for the full taxonomy.

```
manifests (yaml) ──► loader ──► DuckDB (in-memory, local CSV)
                                   │
       schema · quality · freshness · semantic · policy validators
                                   │
                            TrustReport (pass/warn/fail + finding codes)
                                   │
        validate (text/json) · report (json/markdown) · ci (text/github/json + SARIF) · context · exports
```

## CI gate

The `ci` command discovers every directory containing a `dataproduct.yaml` below a path, validates each product, and emits a suite summary. It supports multiple output formats and can write **SARIF** for upload to code scanning.

```bash
dataproduct-kit ci . --profile production --format text
dataproduct-kit ci . --profile production --format github --fail-on warn --sarif dataproduct-kit.sarif.json
```

Readiness profiles control strictness: `starter` for local onboarding, `production` for pull-request gates, and `regulated` for the strictest governance posture. The `doctor` command reports which gaps stand between a product and a higher profile:

```bash
dataproduct-kit doctor data-products/customers --profile production
```

Repository defaults can live in `dataproduct-kit.toml`:

```toml
[ci]
include = ["data-products/**"]
exclude = ["data-products/sandbox/**"]
profile = "production"
fail_on = "warn"
```

### GitHub Action

A reusable composite action wraps the CLI:

```yaml
# Pin to a published tag/ref of this repository.
- uses: johnmikel/dataproduct-kit@v0.4.0
  with:
    path: "."
    profile: "production"
    fail-on: "warn"
    format: "github"
    sarif: "dataproduct-kit.sarif.json"
```

See [docs/ci-adoption.md](docs/ci-adoption.md) for a complete pull-request workflow with SARIF upload, and [docs/ci-rollout.md](docs/ci-rollout.md) for staging the gate into an existing repo.

## Onboarding existing data

You rarely start from a template. Two scaffolds bootstrap manifests from data you already have:

```bash
# From any CSV: infers columns and stubs TODO governance fields
dataproduct-kit init from-csv data/customers.csv --out data-products/customers

# From a dbt manifest: reads model + column metadata from manifest.json
dataproduct-kit init from-dbt target/manifest.json --model fct_orders --out data-products/fct-orders
```

The dbt scaffold reads metadata from `manifest.json` only — it does not connect to a warehouse or export data. Point the generated `data/<model>.csv` path at a local sample before validating. See [docs/from-csv.md](docs/from-csv.md) for the graduation path from a local starter to a production gate.

## Agent-safe context

The `context` command returns the metadata an agent or BI tool needs to use a metric responsibly — its definition, freshness, governing policy, and lineage:

```bash
dataproduct-kit context demo --metric churn_rate --format json
```

By design, it returns *metadata only*. It does not answer business questions and does not generate SQL — a deliberate governance stance that keeps the trust boundary explicit. The context bundle also enforces policy: it requires the metric's product to allow the `agent_context` purpose and refuses to emit metrics that expose sensitive dimensions. An MCP server and warehouse-backed agent integrations are roadmap items, not current behavior.

## Standards-aligned exports

The same local profile can be exported into the open data-product ecosystem's interchange formats:

```bash
dataproduct-kit export odcs demo          # ODCS-compatible data contract JSON
dataproduct-kit export osi demo           # OSI-inspired semantic model JSON
dataproduct-kit emit openlineage demo     # OpenLineage-compatible validation events (JSONL)
```

These are *compatible/inspired* shapes derived from the local profile; the payloads tag themselves accordingly (e.g. ODCS `apiVersion: v3.1.0-compatible`) and are not yet certified against the published ODCS, OSI, or OpenLineage schemas. Tightening that compatibility is on the [roadmap](ROADMAP.md). You can also generate JSON Schema for the manifest files to power editor autocompletion and validation:

```bash
dataproduct-kit schema dataproduct
dataproduct-kit schema all --out schemas
```

## What it catches

The validator returns `fail` for issues such as:

- Missing required columns, or values that cannot cast to the declared contract type.
- Null or blank values in non-nullable fields.
- Failed quality checks — uniqueness, accepted values, min/max, row-count, expressions.
- Data that is stale against its dataset freshness SLA.
- Metrics that reference unknown dimensions or invalid expressions.
- Policy fields that reference columns not declared in the contract.

Runnable pass/fail examples live under [`examples/`](examples):

```
examples/pass/saas-churn                examples/fail/schema-drift
examples/pass/finance-revenue           examples/fail/stale-data
examples/pass/healthcare-appointments   examples/fail/broken-metric
                                        examples/fail/policy-gap
```

Each `examples/fail/*` product fails with the precise finding code for its defect (`schema.missing_column`, `freshness.stale`, `semantic.unknown_dimension`, `policy.unknown_sensitive_field`).

## Project status

**Alpha (`v0.4.0` on PyPI).** The local CLI, the SaaS-churn demo, CSV and dbt scaffolds, readiness profiles, the `doctor`/`report`/`context` commands, repo-wide CI with JSON/SARIF output, and the GitHub Action are all usable today. The manifest profile and standards exports may still evolve before a stable `v1.0`.

Honest caveats worth knowing before you adopt it:

- **Local-only validation.** Checks run over local CSV via DuckDB. There is no warehouse connectivity yet — the enterprise framing is currently a demo-scale proof of concept (warehouse-backed demos are on the roadmap).
- **Standards exports are compatible, not certified.** See [Standards-aligned exports](#standards-aligned-exports).
- **No live agent integration.** "Agent-safe context" is a metadata-only JSON command; an MCP server is a roadmap item (v0.6).

Explicit **non-goals** for v1, by design: natural-language querying, text-to-SQL execution, live catalog sync, cloud credentials, and agent access to row-level data. See [ROADMAP.md](ROADMAP.md).

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Verify a working tree:

```bash
.venv/bin/python -m pytest        # test suite (80 tests)
.venv/bin/python -m ruff check .  # lint
./scripts/verify.sh               # full local gate
```

The project is CI-gated across Python 3.11 / 3.12 / 3.13, builds and `twine check`s the package, smoke-tests the built wheel, and publishes to PyPI via trusted publishing (OIDC). Contribution guidelines are in [CONTRIBUTING.md](CONTRIBUTING.md); security policy in [SECURITY.md](SECURITY.md).

## Documentation

| Topic                         | Doc                                                      |
| ----------------------------- | -------------------------------------------------------- |
| Usage scenarios               | [docs/usage-scenarios.md](docs/usage-scenarios.md)       |
| CI adoption + PR gate         | [docs/ci-adoption.md](docs/ci-adoption.md)               |
| Staged CI rollout             | [docs/ci-rollout.md](docs/ci-rollout.md)                 |
| Readiness profiles            | [docs/readiness-profiles.md](docs/readiness-profiles.md) |
| CSV onboarding                | [docs/from-csv.md](docs/from-csv.md)                     |
| Stable finding codes          | [docs/finding-codes.md](docs/finding-codes.md)           |
| JSON automation contract      | [docs/json-output.md](docs/json-output.md)               |
| Expiring suppressions         | [docs/suppressions.md](docs/suppressions.md)             |
| Automation surfaces           | [docs/compatibility.md](docs/compatibility.md)           |

## License

Apache-2.0. See [LICENSE](LICENSE).
