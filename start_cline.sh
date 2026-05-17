#!/usr/bin/env bash
set -euo pipefail

DIR_NAME="$(basename "$PWD")"
CLEAN_NAME="${DIR_NAME//_/-}"
SANDBOX_NAME="cline-$CLEAN_NAME"

echo "Using sandbox name: $SANDBOX_NAME"

chmod +x ./scripts/start_docker.sh
./scripts/start_docker.sh

code . || true

if sbx ls | grep "$SANDBOX_NAME"; then
  echo "✅ Existing sandbox found: $SANDBOX_NAME"
  echo "Reconnecting..."
  echo "REMINDER: Once inside the sandbox, run 'cline' to start the CLI."
  sbx run "$SANDBOX_NAME"
else
  echo "🆕 Creating new sandbox: $SANDBOX_NAME"
  
  sbx create shell . --name "$SANDBOX_NAME"
  
  echo "⚙️ Upgrading Node, installing Cline..."
  # to install node:
  sbx policy allow network nodejs.org:443 # disable this afterwards if not needed

  # CONFIG_JSON='{"mcpServers":{"serena":{"command":"uv","args":["tool","run","--python","3.13","--from","serena-agent@latest","--prerelease=allow","serena","start-mcp-server","--project",".","--context=ide","--open-web-dashboard=false"]},"exa":{"url":"https://mcp.exa.ai/mcp"}}}'
  # && mkdir -p ~/.config/cline ~/.cline/data/settings && echo '$CONFIG_JSON' > ~/.config/cline/mcp.json && echo '$CONFIG_JSON' > ~/.cline/data/settings/cline_mcp_settings.json"
  
  sbx exec "$SANDBOX_NAME" bash -c "curl -fsSL https://nodejs.org/dist/v24.9.0/node-v24.9.0-linux-arm64.tar.gz | sudo tar -xz -C /usr/local --strip-components=1 && sudo npm install -g cline --no-scripts --allow-git=none"

  echo "✅ Setup complete! Dropping you into the sandbox."
  echo "!!! REMINDER: Run 'cline auth' then 'cline' once inside."
  
  sbx run "$SANDBOX_NAME"
fi