#!/bin/bash

DIR_NAME="$(basename "$PWD")"
CLEAN_NAME="${DIR_NAME//_/-}"
SANDBOX_NAME="codex-$CLEAN_NAME"

chmod +x ./scripts/start_docker.sh
./scripts/start_docker.sh

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

code .

# requires logging in and setting secret (copy url this shows and login with Plus Subscription account):
#  sbx secret set -g openai --oauth

sbx policy allow network "$SANDBOX_NAME" chatgpt.com:443
sbx policy allow network "$SANDBOX_NAME" nodejs.org:443
# needed for context-mode tool
sbx policy allow network "$SANDBOX_NAME" raw.githubusercontent.com:443

if sbx ls | grep "$SANDBOX_NAME"; then
    echo "Setting env vars, disable telemetry..."
    configure_env

    # Copy project npm config into the Docker sandbox user's npm config location
    if [ -f .npmrc ]; then
        sbx cp .npmrc "$SANDBOX_NAME":/home/agent/.npmrc
    fi

    sbx run codex -- --sandbox workspace-write --cd . -c analytics.enabled=false
else
    echo "!!! WARNING !!! No sandbox $SANDBOX_NAME found!"
    echo "    Creating sandbox $SANDBOX_NAME..."

    sbx create codex . --name "$SANDBOX_NAME"

    echo "Installing Node LTS and tools (codex-context)..."
    sbx exec "$SANDBOX_NAME" bash -c "curl -fsSL https://nodejs.org/dist/v24.9.0/node-v24.9.0-linux-arm64.tar.gz | sudo tar -xz -C /usr/local --strip-components=1 && sudo codex plugin marketplace add mksglu/context-mode"

    echo "SUCCESS: Sandbox created. Tools installed. Use the start script or run command to start it."
    echo " !!! REMINDER !!!"
    echo "   T
    o use context-mode tool, run /plugins in codex and select install"
    echo " !!! END REMINDER !!!"
fi

