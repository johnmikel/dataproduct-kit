# CI Adoption

`dataproduct-kit ci` validates every data product under a repository path. It is
designed for pull request gates where a platform team wants fast feedback on data
product contracts, freshness, semantic definitions, and policy context.

## Local command

```bash
dataproduct-kit ci . --profile starter --format text --fail-on fail
dataproduct-kit ci . --profile production --format json --fail-on warn
dataproduct-kit ci . --profile production --format github --sarif dataproduct-kit.sarif.json
```

The command discovers directories that contain `dataproduct.yaml`, validates each
one, and returns a suite status:

- `pass`: every discovered product passed.
- `warn`: at least one product has warnings and none failed.
- `fail`: at least one product failed, or no data products were discovered.

Use `--fail-on warn` when warnings should block a merge.

## Repository Config

Create `dataproduct-kit.toml` at the repository root to make local and CI
behavior consistent:

```toml
[ci]
include = ["data-products/**"]
exclude = ["data-products/sandbox/**"]
profile = "production"
fail_on = "warn"
```

When `--profile` or `--fail-on` is omitted, `dataproduct-kit ci` uses the config
value. See [readiness-profiles.md](readiness-profiles.md) for profile behavior
and [suppressions.md](suppressions.md) for temporary exception handling with
expiry dates.

## Reusable GitHub Action

```yaml
name: Data Product Trust

on:
  pull_request:
    branches: ["main"]

jobs:
  dataproduct-kit:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write

    steps:
      - uses: actions/checkout@v5

      - uses: johnmikel/dataproduct-kit@v0.4.0
        with:
          path: "."
          profile: "production"
          fail-on: "warn"
          format: "github"
          sarif: "dataproduct-kit.sarif.json"

      - uses: github/codeql-action/upload-sarif@v4
        if: always()
        with:
          sarif_file: "dataproduct-kit.sarif.json"
```

The action installs `dataproduct-kit` from the checked-out action source, applies
the selected readiness profile, emits GitHub annotation commands for findings,
and writes SARIF for audit evidence.

## Recommended repository shape

```text
data-products/
  growth/saas-churn/
    dataproduct.yaml
    contract.yaml
    semantic.yaml
    policy.yaml
    data/subscriptions.csv
  finance/revenue/
    dataproduct.yaml
    contract.yaml
    semantic.yaml
    policy.yaml
```

Run:

```bash
dataproduct-kit ci data-products --profile production --format github --fail-on warn
```

## Starter versus production

Use `starter` when a team is importing a CSV or creating its first manifests. It
keeps missing agent constraints, quality checks, and semantic metrics visible as
warnings so the team can iterate locally.

Use `production` in pull request gates. It turns those starter gaps into errors
and also requires policy purposes, the `agent_context` purpose, and sensitive
field coverage.

## When to block

Use `--fail-on fail` when the team is adopting the tool for the first time and
does not want warnings to block delivery.

Use `--fail-on warn` for mature repositories where missing freshness policies or
other warning-level findings should be fixed before merge.
