# v0.4.0 Release Checklist

Use this checklist to cut `v0.4.0` from a clean `main` checkout.

Do not create the GitHub Release until TestPyPI and PyPI Trusted Publishers are
configured as described in [publishing.md](publishing.md). Publishing the GitHub
Release triggers `.github/workflows/publish.yml`.

## 1. Start Clean

```bash
git checkout main
git pull --ff-only
git status --short --branch
```

Expected status:

```text
## main...origin/main
```

## 2. Verify The Release Candidate

```bash
PYTHON=.venv/bin/python ./scripts/verify.sh
```

Record that the command completed successfully. The script runs:

- pytest
- Ruff
- `pip check`
- `python -m build`
- `twine check dist/*`
- wheel smoke install with `scripts/smoke-install.sh`

## 3. Finalize The Changelog

Update `CHANGELOG.md`:

```diff
-## v0.4.0 - Unreleased
+## v0.4.0 - 2026-06-19
```

Commit that changelog-only change:

```bash
git add CHANGELOG.md
git commit -m "Finalize v0.4.0 changelog"
git push origin main
```

Wait for the `main` CI, release smoke, and dogfood workflows to pass.

## 4. Create The Tag

```bash
git tag -a v0.4.0 -m "v0.4.0"
git push origin v0.4.0
```

## 5. Run The TestPyPI Dry Run

Before creating the GitHub Release, run the `Publish` workflow manually with:

```yaml
target: testpypi
```

Confirm that:

- The build job succeeds.
- The `publish-testpypi` job succeeds.
- The `publish-pypi` job is skipped.
- A clean TestPyPI install can run `dataproduct-kit --help`.

## 6. Create The GitHub Release

Create a GitHub Release for tag `v0.4.0`.

Suggested release title:

```text
v0.4.0
```

Suggested release notes:

```markdown
## Highlights

- Add repository config for CI discovery and default gate policy.
- Add expiring suppressions with SARIF suppression metadata.
- Add release smoke install checks.
- Add dogfood, release smoke, and trusted publishing workflows.
- Add public maintainer docs and issue templates.

## Verification

- `./scripts/verify.sh`
- GitHub CI on Python 3.11, 3.12, and 3.13
- GitHub Release Smoke
- dataproduct-kit Dogfood
```

Publishing the GitHub Release starts `.github/workflows/publish.yml`. That
workflow builds the package, publishes to TestPyPI using the `testpypi`
environment, then publishes to PyPI using the `pypi` environment.

## 7. Post-Release Checks

After the workflow completes:

```bash
python3 -m venv /tmp/dataproduct-kit-v040
/tmp/dataproduct-kit-v040/bin/python -m pip install dataproduct-kit==0.4.0
/tmp/dataproduct-kit-v040/bin/dataproduct-kit --help
```

Confirm the GitHub Release links to the successful publish workflow run.
