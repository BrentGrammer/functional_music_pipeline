#!/usr/bin/env bash
set -euo pipefail

DIR_NAME="$(basename "$PWD")"
CLEAN_NAME="${DIR_NAME//_/-}"
SANDBOX_NAME="cline-$CLEAN_NAME"

echo "Using sandbox name: $SANDBOX_NAME"

chmod +x ./scripts/start_docker.sh
./scripts/start_docker.sh

code . || true

if sbx ls | grep -q "$SANDBOX_NAME"; then
  echo "✅ Existing sandbox found: $SANDBOX_NAME"
  echo "Reconnecting..."
  echo "REMINDER: Once inside the sandbox, run 'cline' to start the CLI."
  sbx run "$SANDBOX_NAME"
else
  echo "🆕 Creating new sandbox: $SANDBOX_NAME"
  echo "!!! REMINDER: Install Cline inside the new sandbox:"
  echo "npm install -g cline && cline auth && cline"

  sbx create shell . --name "$SANDBOX_NAME"
  sbx run "$SANDBOX_NAME"
fi