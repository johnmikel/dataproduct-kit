# v0.5 CI Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make dataproduct-kit more production-ready for GitHub CI adoption by adding config schema export, unused suppression warnings, source line locations, and operational docs.

**Architecture:** Keep behavior in the existing focused modules: schema generation in `schemas.py`, config/suppression suite behavior in `suite.py`, source location lookup in a small helper module, and annotation/SARIF rendering in `ci.py`. Avoid changing the public manifest shape beyond generated schema exposure.

**Tech Stack:** Python 3.11+, Pydantic, Typer, pytest, Ruff, SARIF JSON.

---

## File Structure

- Modify `src/dataproduct_kit/schemas.py` to include `KitConfig` as the `config` schema and include it in `all`.
- Modify `src/dataproduct_kit/cli.py` so `dataproduct-kit schema config` is accepted.
- Modify `src/dataproduct_kit/models.py` to add an optional source `line` to findings.
- Create `src/dataproduct_kit/source_locations.py` for best-effort line lookup without coupling validators to YAML/TOML parsing internals.
- Modify `src/dataproduct_kit/suite.py` to enrich suite findings with line numbers and emit `suppression.unused` warnings.
- Modify `src/dataproduct_kit/ci.py` to use `line` in GitHub annotations and SARIF regions.
- Modify `src/dataproduct_kit/finding_codes.py`, `docs/finding-codes.md`, and `docs/suppressions.md` for the new warning code.
- Create `docs/compatibility.md` and `docs/ci-rollout.md`; update `README.md` links.
- Update tests in `tests/test_cli.py`, `tests/test_config.py`, `tests/test_ci.py`, and `tests/test_release_readiness.py`.

## Task 1: Config Schema CLI

- [x] Add a failing CLI test asserting `dataproduct-kit schema config` returns a JSON Schema for `KitConfig`.
- [x] Add a failing CLI test asserting `schema all --out` writes `config.schema.json`.
- [x] Run the focused tests and confirm failure because `config` is not an accepted schema name.
- [x] Import `KitConfig` into `schemas.py`, add it to `SCHEMA_MODELS`, and extend the `SchemaName`/CLI literal to include `config`.
- [x] Run the focused tests and confirm they pass.

## Task 2: Unused Suppression Warning

- [x] Add a failing suite test with a valid passing product and an active suppression that matches no current finding.
- [x] Assert the suite status is `warn`, the suite-level finding code is `suppression.unused`, and the product remains `pass`.
- [x] Run the focused test and confirm failure because no unused suppression warning exists.
- [x] Track matched suppressions while applying suppressions.
- [x] Emit one suite-level `suppression.unused` warning for each valid, active suppression that matched no finding.
- [x] Add `suppression.unused` to known codes and docs.
- [x] Run focused config/suite tests and confirm they pass.

## Task 3: Source Line Locations

- [x] Add failing tests asserting GitHub annotations include `line=` for a schema drift finding.
- [x] Add failing tests asserting SARIF includes `physicalLocation.region.startLine`.
- [x] Add a failing test asserting a suite-level suppression warning points at `dataproduct-kit.toml`.
- [x] Run focused CI/config tests and confirm failure because findings lack line metadata.
- [x] Add `Finding.line: int | None`.
- [x] Implement best-effort source lookup in `source_locations.py` by selecting manifest files from finding codes and scanning for useful tokens.
- [x] Enrich product and suite-level findings in `suite.py` before rendering.
- [x] Update GitHub annotation properties and SARIF location output to include line metadata when present.
- [x] Run focused CI/config tests and confirm they pass.

## Task 4: Production Adoption Docs

- [x] Add failing release-readiness tests for compatibility and CI rollout docs.
- [x] Run focused doc tests and confirm failure because docs are missing.
- [x] Create `docs/compatibility.md` describing stable CLI/config and evolving manifests.
- [x] Create `docs/ci-rollout.md` with observe mode, fail-only gate, warn gate, and suppression cleanup.
- [x] Link both docs from `README.md`.
- [x] Run focused doc tests and confirm they pass.

## Task 5: Full Verification and Integration

- [ ] Run `PYTHON=.venv/bin/python ./scripts/verify.sh`.
- [ ] Fix any failures with tests first when behavior changes are needed.
- [ ] Commit the branch.
- [ ] Merge into local `main` using trunk-based flow.
- [ ] Push `main`.
- [ ] Check hosted GitHub workflows for the pushed commit.
- [ ] Close GitHub issues #2, #3, and #4 if the implementation satisfies them.
