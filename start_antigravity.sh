#!/bin/bash

###############################################################################
# Antigravity CLI OAuth Setup inside Docker SBX Locked-Down Sandbox
# see https://antigravity.google/docs/cli-getting-started
# see https://antigravity.google/docs/mcp
###############################################################################

set -euo pipefail

DIR_NAME=$(basename "$PWD")
CLEAN_NAME="${DIR_NAME//_/-}"
SANDBOX_NAME="antigravity-$CLEAN_NAME"

echo "Using sandbox name: $SANDBOX_NAME"


chmod +x ./scripts/start_docker.sh
./scripts/start_docker.sh

code .


###############################################################################
# Create or reuse sandbox
###############################################################################

if sbx ls | grep -q "$SANDBOX_NAME"; then
  echo "✅ Existing sandbox found: $SANDBOX_NAME"
else
  echo "🆕 Creating new sandbox: $SANDBOX_NAME"

  sbx create shell . --name "$SANDBOX_NAME"

  #############################################################################
  # Copy npm config into the sandbox
  #############################################################################

  if [ -f ".npmrc" ]; then
    echo "Copying project .npmrc into sandbox..."
    sbx cp ".npmrc" "$SANDBOX_NAME:/home/agent/.npmrc"
  else
    echo "No .npmrc found to copy."
  fi
fi

###############################################################################
# Sandbox-specific SBX policies
# These MUST run after the named sandbox exists.
###############################################################################

echo "Allowing sandbox-specific SBX network policies for $SANDBOX_NAME..."

# Antigravity CLI updater / runtime fetches
sbx policy allow network "$SANDBOX_NAME" "antigravity-cli-auto-updater-974169037036.us-central1.run.app:443"
sbx policy allow network "$SANDBOX_NAME" "storage.googleapis.com:443"

# Google OAuth / account login
sbx policy allow network "$SANDBOX_NAME" "oauth2.googleapis.com:443"
sbx policy allow network "$SANDBOX_NAME" "accounts.google.com:443"
sbx policy allow network "$SANDBOX_NAME" "play.googleapis.com:443"

# Gemini / Code Assist / Antigravity model endpoints
sbx policy allow network "$SANDBOX_NAME" "generativelanguage.googleapis.com:443"
sbx policy allow network "$SANDBOX_NAME" "cloudcode-pa.googleapis.com:443"
sbx policy allow network "$SANDBOX_NAME" "daily-cloudcode-pa.googleapis.com:443"

# Antigravity app / CLI endpoints
sbx policy allow network "$SANDBOX_NAME" "antigravity.google:443"
sbx policy allow network "$SANDBOX_NAME" "*.antigravity.google:443"
sbx policy allow network "$SANDBOX_NAME" "antigravity-unleash.goog:443"

# Google-hosted profile/assets
sbx policy allow network "$SANDBOX_NAME" "lh3.googleusercontent.com:443"

# Playwright downloads used by Antigravity/browser tooling
sbx policy allow network "$SANDBOX_NAME" "playwright.azureedge.net:443"
sbx policy allow network "$SANDBOX_NAME" "playwright-akamai.azureedge.net:443"
sbx policy allow network "$SANDBOX_NAME" "playwright-verizon.azureedge.net:443"

# Serena MCP / uv / Python package install
sbx policy allow network "$SANDBOX_NAME" "github.com:443"
sbx policy allow network "$SANDBOX_NAME" "objects.githubusercontent.com:443"
sbx policy allow network "$SANDBOX_NAME" "pypi.org:443"
sbx policy allow network "$SANDBOX_NAME" "files.pythonhosted.org:443"
sbx policy allow network "$SANDBOX_NAME" "astral.sh:443"
sbx policy allow network "$SANDBOX_NAME" "uv.sh:443"

echo "✅ Sandbox-specific SBX network policies applied."

###############################################################################
# Run sandbox
###############################################################################

cat <<'EOF'

Inside the sandbox, install Antigravity if needed:

    sudo apt update && sudo apt upgrade -y
    curl -fsSL https://antigravity.google/cli/install.sh | bash

Start Antigravity:

  agy

EOF

sbx run "$SANDBOX_NAME"