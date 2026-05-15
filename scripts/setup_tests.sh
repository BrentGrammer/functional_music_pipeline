#!/bin/bash
set -e

# tell the agent: Run ./scripts/setup_tests.sh, then run uv run pytest. If uv is unavailable, activate .venv and run pytest.

run_as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "This script needs to install system packages, but sudo is not available." >&2
    echo "Install compiler/build tools and PortAudio headers manually, then rerun this script." >&2
    exit 1
  fi
}

install_system_test_dependencies() {
  if command -v apt-get >/dev/null 2>&1; then
    run_as_root apt-get update
    run_as_root apt-get install -y \
      build-essential \
      gcc \
      gcc-aarch64-linux-gnu \
      portaudio19-dev \
      python3-dev
  elif command -v dnf >/dev/null 2>&1; then
    run_as_root dnf install -y \
      gcc \
      gcc-c++ \
      portaudio-devel \
      python3-devel
  elif command -v apk >/dev/null 2>&1; then
    run_as_root apk add \
      build-base \
      gcc \
      portaudio-dev \
      python3-dev
  elif command -v brew >/dev/null 2>&1; then
    brew install portaudio
  else
    echo "Unsupported package manager." >&2
    echo "Install compiler/build tools and PortAudio headers manually, then rerun this script." >&2
    exit 1
  fi
}

install_system_test_dependencies

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
