# Suppressions

Suppressions let a team accept a known finding for a specific data product while
keeping the finding visible in machine-readable output.

Use them for short-lived migration windows, not for permanent policy changes.
Every suppression must have a code, product path, reason, and expiry date.

## Configuration

Create `dataproduct-kit.toml` at the repository root:

```toml
[ci]
include = ["data-products/**"]
exclude = ["data-products/sandbox/**"]
profile = "production"
fail_on = "warn"

[[suppressions]]
code = "schema.missing_column"
path = "data-products/growth/saas-churn"
reason = "Producer migration is scheduled in the next sprint."
expires = "2026-08-01"
```

`include` and `exclude` use glob patterns against discovered product
directories. `profile` and `fail_on` become the defaults for
`dataproduct-kit ci` when the command does not pass `--profile` or `--fail-on`.

## Rules

- Suppression codes must be known finding codes.
- Expired suppressions fail the suite.
- Active suppressions that match no current finding produce a
  `suppression.unused` warning.
- Suppressed findings do not create GitHub annotations.
- JSON and text output still include the suppressed finding.
- SARIF output includes an external suppression with the reason and expiry.

## Profile Findings

Product-level profile findings use the same suppression mechanism as validation
findings. For example, a team can temporarily suppress
`profile.quality_checks_missing` while a producer adds checks:

```toml
[[suppressions]]
code = "profile.quality_checks_missing"
path = "data-products/growth/saas-churn"
reason = "Quality checks are being migrated from the legacy pipeline."
expires = "2026-08-01"
```

Use profile suppressions sparingly. In the `regulated` profile, any remaining
unsuppressed warning creates `profile.unsuppressed_warning`, so expired or unused
exceptions should be cleaned up before enabling that gate.

## Review Practice

Treat suppressions like production exceptions:

- Keep the reason specific enough for an auditor or new maintainer.
- Set the shortest practical expiry date.
- Review expired suppressions before extending them.
- Remove unused suppressions during cleanup so exceptions do not become stale
  institutional memory.
- Prefer fixing the manifest, data, or semantic definition over adding an
  exception.
