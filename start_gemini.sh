#!/bin/bash

###############################################################################
# Gemini CLI OAuth Setup inside Docker SBX Locked-Down Sandbox
#
# Purpose:
# Use Gemini CLI with Google OAuth (subscription/account login)
# instead of an API key.
#
# Notes:
# - Do NOT use: sbx run gemini
# - Use: sbx run shell .
# - Gemini CLI may say "no sandbox"
#   because that refers to Gemini's internal sandbox,
#   not Docker SBX.
#
# First-Time Setup:
#
# 1. Remove Google API-key secret so Gemini uses OAuth:
#    sbx secret rm -g google
#
# 2. Allow required network policies:
#    sbx policy allow network registry.npmjs.org
#    sbx policy allow network generativelanguage.googleapis.com
#    sbx policy allow network oauth2.googleapis.com
#    sbx policy allow network accounts.google.com
#    sbx policy allow network play.googleapis.com
#    sbx policy allow network cloudcode-pa.googleapis.com
#
# 3. CD into the project root folder and start a generic shell sandbox in your project:
#    sbx run shell . --name <sandbox-name>
# optionally update and upgrade 
#    sudo apt update
#    sudo apt upgrade -y
#
# 4. Inside the sandbox, install Gemini CLI:
#    npm install -g @google/gemini-cli --no-scripts allow-git=none
#
# 5. Start Gemini CLI:
#    gemini
#
# 6. Choose:
#    "Sign in with Google"
#
################################################ 
#
# REUSING EXISTING SANDBOX (after setting it up initially using above instructions)
#
# 1. List existing sandboxes:
#    sbx ls
#
# 2. Reconnect to the existing sandbox:
#    sbx run <sandbox-name>
#
# Notes:
# - Gemini CLI install persists inside the sandbox.
# - OAuth login/session should persist inside the sandbox.
#
###############################################################################

# Get the base name of the current directory
DIR_NAME=$(basename "$PWD")
# Replace all underscores (_) with dashes (-)
CLEAN_NAME="${DIR_NAME//_/-}"
SANDBOX_NAME="gemini-$CLEAN_NAME"

echo "Using sandbox name: $SANDBOX_NAME"

chmod +x ./scripts/start_docker.sh
./scripts/start_docker.sh

code .

# Required policies for Gemini OAuth + Gemini CLI
chmod +x ./scripts/allow_sbx_policies.sh
./scripts/allow_sbx_policies.sh

# sync_gemini_settings() {
#   if [[ -f ".gemini/settings.json" ]]; then
#     echo "Syncing project .gemini/settings.json to sandbox home..."

#     sbx exec -d "$SANDBOX_NAME" bash -lc '
#       set -euo pipefail
#       mkdir -p "$HOME/.gemini"
#       cp .gemini/settings.json "$HOME/.gemini/settings.json"
#     ' || true
#   else
#     echo "No project .gemini/settings.json found; skipping settings sync."
#   fi
# }

# Reuse existing sandbox if it already exists
if sbx ls | grep -q "$SANDBOX_NAME"; then
  echo "✅ Existing sandbox found: $SANDBOX_NAME"
  echo "Reconnecting..."
  # sync_gemini_settings
  echo "REMINDER: Once inside the sandbox, run the command 'gemini' to start the cli."
  sbx run "$SANDBOX_NAME"
else
  echo "🆕 Creating new sandbox: $SANDBOX_NAME"
  sbx run shell . --name "$SANDBOX_NAME"
  # sync_gemini_settings
fi