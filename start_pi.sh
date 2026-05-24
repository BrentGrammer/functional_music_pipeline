#!/usr/bin/env bash
set -euo pipefail

DIR_NAME="$(basename "$PWD")"
CLEAN_NAME="${DIR_NAME//_/-}"
SANDBOX_NAME="pi-$CLEAN_NAME"

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
    echo "REMINDER: Once inside the sandbox, run 'pi' to start the CLI."

    configure_env

    sbx run "$SANDBOX_NAME"
else
    echo "🆕 Creating new sandbox: $SANDBOX_NAME"

    sbx create shell . --name "$SANDBOX_NAME"

    echo "⚙️ Upgrading Node, installing pi..."
    # to install node and allow pi auth:
    sbx policy allow network "$SANDBOX_NAME" nodejs.org:443
    sbx policy allow network "$SANDBOX_NAME" pi.dev:443
    sbx policy allow network "$SANDBOX_NAME" release-assets.githubusercontent.com:443

    # echo "Installing serena..."
    # sbx exec "$SANDBOX_NAME" bash -c "uv tool install -p 3.13 serena-agent@latest --prerelease=allow"
    # echo "SUCCESS: Serena installed. Settings copied to mcp_config.json"

    echo "Installing Node LTS, pi coding agent, context-mode package and mcp adapter for pi..."
    sbx exec "$SANDBOX_NAME" bash -c "curl -fsSL https://nodejs.org/dist/v24.9.0/node-v24.9.0-linux-arm64.tar.gz | sudo tar -xz -C /usr/local --strip-components=1 && sudo npm install -g --ignore-scripts @earendil-works/pi-coding-agent && npm install -g context-mode --ignore-scripts && pi install npm:pi-mcp-adapter"

    configure_env

    echo "✅ Setup complete! Dropping you into the sandbox."
    echo "!!! REMINDER: Run 'pi' to start the CLI, then run '/login' command after starting pi to set a key or subscription plan."
    sbx run "$SANDBOX_NAME"
fi

# Useful shortcuts in pi

# Turn off telemetry: /settings > select Install telemtry = false

# Ctrl+L - choose model
# Ctrl+P cycle model
# Shift+Tab thinking level
# Esc Abort
# /tree go back and edit a previous prompt to resubmit
# pi -c # continue session
# pi -r # resume picker select
# /settings
# !!<enter command> run a command in shell

# Skills stored in .agents/skills/<filename>

# packages at pi.dev/packages
# Get context-mode to save on context: https://pi.dev/packages/context-mode
# enable mcp compatibility and usage: https://pi.dev/packages/pi-mcp-adapter

# see https://www.youtube.com/watch?v=8Dt0HM8HIq4

#  To disable insights (analytics) for the context-mode package in pi agent:                                                                              
                                                                                                                                                        
#  Open .pi/npm/node_modules/context-mode/.env in a text editor and set:                                                                                  
                                                                                                                                                        
#  ```                                                                                                                                                    
#    CONTEXT_MODE_INSIGHTS=false                                                                                                                          
#  ```                                                                                                                                                    
                                                                                                                                                        
#  or set the environment variable before launching pi:                                                                                                   
                                                                                                                                                        
#  ```bash                                                                                                                                                
#    export CONTEXT_MODE_INSIGHTS=false                                                                                                                   
#  ```  
