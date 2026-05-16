#!/usr/bin/env bash

# Policies to allow in docker sandbox when in locked down mode

set -euo pipefail

# For hosting Ollama models locally:
sbx policy allow network localhost:11434
sbx policy allow network host.docker.internal:11434

# Allow Docker Hub access:
sbx policy allow download.docker.com:443

# Allow ubuntu security updates for patches and package upgrades
sbx policy allow network debian.org:443
sbx policy allow network ports.ubuntu.com:443
sbx policy allow network deb.debian.org:443
sbx policy allow network archive.ubuntu.com:443
sbx policy allow network security.ubuntu.com:443

# Allow dependency registries
sbx policy allow network registry.npmjs.org:443
sbx policy allow network pypi.org:443
sbx policy allow network files.pythonhosted.org:443

# Allow AWS Bedrock
sbx policy allow network bedrock-runtime.us-west-2.amazonaws.com:443
sbx policy allow network bedrock-runtime.us-east-1.amazonaws.com:443

# Allow Google gemini
sbx policy allow network generativelanguage.googleapis.com:443
sbx policy allow network gemini-api-docs-mcp.dev:443
sbx policy allow network ai.google.dev:443
sbx policy allow network oauth2.googleapis.com:443
sbx policy allow network accounts.google.com:443
sbx policy allow network cloudcode-pa.googleapis.com:443
sbx policy allow network play.googleapis.com:443

# Allow OpenAI for codex Pro subscription
sbx policy allow network chatgpt.com:443
sbx policy allow network api.openai.com:443