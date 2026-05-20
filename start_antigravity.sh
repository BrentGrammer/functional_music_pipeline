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

configure_env() {
	echo "Configuring privacy/telemetry environment inside sandbox..."
	# This is idempotent: it replaces any previous block managed by this script.
	sbx exec -d "$SANDBOX_NAME" bash -c '
set -euo pipefail

touch /etc/sandbox-persistent.sh

cat >> /etc/sandbox-persistent.sh <<'"'"'EOF'"'"'
export DO_NOT_TRACK=1
export SBX_NO_TELEMETRY=1
export AWS_REGION=us-west-2
export TERM=xterm-256color
EOF

for rcfile in "$HOME/.bashrc" "$HOME/.profile"; do
  if [ -f "$rcfile" ]; then
    if ! grep "source /etc/sandbox-persistent.sh" "$rcfile"; then
      echo "source /etc/sandbox-persistent.sh" >> "$rcfile"
    fi
  fi
done
' || true
}

###############################################################################
# Create or reuse sandbox
###############################################################################

if sbx ls | grep "$SANDBOX_NAME"; then
	echo "✅ Existing sandbox found: $SANDBOX_NAME"
else
	echo "🆕 Creating new sandbox: $SANDBOX_NAME"

	sbx create shell . --name "$SANDBOX_NAME"

	configure_env

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
	sbx policy allow network "$SANDBOX_NAME" oraios-software.de:443

	# for installing node
	sbx policy allow network "$SANDBOX_NAME" nodejs.org:443

	echo "Installing serena..."
	# Create the directory so sbx cp's internal tar extraction doesn't crash
	sbx exec "$SANDBOX_NAME" bash -c "mkdir -p /home/agent/.gemini/antigravity-cli"
	# install serena
	sbx exec "$SANDBOX_NAME" bash -c "uv tool install -p 3.13 serena-agent@latest --prerelease=allow"
	# move mcp settings to sandbox
	sbx cp .gemini/antigravity/mcp_config.json "$SANDBOX_NAME":/home/agent/.gemini/antigravity-cli/mcp_config.json
	echo "SUCCESS: Serena installed. Settings copied to mcp_config.json"

	# Node and usage tool: see https://github.com/skainguyen1412/antigravity-usage
	echo "Installing Node..."
	sbx exec "$SANDBOX_NAME" bash -c "curl -fsSL https://nodejs.org/dist/v24.9.0/node-v24.9.0-linux-arm64.tar.gz | sudo tar -xz -C /usr/local --strip-components=1"
	# This did not work - requires callback to localhost to signin: && sudo npm install -g antigravity-usage --ignore-scripts --allow-git=none"
	echo "SUCCESS: Node installed!"

	echo "Installing antigravity-cli..."
	sbx exec "$SANDBOX_NAME" bash -c "curl -fsSL https://antigravity.google/cli/install.sh | bash"
	echo "SUCCESS: Installed Antigravity CLI"

	# Copy npm config into the sandbox
	if [ -f ".npmrc" ]; then
		echo "Copying project .npmrc into sandbox..."
		sbx cp ".npmrc" "$SANDBOX_NAME:/home/agent/.npmrc"
	else
		echo "No .npmrc found to copy."
	fi
fi

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
