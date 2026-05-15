#!/bin/bash
set -e

# tell the agent: Run ./scripts/setup_tests.sh, then run uv run pytest. If uv is unavailable, activate .venv and run pytest.

if command -v uv >/dev/null 2>&1; then
  uv pip install -r requirements-dev.txt
  uv pip install -e .
else
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -U pip wheel setuptools
  pip install -r requirements-dev.txt
  pip install -e .
fi