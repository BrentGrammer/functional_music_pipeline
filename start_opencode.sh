#!/usr/bin/env bash
set -euo pipefail

# try these models:
# qwen.qwen3-coder-next
# minimax.minimax-m2.5
# minimax.minimax-m2.1
# mistral.devstral-2-123b
# deepseek.v3.2
# zai.glm-4.7

# Could not get Deepseek R1 to work with OPENCODE

# Good complex coding models to try from Bedrock:
# 1. Claude Opus 4.5 or Claude Opus 4.6 (US) works from Bedrock
# 2. Claude Sonnet 4.5
# 3. Claude Opus 4.1
# 4. Qwen3 Coder Next  # This one seemed really good for planning refactors!
# 5. Devstral 2 123B
# 6. DeepSeek V3.2
# 7. MiniMax M2.5
# 8. GLM5
# 9. Kimi K2.5 # The thinking version is capable, but was really slow and a little glitchy

MODEL="openai/gpt-5.5"
# MODEL="amazon-bedrock/zai.glm-5"
PROJECT_DIR="${1:-$PWD}"

PROJECT_BASENAME="$(basename "$PROJECT_DIR")"
SANDBOX_NAME="opencode-${PROJECT_BASENAME//_/-}"

# One-time setup per sandbox name - enter your API key for BYOK usage:
#   Ex: sbx secret set <sandbox_name> openai
#
# Usage:
#   ./start-opencode-sbx.sh /path/to/my_project
#
# Example sandbox name:
#   my_project -> opencode-my-project

# Required for using bedrock
sbx policy allow network "bedrock-runtime.us-west-2.amazonaws.com"
sbx policy allow network "bedrock-runtime.us-east-1.amazonaws.com"

configure_privacy_flags() {
  echo "Configuring privacy/telemetry environment inside sandbox..."
  # Persist OpenCode/Docker telemetry-related env vars inside this sandbox.
  # This is idempotent: it replaces any previous block managed by this script.
  sbx exec -d "$SANDBOX_NAME" bash -c '
set -euo pipefail

touch /etc/sandbox-persistent.sh

sed -i "/# BEGIN opencode privacy flags/,/# END opencode privacy flags/d" /etc/sandbox-persistent.sh

cat >> /etc/sandbox-persistent.sh <<'"'"'EOF'"'"'
# BEGIN opencode privacy flags
export OPENCODE_DISABLE_SHARE=1
export OPENCODE_DISABLE_AUTOUPDATE=1
export DO_NOT_TRACK=1
export SBX_NO_TELEMETRY=1
# END opencode privacy flags
EOF
' || true
}

# OPENCODE_DISABLE_MODELS_FETCH # this can slow things down, so revisit whether really need this

echo "Starting opencode agent for project $PROJECT_BASENAME with model: $MODEL..."
echo "Sandbox name: $SANDBOX_NAME"
echo "Project dir: $PROJECT_DIR"
echo "!!! IMPORTANT !!! --- Remember to set your API key with 'sbx secret set ${SANDBOX_NAME} openai' ---"

# Reuse existing sandbox if it already exists
if sbx ls | grep "$SANDBOX_NAME"; then
  echo "✅ Existing sandbox found: $SANDBOX_NAME"
  echo "Reconnecting..."

  configure_privacy_flags

  sbx run "$SANDBOX_NAME" -- --model "$MODEL"
else
  echo "🆕 Creating new sandbox: $SANDBOX_NAME"

  sbx create opencode "$PROJECT_DIR" --name "$SANDBOX_NAME"

  configure_privacy_flags

  sbx run "$SANDBOX_NAME" -- --model "$MODEL"
fi