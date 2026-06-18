# CI Rollout Guide

Use a staged rollout so data product teams learn from findings before the gate
blocks delivery.

## Phase 1: observe mode

Run the action or CLI on pull requests with text, GitHub annotation, and SARIF
output, but keep `fail-on: fail` and start with known passing examples or a
small product set.

```yaml
- uses: johnmikel/dataproduct-kit@v0.4.0
  with:
    path: "data-products"
    fail-on: "fail"
    format: "github"
    sarif: "dataproduct-kit.sarif.json"
```

During observe mode, review findings with product owners and decide whether each
one is a real defect, a missing manifest detail, or a short-lived migration.

## Phase 2: fail-only gate

Keep the default fail-only gate once teams understand the output. This blocks
schema drift, stale data, broken semantic definitions, and invalid policies while
allowing warnings to remain visible.

```toml
[ci]
include = ["data-products/**"]
exclude = ["data-products/sandbox/**"]
fail_on = "fail"
```

Use suppressions only for time-bound exceptions with clear owners and expiry
dates.

## Phase 3: warn gate

Move mature products to a warn gate when warnings represent policy expectations,
not optional advice.

```toml
[ci]
fail_on = "warn"
```

This makes missing freshness policies and unused suppressions block merges until
the product metadata is cleaned up.

## Phase 4: suppression cleanup

Schedule suppression cleanup as part of normal platform operations:

- Remove suppressions that produce `suppression.unused`.
- Fix or renew suppressions before they expire.
- Keep reasons specific enough for audit review.
- Prefer manifest, data, or semantic fixes over extending exceptions.

The goal is to make exceptions temporary and visible, not permanent CI noise.
