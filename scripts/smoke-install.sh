#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: scripts/smoke-install.sh <wheel>" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
wheel="$1"

if [[ "$wheel" != /* ]]; then
  wheel="$repo_root/$wheel"
fi

if [[ ! -f "$wheel" ]]; then
  echo "wheel not found: $wheel" >&2
  exit 2
fi

PYTHON="${PYTHON:-python3}"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

cd "$repo_root"
# Keep this smoke test isolated with python -m venv so only the built wheel is exercised.
"$PYTHON" -m venv "$tmp_dir/venv"
"$tmp_dir/venv/bin/python" -m pip install --upgrade pip
"$tmp_dir/venv/bin/python" -m pip install "$wheel"

PATH="$tmp_dir/venv/bin:$PATH" dataproduct-kit --help >/dev/null
PATH="$tmp_dir/venv/bin:$PATH" dataproduct-kit schema all >/dev/null
PATH="$tmp_dir/venv/bin:$PATH" dataproduct-kit ci examples/pass >/dev/null
