#!/bin/bash

# Get the base name of the current directory
DIR_NAME=$(basename "$PWD")
# Replace all underscores (_) with dashes (-)
CLEAN_NAME="${DIR_NAME//_/-}"
SANDBOX_NAME="gemini-$CLEAN_NAME"

echo "Using sandbox name: $SANDBOX_NAME"

chmod +x ./scripts/start_docker.sh
./scripts/start_docker.sh

code .

# Reuse existing sandbox if it already exists
if sbx ls | grep -q "$SANDBOX_NAME"; then
  echo "✅ Existing sandbox found: $SANDBOX_NAME"
  echo "Reconnecting..."
  echo "REMINDER: Once inside the sandbox, run the command 'gemini' to start the cli."
  sbx run "$SANDBOX_NAME"
else
  echo "🆕 Creating new sandbox: $SANDBOX_NAME"
  sbx run shell . --name "$SANDBOX_NAME"
fi