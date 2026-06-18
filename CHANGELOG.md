# Changelog

## v0.4.0 - Unreleased

- Add repository config with CI discovery filters and default `fail_on` policy.
- Add suppression support with expiry validation and SARIF suppression metadata.
- Add release smoke install script and run it from the verification script.
- Add dogfood, release smoke, and trusted publishing GitHub workflows.
- Add suppression documentation and public issue templates.
- Add Trusted Publishing setup docs and a v0.4.0 release checklist.
- Add a manual TestPyPI-only publishing dry run.
- Add readiness profiles for starter, production, and regulated adoption.
- Add CSV onboarding for teams bringing their own local data.
- Add a doctor command that explains production-readiness gaps.
- Stabilize CI JSON output for v1 automation consumers.
- Add config JSON Schema export, unused suppression warnings, source line
  metadata for CI annotations/SARIF, and production rollout docs.

## v0.3.0 - 2026-06-17

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
