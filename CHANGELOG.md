# Changelog

## v0.3.0 - Unreleased

- Add repo-wide CI validation with the `ci` command.
- Add GitHub workflow annotation output for pull request review.
- Add SARIF output for security/code-scanning style evidence.
- Add a reusable composite GitHub Action.
- Add finding-code and CI adoption documentation.
- Update GitHub Actions workflow dependencies to Node 24-compatible major versions.

## v0.2.0 - 2026-06-17

- Add machine-readable validation output with `validate --format json`.
- Add strict CI behavior with `validate --fail-on warn`.
- Add manifest JSON Schema generation with the `schema` command.
- Add file output support to standards exports with `export --out`.
- Add passing and failing example data products for common validation scenarios.
- Add release verification script with tests, lint, dependency check, package build, and metadata check.

## v0.1.0 - 2026-06-17

- Initial alpha release with local manifests, DuckDB validation, trust reports,
  agent-safe context, standards-aligned exports, OpenLineage-compatible events,
  and SaaS churn demo template.
