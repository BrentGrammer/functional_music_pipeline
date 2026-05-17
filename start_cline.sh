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
  
  echo "⚙️ Installing and configuring Cline directly inside the sandbox..."
  # uv tool run --python 3.13 --from serena-agent@latest --prerelease=allow serena start-mcp-server --project . --context=ide --open-web-dashboard=false
  # Use 'sbx exec' to run the setup strictly inside the container/microVM
  sbx exec "$SANDBOX_NAME" bash -c "npm install -g cline --no-scripts --allow-git=none && cline mcp add serena -- uv tool run --python 3.13 --from serena-agent@latest --prerelease=allow serena start-mcp-server --project . --context=ide --open-web-dashboard=false && cline mcp add exa https://mcp.exa.ai/mcp --type http"
  
  echo "✅ Setup complete! Dropping you into the sandbox."
  echo "!!! REMINDER: Run 'cline auth' then 'cline' once inside."
  
  sbx run
fi