#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-python3}"

"$PYTHON" -m pytest
"$PYTHON" -m ruff check .
"$PYTHON" -m pip check
rm -rf dist build
"$PYTHON" -m build
"$PYTHON" -m twine check dist/*
./scripts/smoke-install.sh dist/dataproduct_kit-*.whl
