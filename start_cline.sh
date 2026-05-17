#!/usr/bin/env bash
set -euo pipefail

DIR_NAME="$(basename "$PWD")"
CLEAN_NAME="${DIR_NAME//_/-}"
SANDBOX_NAME="cline-$CLEAN_NAME"

echo "Using sandbox name: $SANDBOX_NAME"

chmod +x ./scripts/start_docker.sh
./scripts/start_docker.sh

code . || true

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

if sbx ls | grep "$SANDBOX_NAME"; then
  echo "✅ Existing sandbox found: $SANDBOX_NAME"
  echo "Reconnecting..."
  echo "REMINDER: Once inside the sandbox, run 'cline' to start the CLI."

  configure_env
  
  sbx run "$SANDBOX_NAME"
else
  echo "🆕 Creating new sandbox: $SANDBOX_NAME"
  
  sbx create shell . --name "$SANDBOX_NAME"
  
  echo "⚙️ Upgrading Node, installing Cline..."
  # to install node and allow cline auth:
  sbx policy allow network $SANDBOX_NAME nodejs.org:443
  sbx policy allow network $SANDBOX_NAME api.workos.com:443
  sbx policy allow network $SANDBOX_NAME api.cline.bot:443

  # CONFIG_JSON='{"mcpServers":{"serena":{"command":"uv","args":["tool","run","--python","3.13","--from","serena-agent@latest","--prerelease=allow","serena","start-mcp-server","--project",".","--context=ide","--open-web-dashboard=false"]},"exa":{"url":"https://mcp.exa.ai/mcp"}}}'
  # && mkdir -p ~/.config/cline ~/.cline/data/settings && echo '$CONFIG_JSON' > ~/.config/cline/mcp.json && echo '$CONFIG_JSON' > ~/.cline/data/settings/cline_mcp_settings.json"
  
  sbx exec "$SANDBOX_NAME" bash -c "curl -fsSL https://nodejs.org/dist/v24.9.0/node-v24.9.0-linux-arm64.tar.gz | sudo tar -xz -C /usr/local --strip-components=1 && sudo npm install -g cline --no-scripts --allow-git=none"

  configure_env

  # Create the directory so sbx cp's internal tar extraction doesn't crash
  sbx exec "$SANDBOX_NAME" bash -c "mkdir -p /home/agent/.cline/data/settings"

  # move global config with mcp server and telemtry flags to the sandbox directory where cline expects these.
  sbx cp .cline/data/settings/cline_mcp_settings.json "$SANDBOX_NAME":/home/agent/.cline/data/settings/cline_mcp_settings.json
  sbx cp .cline/data/settings/global-settings.json "$SANDBOX_NAME":/home/agent/.cline/data/settings/global-settings.json
  
  echo "✅ Setup complete! Dropping you into the sandbox."
  echo "!!! REMINDER: Run 'cline auth' (requires registering a cline account on their site), then 'cline' to start the CLI."
  sbx run "$SANDBOX_NAME"
fi