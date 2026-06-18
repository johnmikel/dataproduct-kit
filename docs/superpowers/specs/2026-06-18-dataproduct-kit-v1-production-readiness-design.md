# dataproduct-kit v1 Production Readiness Design

Date: 2026-06-18
Status: Approved for specification

## Summary

`dataproduct-kit` v1 will be the open source CI gate for proving whether a data
product is safe for AI agents to consume. The product is local-first and
CI-first: it validates repository-owned data product manifests, sample data, and
policy context without requiring cloud credentials, live catalog sync, or access
to production warehouses.

The primary user is an AI or data platform engineer who needs a pull-request
gate for agent-ready data products. The tool must answer one production
question clearly: can this data product be trusted by an agent without exposing
unsafe, stale, undocumented, or ungoverned data context?

## Goals

- Make `dataproduct-kit ci` and the GitHub Action the main production workflow.
- Provide a 10-minute demo path that proves the full validation, report, export,
  and context loop works locally.
- Provide a bring-your-own CSV onboarding path that generates starter manifests
  with explicit suggested or unknown fields, not false governance claims.
- Add named readiness profiles: `starter`, `production`, and `regulated`.
- Keep validation deterministic, local, and suitable for repeatable CI runs.
- Treat core JSON fields as the stable automation contract for v1.
- Keep agent context policy-aware and free of row-level data.

## Non-goals

- No MCP server in v1.
- No natural-language querying.
- No text-to-SQL generation or execution.
- No live catalog sync.
- No cloud warehouse credentials.
- No row-level data access for agents.
- No numeric readiness score or bronze/silver/gold maturity score in v1.

## Product Identity

The v1 positioning is:

> `dataproduct-kit` is the open source CI gate for agent-safe data products.

The tool should be easy for a newcomer to try, but production credibility comes
from deterministic gates, stable finding codes, explicit governance, and
machine-readable evidence.

The CLI remains useful outside CI, but every user-facing workflow should lead
toward repository validation:

- `dataproduct-kit init demo --template saas-churn`
- `dataproduct-kit init from-csv data/customers.csv --out data-products/customers`
- `dataproduct-kit doctor data-products/customers`
- `dataproduct-kit ci data-products --profile production`
- `dataproduct-kit report data-products/customers --format markdown`
- `dataproduct-kit context data-products/customers --metric customer_count`

## Readiness Profiles

Profiles define how strict the gate is. They do not hide findings. Relaxed
requirements remain visible as warnings, suppressions, or profile metadata in
machine-readable output.

### starter

`starter` is optimized for local onboarding and first adoption.

It blocks:

- Invalid or unreadable manifests.
- Missing data product directories.
- Missing declared data files.
- CSV read errors.
- Schema drift against declared contract fields.
- Type mismatches for declared non-string fields.
- Failed declared quality checks.
- Semantic references to unknown datasets, dimensions, entities, or columns.
- Policy references to unknown contract fields.

It warns for:

- Missing freshness policy.
- Missing quality checks.
- Empty semantic metrics.
- Empty `agent_constraints`.
- Empty `sensitive_fields` when fields are classified as confidential,
  restricted, sensitive, or personally identifying.

### production

`production` is the recommended CI profile for real data product repositories.

It blocks everything `starter` blocks, plus:

- Missing owner name, team, or valid email.
- Missing freshness policy for datasets used by a contract.
- Missing quality checks.
- Missing allowed purposes.
- Missing `agent_context` or an equivalent approved agent purpose.
- Missing `agent_constraints`.
- Sensitive or confidential contract fields not declared in policy.
- Agent context for a metric whose dataset or dimensions include undeclared
  sensitive fields.

### regulated

`regulated` is for teams that need stricter audit evidence.

It blocks everything `production` blocks, plus:

- Any unsuppressed warning.
- Expired or invalid suppressions.
- Missing field classifications.
- Sensitive fields without explicit access notes.
- Missing report, SARIF, and OpenLineage-compatible evidence when running in
  CI mode with evidence output configured.

## Configuration

Repository configuration lives in `dataproduct-kit.toml`.

```toml
[ci]
profile = "production"
include = ["data-products/**"]
exclude = ["data-products/sandbox/**"]
fail_on = "warn"

[[suppressions]]
code = "freshness.stale"
path = "data-products/growth/saas-churn"
reason = "Producer backfill scheduled in the current sprint."
expires = "2026-08-01"
```

Command-line options override config for a single run. The GitHub Action exposes
`profile`, `path`, `fail-on`, `format`, `sarif`, and `python-version` inputs.

## First-run Experience

The first-run experience is demo-first, followed immediately by a bring-your-own
CSV path.

Demo path:

```bash
pipx install dataproduct-kit
dataproduct-kit init demo --template saas-churn
dataproduct-kit ci demo --profile starter
dataproduct-kit report demo --format markdown
dataproduct-kit context demo --metric churn_rate --format json
```

Bring-your-own CSV path:

```bash
dataproduct-kit init from-csv data/customers.csv --out data-products/customers
dataproduct-kit doctor data-products/customers
dataproduct-kit ci data-products/customers --profile starter
```

`init from-csv` may infer column names, basic data types, row-count checks, and
candidate freshness columns. It must mark inferred governance fields as
`unknown`, `suggested`, or clearly human-editable. It must not claim an owner,
approved purpose, sensitive-field policy, or agent constraint has been confirmed
unless the user supplied it explicitly.

`doctor` explains what is present, what is inferred, and what must be completed
to pass `production`.

## Architecture

The existing module structure remains the foundation. v1 adds focused layers
without turning the project into a platform.

### Manifest layer

Pydantic models define the local manifest profile:

- `dataproduct.yaml`
- `contract.yaml`
- `semantic.yaml`
- `policy.yaml`
- `dataproduct-kit.toml`

These models remain strict by default. Unknown fields should fail fast unless a
specific extension field is introduced and documented.

### Project loader

The loader reads YAML files, validates them with Pydantic, and returns a
`DataProductProject`. It remains local and deterministic. Load errors should
include the file and field path where possible.

### Validation engine

The validator checks data, contract, semantic, freshness, and policy rules and
returns structured findings. It does not know about GitHub Actions, SARIF,
Markdown formatting, or CLI presentation.

### Readiness profile layer

The profile layer maps validation results and required governance evidence to a
profile-specific outcome. It can add findings for missing evidence that is only
required in stricter profiles.

### Suite runner

The suite runner discovers data product directories, loads config, runs
validation, applies readiness profiles, applies suppressions, and aggregates
repository-level results.

### Output adapters

Output adapters render the same underlying report objects as:

- Text summaries.
- Stable JSON.
- GitHub annotations.
- SARIF.
- Markdown trust reports.
- ODCS-compatible contract JSON.
- OSI-inspired semantic JSON.
- OpenLineage-compatible validation events.

### Scaffolding helpers

Scaffolding helpers are separate from validation. They may infer starter content
but must not make production governance claims.

### Agent context builder

The agent context builder emits approved metric, freshness, quality, policy, and
lineage context. It does not emit row-level data or answer business questions.

## Data Flow

For `dataproduct-kit ci`:

1. Load repository config from `dataproduct-kit.toml`.
2. Discover directories containing `dataproduct.yaml` using include/exclude
   patterns.
3. Load each data product's manifests.
4. Validate data, schema, quality, freshness, semantic references, and policy.
5. Apply the selected readiness profile.
6. Apply valid, unexpired suppressions.
7. Aggregate product reports into a suite report.
8. Render requested output formats.
9. Exit according to suite status and `fail_on`.

For `dataproduct-kit context`:

1. Load one data product.
2. Validate the project.
3. Resolve the requested metric.
4. Confirm policy permits agent context for the metric.
5. Emit metric, dimension, freshness, quality, policy, and lineage metadata.
6. Exclude row-level data and sensitive fields not approved for agent context.

For `init from-csv`:

1. Read a local CSV file with DuckDB or the standard CSV parser.
2. Infer column names and simple data types.
3. Generate four starter manifests and copy or reference the CSV.
4. Mark unconfirmed governance as unknown or suggested.
5. Print next-step guidance using `doctor`.

## Error Handling And Output Contracts

The v1 exit-code contract is:

- `0`: selected profile and `fail_on` policy allow the result.
- `1`: validation failed the selected gate.
- `2`: invalid CLI usage or invalid configuration.

Every finding includes:

- `level`
- `code`
- `message`
- optional `check`
- optional suppression metadata
- source manifest mapping through output adapters

Core JSON fields are stable for v1 automation:

- `status`
- `summary`
- `findings`
- `products`
- `profile`
- `policy`

Additional fields may be added in minor releases. Existing core field names and
types should not change without a major version.

## Testing Strategy

The test suite should cover:

- CLI smoke paths for demo initialization, validation, reports, context, export,
  emit, and CI.
- `init from-csv` generation over representative CSV input.
- `doctor` output for starter manifests and production gaps.
- Profile behavior for `starter`, `production`, and `regulated`.
- Suppression handling, including expired and unknown-code suppressions.
- Stable JSON snapshots or targeted contract assertions for core fields.
- GitHub annotation and SARIF rendering from the same findings.
- Release readiness: build, twine check, wheel install smoke test, and CLI help.

## Documentation Strategy

The README should open with the v1 identity and the 10-minute path. Supporting
docs should include:

- CI adoption guide with `production` profile GitHub Action example.
- Readiness profiles reference.
- Bring-your-own CSV onboarding guide.
- Finding codes reference.
- Suppressions and exception handling guide.
- JSON output compatibility notes.
- Publishing and release checklist.

## Release Criteria

v1 is ready when:

- A new user can install with `pipx` or `pip`, run the demo, and see a passing
  trust report in under 10 minutes.
- A user can generate starter manifests from a CSV and understand what is
  missing for production.
- A repository can use the GitHub Action with `profile: production`.
- `starter`, `production`, and `regulated` profile behavior is documented and
  tested.
- Core JSON output fields are documented and covered by tests.
- Release smoke tests verify the built wheel, CLI help, schemas, and CI command.
- The README, docs, examples, and issue templates are coherent with the v1
  product identity.

## Open Decisions Resolved

- v1 focuses on CI gating rather than MCP or live agent serving.
- `starter` is optimized for local onboarding.
- Published CI examples recommend `production`.
- `init from-csv` is included in v1.
- Outcomes remain `pass`, `warn`, and `fail`.
- Core JSON fields are stable for v1 automation.
